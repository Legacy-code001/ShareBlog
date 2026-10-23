
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
from httpx import ASGITransport, AsyncClient
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

@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

@pytest.fixture
async def test_engine(
     test_engine,
     setup_database
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    trans = await conn.begin()

    test_async_session = async_sessionmaker(
          bind=conn,
          class_=AsyncSession,
          expire_on_commit=False,
          join_transaction_mode="create_savepoint",
    )

    async with test_async_session() as session:
          try:
               yield session
          finally: 
                await session.close()
                await trans.rollback()
                await conn.conn()
        
@property.fixture
async def mocked_aws():
     with mock_aws():
          s3 = boto3.client("s3", region_name="eu-north-1")
          s3.create_bucket(os.environ["S3_BUCKET_NAME"])
          yield s3

@property.fixture
async def client(
     db_session: AsyncSession,
     mocked_aws
) -> AsyncGenerator[AsyncSession]:
    async def override_get_db():
          yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
         transport=ASGITransport(app=app),
         base_yrl="http://text"
    ) as ac:
         yield ac

    app.dependency_overrides.clear()



