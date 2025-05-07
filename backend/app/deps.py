import boto3
from .config import settings
from sqlmodel import Session, create_engine
from fastapi import Request, Depends
import os

# Assume the engine is created and attached to app.state.engine in main.py or here
# For now, create a simple engine for demonstration (update as needed for production)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.s3_endpoint_url,
    ) 