import os
import re
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

# Test tenant/app; must be set before the app (and its settings) are imported.
TENANT = "11111111-1111-1111-1111-111111111111"
CLIENT = "22222222-2222-2222-2222-222222222222"
load_dotenv()
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")  # never connected
os.environ.update(
    OIDCProvider="EntraID",
    EntraID_Instance="https://login.microsoftonline.com/",
    EntraID_TenantId=TENANT,
    EntraID_ClientId=CLIENT,
    EntraID_Audience=f"api://{CLIENT}",
    ENABLE_DOCS="false",
)

from app.core import auth  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.security_headers import SECURITY_HEADERS  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
# Local key source instead of the provider's JWKS; a key without "alg" is RS256, like Entra's.
auth._fetch_keys = lambda: {"test-kid": jwt.PyJWK(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True))}

client = TestClient(app)  # not entered as a context manager, so lifespan (DB init) doesn't run
V2_ISS = f"https://login.microsoftonline.com/{TENANT}/v2.0"


def token(key=KEY, kid="test-kid", algorithm="RS256", **claims):
    now = int(time.time())
    claims = {"iss": V2_ISS, "aud": f"api://{CLIENT}", "exp": now + 600, "nbf": now - 10, "scp": "access_as_user"} | claims
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


def cluster(tok):
    # Clustering needs no database, so a 200 here means auth let the request through.
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    return client.post("/molcal/cluster", json=[{"id": str(uuid.uuid4()), "smiles": "CCO"}], headers=headers)


PROTECTED = [
    (method, route.path)
    for route in app.routes
    if isinstance(route, APIRoute) and route.path != "/config/health"
    for method in route.methods
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_every_route_but_health_requires_token(method, path):
    r = client.request(method, re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path))
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"


def test_health_is_anonymous():
    assert client.get("/config/health").status_code == 200


@pytest.mark.parametrize("path", ["/openapi.json", "/docs", "/redoc"])
def test_docs_are_off(path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize(
    "claims",
    [
        {},
        {"iss": f"https://sts.windows.net/{TENANT}/"},  # v1 issuer
        {"aud": CLIENT},  # bare client id audience
        {"scp": None, "roles": ["Chemvault.ReadWrite"]},  # app-only token
        {"exp": int(time.time()) - 60},  # expired, but within clock skew
    ],
)
def test_valid_token_passes(claims):
    assert cluster(token(**claims)).status_code == 200


@pytest.mark.parametrize(
    "tok",
    [
        token(aud="api://some-other-app"),
        # Another tenant's token, signed with Entra's shared keys: rejected in both issuer forms.
        token(iss="https://login.microsoftonline.com/33333333-3333-3333-3333-333333333333/v2.0"),
        token(iss="https://sts.windows.net/33333333-3333-3333-3333-333333333333/"),
        token(exp=int(time.time()) - 400),
        token(nbf=int(time.time()) + 400),
        token(exp=None),
        token(key=OTHER_KEY),  # bad signature
        token(kid="unknown-kid"),
        token(scp=None),  # ID token: neither scp nor roles
        token(key="x" * 32, algorithm="HS256"),
        "not-a-jwt",
    ],
    ids=["audience", "issuer-other-tenant", "issuer-v1-other-tenant", "expired", "not-yet-valid", "no-exp", "signature", "kid", "no-scp-or-roles", "hs256", "garbage"],
)
def test_invalid_token_is_rejected(tok):
    r = cluster(tok)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


def test_keycloak_token(monkeypatch):
    authority = "https://keycloak.example.org/realms/daikon"
    monkeypatch.setattr(auth.settings, "OIDCProvider", "KeyCloak")
    monkeypatch.setattr(auth, "ISSUERS", [authority])
    monkeypatch.setattr(auth, "AUDIENCES", ["daikon-api"])
    # No scp/roles check for KeyCloak, matching DAIKON; issuer and audience must be the configured ones.
    assert cluster(token(iss=authority, aud="daikon-api", scp=None)).status_code == 200
    assert cluster(token(aud="daikon-api", scp=None)).status_code == 401


@pytest.mark.parametrize(
    "env",
    [
        {"OIDCProvider": "Okta"},
        {"OIDCProvider": "EntraID", "EntraID_TenantId": " "},
        {"OIDCProvider": "KeyCloak", "KeyCloak_Authority": "https://keycloak.example.org/realms/daikon"},
    ],
)
def test_incomplete_auth_settings_refuse_to_start(monkeypatch, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings()


@pytest.mark.parametrize("method,path", [("GET", "/config/health"), ("POST", "/molcal/cluster")])  # a 200 and a 401
def test_security_headers(method, path):
    headers = client.request(method, path).headers
    for name, value in SECURITY_HEADERS.items():
        assert headers[name.decode()] == value.decode()
