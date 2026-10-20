from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    database_url: str
    secrete_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    max_upload_size_bytes: int = 5 * 1024 * 1024

    post_per_page: int = 10

    reset_token_expire_minutes: int = 60

    mail_server: str = "localhost"
    mail_port : int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("") 
    mail_from: str = "noreplay@example.com"
    mail_use_tls: bool = True
    frontend_url: str = "http://localhost:8000"

    #S3 configuration
    S3_bucket_name: str
    S3_region: str = "eu-north-1"
    S3_access_key_id: str | None = None
    S3_security_access_key: str | None = None
    S3_endpoint_url: str | None = None



settings = Settings() #load from .env file