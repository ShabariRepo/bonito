from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


async def _init_pgvector_connection(conn):
    """Register pgvector 'vector' type codec with asyncpg on each new connection.
    
    Without this, asyncpg raises 'Unknown PG numeric type: 24578' when reading
    vector columns because it doesn't know pgvector's custom type.
    """
    await conn.set_type_codec(
        "vector",
        encoder=str,
        decoder=lambda v: [float(x) for x in v[1:-1].split(",")] if v else [],
        schema="public",
        format="text",
    )


# Create engine with connection pooling configuration
engine = create_async_engine(
    settings.get_async_database_url(), 
    echo=False,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args={
        "init": _init_pgvector_connection,  # Register vector type on every new asyncpg connection
    },
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# Global database reference for cleanup
database = engine


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """Standalone async context manager for use outside of FastAPI dependencies."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
