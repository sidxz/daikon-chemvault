
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    LOG_LEVEL: str = "DEBUG"
    LOG_JSON: bool = False

    model_config = ConfigDict(env_file=".env", extra="allow")

settings = Settings()
