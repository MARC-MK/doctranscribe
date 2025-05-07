from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_region: str = "us-east-1"
    s3_bucket: str = "lab-sheets-private"
    s3_endpoint_url: Optional[str] = None  # Allows LocalStack override

    # Default OpenAI model – can be overridden per deployment
    openai_model: str = "gpt-4.1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings() 
