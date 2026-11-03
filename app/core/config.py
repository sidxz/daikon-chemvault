from pydantic_settings import BaseSettings
from typing import Literal
from pydantic import ConfigDict, model_validator


class Settings(BaseSettings):
    # Define environment variables with default values
    DATABASE_URL: str
    LOG_LEVEL: str = "DEBUG"
    LOG_JSON: bool = False

    # Bearer-token auth, same values as DAIKON's OIDCProvider, EntraID_* and Keycloak_* settings.
    # The chosen provider's settings are required: the app refuses to start without them, there is no auth-off mode.
    OIDCProvider: Literal["EntraID", "KeyCloak"]
    EntraID_Instance: str = ""
    EntraID_TenantId: str = ""
    EntraID_ClientId: str = ""
    EntraID_Audience: str = ""
    KeyCloak_Authority: str = ""
    KeyCloak_Audience: str = ""

    # Serve /docs, /redoc and /openapi.json (anonymously). Leave off in production.
    ENABLE_DOCS: bool = False

    @model_validator(mode="after")
    def _require_provider_settings(self):
        required = {
            "EntraID": ["EntraID_Instance", "EntraID_TenantId", "EntraID_ClientId", "EntraID_Audience"],
            "KeyCloak": ["KeyCloak_Authority", "KeyCloak_Audience"],
        }[self.OIDCProvider]
        missing = [name for name in required if not getattr(self, name).strip()]
        if missing:
            raise ValueError(f"OIDCProvider={self.OIDCProvider} needs {', '.join(missing)}")
        return self

    # Pydantic will automatically load from the environment
    model_config = ConfigDict(extra="allow")


# Instantiate the Settings class
settings = Settings()
