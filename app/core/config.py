from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Define environment variables with default values
    CHEMVAULT_DATABASE_URL: str
    CHEMVAULT_LOG_LEVEL: str = "DEBUG"
    CHEMVAULT_LOG_JSON: bool = False

    # Pydantic will automatically load from the environment
    model_config = ConfigDict(extra="allow")


# Instantiate the Settings class
settings = Settings()

print(settings.CHEMVAULT_DATABASE_URL)  # This should print the value of CHEMVAULT_DATABASE_URL
