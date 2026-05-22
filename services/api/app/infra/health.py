from collections.abc import Awaitable, Callable
from importlib import import_module
from typing import Any

import httpx
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


class DependencyHealth(BaseModel):
    name: str
    status: str
    detail: str | None = None


DependencyHealthChecker = Callable[[], Awaitable[list[DependencyHealth]]]


async def check_postgres() -> DependencyHealth:
    engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
        return DependencyHealth(name="postgres", status="ok")
    except Exception as exc:
        return DependencyHealth(name="postgres", status="error", detail=exc.__class__.__name__)
    finally:
        await engine.dispose()


async def check_redis() -> DependencyHealth:
    redis_asyncio: Any = import_module("redis.asyncio")
    redis: Any = redis_asyncio.Redis.from_url(get_settings().redis_url)
    try:
        await redis.ping()
        return DependencyHealth(name="redis", status="ok")
    except Exception as exc:
        return DependencyHealth(name="redis", status="error", detail=exc.__class__.__name__)
    finally:
        await redis.aclose()


async def check_qdrant() -> DependencyHealth:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{get_settings().qdrant_url.rstrip('/')}/readyz")
        response.raise_for_status()
        return DependencyHealth(name="qdrant", status="ok")
    except Exception as exc:
        return DependencyHealth(name="qdrant", status="error", detail=exc.__class__.__name__)


async def check_dependencies() -> list[DependencyHealth]:
    return [await check_postgres(), await check_redis(), await check_qdrant()]


def get_dependency_health_checker() -> DependencyHealthChecker:
    return check_dependencies
