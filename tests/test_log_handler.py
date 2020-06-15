import json
import logging
import time

import pytest

from chouette_iot_client._chouette_log_handler import ChouetteLogHandler


@pytest.fixture(scope="module")
def logger_no_chouette_log_level():
    """
    Fixture for a logger that has no CHOUETTE_LOG_LEVEL parameter
    set, so all its messages are sent to Datadog.
    """
    handler = ChouetteLogHandler(service_name="testService")
    logger = logging.getLogger("noChouetteLogLevel")
    logger.addHandler(handler)
    logger.setLevel("INFO")
    return logger


@pytest.fixture
def logger_with_chouette_log_level(monkeypatch):
    """
    Fixture for a logger that has CHOUETTE_LOG_LEVEL parameter
    set to WARNING, so only WARNING, ERROR and CRITICAL log
    messages are sent to Datadog.
    """
    monkeypatch.setenv("CHOUETTE_LOG_LEVEL", "WARNING")
    logger = logging.getLogger("withChouetteLogLevel")
    logger.setLevel("INFO")
    if not logger.handlers:
        handler = ChouetteLogHandler(service_name="testService")
        logger.addHandler(handler)
    return logger


def test_logger_no_chouette_log_level(
    logger_no_chouette_log_level, redis_client, logs_queue
):
    """
    ChouetteLogHandler without CHOUETTE_LOG_LEVEL stores a message fine.

    GIVEN: There is a logger with log level INFO.
    AND: There is no CHOUETTE_LOG_LEVEL configured.
    WHEN: An INFO message is logged.
    THEN: ChouetteLogHandler stores a log message.
    AND: It has 'date' specified.
    AND: Its tags are correct (empty if no tags were specified).
    AND: Its ddsource and service names are correct.
    AND: Its message is a json.
    AND: Its level is correct.
    """
    redis_client.flushall()
    logger_no_chouette_log_level.info("Test message")
    time.sleep(0.1)
    keys = redis_client.zrange(f"{logs_queue}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    value = redis_client.hget(f"{logs_queue}.values", key)
    assert value
    record = json.loads(value)
    assert "date" in record
    assert record["ddtags"] == []
    assert record["ddsource"] == "testService"
    assert record["service"] == "testService"
    assert record["message"] == {"msg": "Test message"}
    assert record["level"] == "INFO"


def test_logger_no_chouette_log_level_not_sending(
    logger_no_chouette_log_level, redis_client, logs_queue
):
    """
    ChouetteHandler doesn't handle messages that its logger doesn't
    handle itself.

    GIVEN: We have a logger with level INFO.
    AND: There is no CHOUETTE_LOG_LEVEL for ChouetteLogHandler.
    WHEN: logger.debug is called.
    THEN: ChouetteLogHandler doesn't store any metric.
    """
    redis_client.flushall()
    logger_no_chouette_log_level.debug("Test message")
    time.sleep(0.1)
    keys = redis_client.zrange(f"{logs_queue}.keys", 0, -1)
    assert not keys


def test_logger_with_chouette_log_level(
    logger_with_chouette_log_level, redis_client, logs_queue
):
    """
    ChouetteLogHandler with CHOUETTE_LOG_LEVEL stores a message fine.

    GIVEN: There is a logger with log level INFO.
    AND: CHOUETTE_LOG_LEVEL is set to WARNING.
    WHEN: A WARNING message is logged.
    THEN: ChouetteLogHandler stores a log message.
    AND: It has 'date' specified.
    AND: Its tags are pre-formatted for Datadog as ["str:str"].
    AND: Its ddsource and service names are correct.
    AND: Its message is a json.
    AND: Its level is correct.
    AND: It has all specified extra fields.
    """
    redis_client.flushall()
    logger_with_chouette_log_level.warning(
        "Test message", extra={"tags": {"one": "two", "three": "four"}, "code": 89}
    )
    time.sleep(0.1)
    keys = redis_client.zrange(f"{logs_queue}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    value = redis_client.hget(f"{logs_queue}.values", key)
    assert value
    record = json.loads(value)
    assert "date" in record
    assert sorted(record["ddtags"]) == sorted(["one:two", "three:four"])
    assert record["ddsource"] == "testService"
    assert record["service"] == "testService"
    assert record["message"] == {"msg": "Test message"}
    assert record["level"] == "WARNING"
    assert record["code"] == 89


def test_logger_with_chouette_log_level_not_sending(
    logger_with_chouette_log_level, redis_client, logs_queue
):
    """
    ChouetteHandler doesn't handle messages less important than
    its value.

    GIVEN: We have a logger with level INFO.
    AND: CHOUETTE_LOG_LEVEL is set to WARNING.
    WHEN: logger.info is called.
    THEN: ChouetteLogHandler doesn't store any metric.
    """
    redis_client.flushall()
    logger_with_chouette_log_level.info("Test message")
    time.sleep(0.1)
    keys = redis_client.zrange(f"{logs_queue}.keys", 0, -1)
    assert not keys


def test_log_exception(logger_with_chouette_log_level, redis_client, logs_queue):
    """
    ChouetteLogHandler sends Exception info as "exc_info":

    GIVEN: ChouetteLogHandler is configured fine.
    WHEN: A log message with 'exc_info=True' is logged.
    THEN: ChouetteLogHandler stores a log message.
    AND: This message has exception info in its 'exc_info' field.
    """
    exception_string = (
        'raise RuntimeError("Test exception!")\nRuntimeError: Test exception!'
    )
    redis_client.flushall()
    try:
        raise RuntimeError("Test exception!")
    except RuntimeError:
        logger_with_chouette_log_level.error("Exception happened.", exc_info=True)
    time.sleep(0.1)
    keys = redis_client.zrange(f"{logs_queue}.keys", 0, -1)
    assert len(keys) == 1
    key = keys.pop()
    value = redis_client.hget(f"{logs_queue}.values", key)
    assert value
    record = json.loads(value)
    assert exception_string in record["exc_info"]
