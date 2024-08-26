from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Define environment variables with default values
    DATABASE_URL: str
    LOG_LEVEL: str = "DEBUG"
    LOG_JSON: bool = False

    # Configure model to load settings from a .env file and allow extra fields
    model_config = ConfigDict(env_file=".env", extra="allow")


# Instantiate the Settings class, which will load and validate the environment variables
settings = Settings()
