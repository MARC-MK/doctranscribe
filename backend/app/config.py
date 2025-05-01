from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_region: str = "us-east-1"
    s3_bucket: str = "lab-sheets-private"
    s3_endpoint_url: str | None = None  # Allows LocalStack override

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings() 