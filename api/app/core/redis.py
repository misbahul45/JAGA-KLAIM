from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    settings = get_settings()
    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password.get_secret_value(),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


def redis_dependency() -> Redis:
    return get_redis()


RedisDep = Annotated[Redis, Depends(redis_dependency)]
