import json
import time

import pytest

from chouette_iot_client import timed


@pytest.mark.parametrize("use_ms, expected_value", ((True, 100), (False, 0.1)))
def test_timed_decorator(redis_client, use_ms, expected_value, metrics_queue):
    """
    Timed Decorator test:

    GIVEN: There is a function wrapped to a timed decorator.
    WHEN: This function is executed.
    THEN: In a short time data about it appears in both keys and values.
    AND: Its name, type and tags are fine.
    AND: Its value is the expected code execution duration in seconds for
         'use_ms'=False or milliseconds for 'use_ms'=True.
    """

    @timed("test.timed.decorator", tags={"producer": "timer"}, use_ms=use_ms)
    def sleep():
        time.sleep(0.1)

    redis_client.flushall()
    sleep()
    time.sleep(0.1)
    keys = redis_client.zrange(f"{metrics_queue}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", key))
    assert record["metric"] == "test.timed.decorator"
    assert record["type"] == "histogram"
    assert record["tags"] == {"producer": "timer"}
    value = float("%.3f" % record["value"])
    # Due to milliseconds calculation that can show 101 ms:
    assert value in [expected_value, expected_value + 0.01]


@pytest.mark.parametrize("use_ms, expected_value", ((True, 100), (False, 0.1)))
def test_timed_context_manager(redis_client, use_ms, expected_value, metrics_queue):
    """
    Timed Context Manager test.

    GIVEN: There is some code wrapped into a timed context manager.
    WHEN: This code is executed.
    THEN: In a short time data about it appears in both keys and values.
    AND: Its name, type and tags are fine.
    AND: Its value is the expected code execution duration in seconds for
         'use_ms'=False or milliseconds for 'use_ms'=True.
    """
    redis_client.flushall()
    with timed("test.timed.context_manager", tags={"producer": "timer"}, use_ms=use_ms):
        time.sleep(0.1)
    time.sleep(0.1)
    keys = redis_client.zrange(f"{metrics_queue}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    record = json.loads(redis_client.hget(f"{metrics_queue}.values", key))
    assert record["metric"] == "test.timed.context_manager"
    assert record["type"] == "histogram"
    assert record["tags"] == {"producer": "timer"}
    value = float("%.3f" % record["value"])
    # Due to milliseconds calculation that can show 101 ms:
    assert value in [expected_value, expected_value + 0.01]
