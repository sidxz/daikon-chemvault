import os
import re
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import Settings
from app.main import app
from app.middleware.security_headers import SECURITY_HEADERS

TENANT = os.environ["EntraID_TenantId"]  # the test tenant and app registration set in conftest.py
CLIENT = os.environ["EntraID_ClientId"]

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


KC_AUTHORITY = "https://keycloak.example.org/realms/daikon"
KC_CLIENT = "daikon-web"


@pytest.fixture
def keycloak(monkeypatch):
    # Audience == the frontend's client id: the configuration where ID and Logout tokens carry a matching aud too.
    monkeypatch.setattr(auth.settings, "OIDCProvider", "KeyCloak")
    monkeypatch.setattr(auth, "ISSUERS", [KC_AUTHORITY])
    monkeypatch.setattr(auth, "AUDIENCES", [KC_CLIENT])


@pytest.mark.parametrize("typ,status", [("Bearer", 200), ("ID", 401), ("Logout", 401), (None, 401), ("bearer", 401)])
def test_keycloak_accepts_only_access_tokens(keycloak, typ, status):
    # No scp/roles on KeyCloak tokens, matching DAIKON; typ must be exactly "Bearer".
    assert cluster(token(iss=KC_AUTHORITY, aud=KC_CLIENT, scp=None, typ=typ)).status_code == status


def test_keycloak_rejects_other_issuer(keycloak):
    assert cluster(token(aud=KC_CLIENT, scp=None, typ="Bearer")).status_code == 401


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
