# core/auth.py
# Bearer-token validation for the access tokens DAIKON forwards. Mirrors DAIKON's AddDaikonAuthentication
# (Microsoft.Identity.Web for Entra ID, plain JwtBearer for KeyCloak) so the same tokens pass in both.

import threading
import time

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.logging_config import logger

if settings.OIDCProvider == "EntraID":
    _instance = settings.EntraID_Instance.rstrip("/") + "/"
    _tenant = settings.EntraID_TenantId
    _client = settings.EntraID_ClientId
    DISCOVERY_URL = f"{_instance}{_tenant}/v2.0/.well-known/openid-configuration"
    # v2 and v1 issuer forms for this tenant; which one a token carries depends on the app registration.
    ISSUERS = [f"{_instance}{_tenant}/v2.0", f"https://sts.windows.net/{_tenant}/"]
    AUDIENCES = [settings.EntraID_Audience, _client, f"api://{_client}"]
else:  # KeyCloak: DAIKON validates issuer == Authority exactly, and the one configured audience.
    DISCOVERY_URL = settings.KeyCloak_Authority.rstrip("/") + "/.well-known/openid-configuration"
    ISSUERS = [settings.KeyCloak_Authority]
    AUDIENCES = [settings.KeyCloak_Audience]
CLOCK_SKEW_SECONDS = 300

_keys: dict = {}  # kid -> PyJWK
_fetched_at = float("-inf")
_lock = threading.Lock()


def _fetch_keys() -> dict:
    jwks_uri = httpx.get(DISCOVERY_URL, timeout=10).raise_for_status().json()["jwks_uri"]
    jwks = httpx.get(jwks_uri, timeout=10).raise_for_status().json()
    return {k.key_id: k for k in jwt.PyJWKSet.from_dict(jwks).keys}


def _signing_key(kid):
    global _keys, _fetched_at
    with _lock:
        age = time.monotonic() - _fetched_at
        # Refetch when an unknown kid shows up (key rollover), at most once a minute so junk
        # tokens can't make us hammer Entra, and every 12h so retired keys drop out.
        if (kid not in _keys and age > 60) or age > 12 * 3600:
            _fetched_at = time.monotonic()
            _keys = _fetch_keys()
        return _keys.get(kid)


_bearer = HTTPBearer(auto_error=False)


def require_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Reject the request with 401 unless it carries a valid access token for DAIKON.

    Returns the token's claims; use them (oid, name, preferred_username) to identify the
    caller, never request headers. Sync on purpose: FastAPI runs it in a thread, so a key
    fetch doesn't block the event loop.
    """
    if creds is None:
        raise HTTPException(401, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    try:
        key = _signing_key(jwt.get_unverified_header(creds.credentials).get("kid"))
        if key is None:
            raise jwt.InvalidTokenError("Unknown signing key")
        claims = jwt.decode(
            creds.credentials,
            key.key,
            algorithms=[key.algorithm_name],  # the key's own algorithm: RS256 for Entra ID keys
            audience=AUDIENCES,
            issuer=ISSUERS,
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["exp", "iss", "aud"]},
        )
        # Accept access tokens only, as DAIKON does: ID and Logout tokens are signed with the same keys and can
        # carry the same audience.
        if settings.OIDCProvider == "EntraID":
            # Microsoft.Identity.Web requires scp (delegated) or roles (app-only).
            if not claims.get("scp") and not claims.get("roles"):
                raise jwt.InvalidTokenError("Token has neither scp nor roles")
        elif claims.get("typ") != "Bearer":
            # KeyCloak names the token kind in typ: allow exactly "Bearer"; "ID", "Logout" or no typ are rejected.
            raise jwt.InvalidTokenError("Not a KeyCloak access token")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Rejected bearer token: {e}")  # never log the token itself
        raise HTTPException(
            401, "Invalid token", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'}
        )
    return claims
