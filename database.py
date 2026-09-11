from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False },
)

AsyncSessionLocal = async_sessionmaker(engine, class=AsyncSession, expire_on_commit=False)

#DeclarativeBase acts as the foundation for your Object-Relational Mapping (ORM) models.
class Base(DeclarativeBase):
    pass

def get_db():
    with AsyncSessionLocal() as session:
        yield session