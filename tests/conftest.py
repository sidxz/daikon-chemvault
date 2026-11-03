import os

from dotenv import load_dotenv

# Settings are read when app modules are first imported, so set them before any test module imports app code.
load_dotenv()
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")  # not connected by default
os.environ.update(
    OIDCProvider="EntraID",
    EntraID_Instance="https://login.microsoftonline.com/",
    EntraID_TenantId="11111111-1111-1111-1111-111111111111",
    EntraID_ClientId="22222222-2222-2222-2222-222222222222",
    EntraID_Audience="api://22222222-2222-2222-2222-222222222222",
    ENABLE_DOCS="false",
)
