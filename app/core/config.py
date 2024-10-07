from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Define environment variables with default values
    DATABASE_URL: str
    LOG_LEVEL: str = "DEBUG"
    LOG_JSON: bool = False

    # Pydantic will automatically load from the environment
    model_config = ConfigDict(extra="allow")


# Instantiate the Settings class
settings = Settings()

print(settings.DATABASE_URL)  # This should print the value of DATABASE_URL
