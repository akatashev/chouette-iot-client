import pytest
from redis import Redis, RedisError
from redis.client import Pipeline
import os
import json
import time
from concurrent.futures import Future
from chouette_iot_client import ChouetteClient, timed
from chouette_iot_client._storages import StoragesFactory
from unittest.mock import patch

METRICS_QUEUE = "chouette:metrics:raw"


@pytest.fixture(scope="module")
def redis_client():
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    client = Redis(host=redis_host, port=redis_port)
    yield client
    client.flushall()


@pytest.mark.parametrize(
    "method",
    (
        ChouetteClient.count,
        ChouetteClient.gauge,
        ChouetteClient.histogram,
        ChouetteClient.rate,
    ),
)
def test_float_metrics(method, redis_client):
    redis_client.flushall()
    metric_name = "test.float.metric"
    execution_future = method(
        metric=metric_name, value=10, timestamp=3600, tags={"producer": "test"}
    )
    assert isinstance(execution_future, Future)
    result = execution_future.result()
    assert isinstance(result, str)
    keys = redis_client.zrange(f"{METRICS_QUEUE}.keys", 0, -1, withscores=True)
    record = json.loads(redis_client.hget(f"{METRICS_QUEUE}.values", result))
    assert (result.encode(), 3600.0) in keys
    assert record["metric"] == metric_name
    assert record["type"] == method.__name__
    assert record["value"] == 10
    assert record["timestamp"] == 3600.0
    assert record["tags"] == {"producer": "test"}


@pytest.mark.parametrize("value", (["a", "b", "c"], {"a", "b", "c"}))
def test_set_metric(redis_client, value):
    redis_client.flushall()
    metric_name = "test.set.metric"
    before_storing = time.time()
    execution_future = ChouetteClient.set(metric=metric_name, value=value)
    assert isinstance(execution_future, Future)
    result = execution_future.result()
    after_storing = time.time()
    assert isinstance(result, str)
    record = json.loads(redis_client.hget(f"{METRICS_QUEUE}.values", result))
    assert record["metric"] == metric_name
    assert record["type"] == "set"
    assert sorted(record["value"]) == sorted(["a", "b", "c"])
    assert record["tags"] == {}
    timestamp = record["timestamp"]
    assert before_storing < timestamp < after_storing


@pytest.mark.parametrize("use_ms, expected_value", ((True, 100), (False, 0.1)))
def test_timed_metric(redis_client, use_ms, expected_value):
    @timed("test.timed.metric", tags={"producer": "timer"}, use_ms=use_ms)
    def sleep():
        time.sleep(0.1)

    redis_client.flushall()
    sleep()
    time.sleep(0.1)
    keys = redis_client.zrange(f"{METRICS_QUEUE}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    record = json.loads(redis_client.hget(f"{METRICS_QUEUE}.values", key))
    assert record["metric"] == "test.timed.metric"
    assert record["type"] == "histogram"
    assert record["tags"] == {"producer": "timer"}
    assert float("%.3f" % record["value"]) == expected_value


def test_future_returns_none_on_no_storage(monkeypatch):
    monkeypatch.setattr(ChouetteClient, "storage", None)
    execution_future = ChouetteClient.count("test", 1)
    assert execution_future.result() is None


def test_storages_factory_returns_none_on_redis_error():
    with patch.object(Redis, "ping", side_effect=RedisError):
        storage = StoragesFactory.get_storage("redis")
    assert storage is None


def test_redis_storage_returns_none_on_storing_for_redis_error():
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
