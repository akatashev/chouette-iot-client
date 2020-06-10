from unittest.mock import patch

from redis import Redis, RedisError
from redis.client import Pipeline

from chouette_iot_client._storages import StoragesFactory


def test_storages_factory_returns_none_on_non_redis_type():
    """
    WHEN: get_storage is called with an unknown storage type.
    THEN: It returns None.
    """
    storage = StoragesFactory.get_storage("celery")
    assert storage is None


def test_redis_storage_returns_none_on_storing_for_redis_error():
    """
    RedisStorage returns None if it can't store a metrics due to a RedisError.

    GIVEN: Redis is not reachable.
    WHEN: There is an attempt to store metric.
    THEN: 'store_metric' method returns None.
    """
    metric = {
        "metric": "test",
        "type": "count",
        "value": 1,
        "timestamp": 3600,
        "tags": {},
    }
    storage = StoragesFactory.get_storage("redis")
    with patch.object(Pipeline, "execute", side_effect=RedisError):
        result = storage.store_metric(metric)
    assert result is None
