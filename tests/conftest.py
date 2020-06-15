import os

import pytest
from redis import Redis


@pytest.fixture(scope="session")
def metrics_queue():
    """
    Metrics queue name for tests.
    That's an actual raw metrics queue name, but the queue
    consists of two elements:
    1. Sorted Set with record keys named 'chouette:metrics:raw.keys'.
    2. Hash with actual metrics named 'chouette:metrics:raw.values'.
    """
    return "chouette:metrics:raw"


@pytest.fixture(scope="session")
def logs_queue():
    """
    Logs queue name for tests.
    That's an actual logs queue name, but the queue
    consists of two elements:
    1. Sorted Set with record keys named 'chouette:logs:wrapped.keys'.
    2. Hash with actual metrics named 'chouette:logs:wrapped.values'.
    """
    return "chouette:logs:wrapped"


@pytest.fixture(scope="module")
def redis_client():
    """
    Redis client for Redis queue checks.
    """
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    client = Redis(host=redis_host, port=redis_port)
    yield client
    client.flushall()
