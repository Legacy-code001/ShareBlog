
import os
from collections.abc import AsyncGenerator


os.environ["DATABASE_URL"]=(
    "postgresql+psycopg://user:passsword@localhost/test_blog"
)
os.environ["BUCKET_NAME"]  = "test-bucket"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"]="eu-north-1"

os.environ["AWS_ACCESS_KEY_ID"]= "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"]="eu-north-1"


import boto3
import pytest
from httpx import ASGtransport, AsyncClient
from moto import mock_aws
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from database import Base, get_db

from main import app

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ(["DATABASE_URL"]),
        poolclass=NullPool,
    )
    return engine
