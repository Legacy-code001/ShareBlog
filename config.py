from pydantic import SecreteStr
from pydantic_settings import BaseSettings, SettingConfigDict



class Settings(BaseSettings):
    model_config = SettingConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    secrete_key: SecreteStr
    algorithm: str "HS256"
    access_token_expire_minutes: int = 30

    settings = Settings() #load from .env file
    