import json
import time
from concurrent.futures import Future

import pytest

from chouette_iot_client import ChouetteClient
from chouette_iot_client._storages import StoragesFactory
from unittest.mock import patch


@pytest.mark.parametrize(
    "method",
    (
        ChouetteClient.count,
        ChouetteClient.gauge,
        ChouetteClient.histogram,
        ChouetteClient.rate,
    ),
)
def test_float_metrics(method, redis_client, metrics_queue):
    """
    Tests 'float' metrics like 'count', 'gauge', 'histogram' and 'rate'.

    GIVEN: We have a metric of a float value.
    AND: RedisStorage works fine.
    WHEN: We send this metric by running a corresponding method.
    THEN: A future is returned.
    AND: This future contains a string.
    AND: This string can be found in the 'keys' sorted set with a
         correct timestamp.
    AND: In the 'values' hash there is a metric value under this key.
    AND: All the data in this metric is correct, including type.
    """
    redis_client.flushall()
    metric_name = "test.float.metric"
    execution_future = method(
        metric=metric_name, value=10, timestamp=3600, tags={"producer": "test"}
    )
    assert isinstance(execution_future, Future)
    result = execution_future.result()
    assert isinstance(result, str)
    keys = redis_client.zrange(f"{metrics_queue}.keys", 0, -1, withscores=True)
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", result))
    assert (result.encode(), 3600.0) in keys
    assert record["metric"] == metric_name
    assert record["type"] == method.__name__
    assert record["value"] == 10
    assert record["timestamp"] == 3600.0
    assert record["tags"] == {"producer": "test"}


@pytest.mark.parametrize("method", (ChouetteClient.increment, ChouetteClient.decrement))
def test_increment_decrement_metrics(redis_client, metrics_queue, method):
    """
    Tests 'increment' and 'decrement' methods.

    'Increment' and 'decrement' are aliases for a 'count' method used in
    DogstatsD. 'increment' sends a positive value just like 'count' does
    while 'decrement' sends a negative value.

    GIVEN: We send a value 2 by an increment or decrement method.
    WHEN: This method is called.
    THEN: A record with a metric name appears in a storage.
    AND: The type of this metric is "count".
    AND: Its value is 2 for 'increment'.
    OR: It's value is -2 for 'decrement'.
    """
    expected_result = 2
    if method.__name__ == "decrement":
        expected_result *= -1
    redis_client.flushall()
    metric_name = "test.metric.count.datadogstyle"
    execution_future = method(metric=metric_name, value=2)
    result = execution_future.result()
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", result))
    assert record["metric"] == metric_name
    assert record["type"] == "count"
    assert record["value"] == expected_result


@pytest.mark.parametrize("value", (["a", "b", "c"], {"a", "b", "c"}))
def test_set_metric(redis_client, value, metrics_queue):
    """
    Tests 'set' metric of hashable elements.

    GIVEN: We have a list or a set of hashable elements for a metric.
    AND: RedisStorage works fine.
    WHEN: We send this metric by running a corresponding method.
    THEN: A future is returned.
    AND: This future contains a string.
    AND: This string can be found in the 'keys' sorted set with a
         correct timestamp.
    AND: In the 'values' hash there is a metric value under this key.
    AND: Type, metric name, tags and timestamp are correct.
    AND: Its value is a list of elements regardless of whether original
         data was a list or a set.
    """
    redis_client.flushall()
    metric_name = "test.set.metric"
    before_storing = time.time()
    execution_future = ChouetteClient.set(metric=metric_name, value=value)
    assert isinstance(execution_future, Future)
    result = execution_future.result()
    after_storing = time.time()
    assert isinstance(result, str)
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", result))
    assert record["metric"] == metric_name
    assert record["type"] == "set"
    assert sorted(record["value"]) == sorted(["a", "b", "c"])
    assert record["tags"] == {}
    timestamp = record["timestamp"]
    assert before_storing < timestamp < after_storing


def test_set_uhashable_metric(redis_client, metrics_queue):
    """
    Tests 'set' metric of unhashable elements.

    GIVEN: We have a list of unhashable elements for a metric.
    AND: RedisStorage works fine.
    WHEN: We send this metric by running a corresponding method.
    THEN: This metric's value in a storage is a list of string
          representations of these unhashable elements.
    """
    redis_client.flushall()
    metric_name = "test.set.metric"
    execution_future = ChouetteClient.set(
        metric=metric_name, value=[{"a": "b"}, {"c": "d"}]
    )
    result = execution_future.result()
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", result))
    assert sorted(record["value"]) == sorted(["{'a': 'b'}", "{'c': 'd'}"])


def test_future_returns_none_on_no_storage(monkeypatch):
    """
    Tests a situation when there is no storage.

    GIVEN: For some reason storage is None.
    WHEN: There is an attempt to send a metric.
    THEN: Returned future's result is None.
    """
    monkeypatch.setattr(ChouetteClient, "storage", None)
    with patch.object(StoragesFactory, "get_storage", return_value=None):
        execution_future = ChouetteClient.count("test", 1)
    assert execution_future.result() is None
