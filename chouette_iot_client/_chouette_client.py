import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List, Optional, Set, Union

from redis import RedisError

from ._storages import RedisStorage

logger = logging.getLogger("chouette-iot")


class ChouetteClient:
    executors: Dict[int, ThreadPoolExecutor] = {}
    storage: Optional[RedisStorage] = None

    def __new__(cls):
        redis_host = os.environ.get("REDIS_HOST", "redis")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        redis_storage = RedisStorage(host=redis_host, port=redis_port)
        try:
            redis_storage.ping()
            cls.storage: RedisStorage = redis_storage
        except RedisError:
            logger.warning(
                "Redis %s:%s can't be pinged. Metrics WON'T be sent.",
                redis_host,
                redis_port,
            )

    @classmethod
    def count(cls, metric, value: float, timestamp=None, tags=None):
        to_store = cls._prepare_metric(
            metric=metric, type="count", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def gauge(cls, metric, value: float, timestamp=None, tags=None):
        to_store = cls._prepare_metric(
            metric=metric, type="gauge", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def rate(cls, metric, value: float, timestamp=None, tags=None):
        to_store = cls._prepare_metric(
            metric=metric, type="rate", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def set(cls, metric, value: Union[List, Set], timestamp=None, tags=None):
        to_store = cls._prepare_metric(
            metric=metric, type="set", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def histogram(cls, metric, value: float, timestamp=None, tags=None):
        to_store = cls._prepare_metric(
            metric=metric, type="histogram", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def _store(cls, metric) -> Future:
        # If we don't store any metrics we return a Future containing none.
        if not cls.storage:
            future: Future = Future()
            future.set_result(None)
            return future
        # Actual future handling:
        executor = cls._get_executor()
        future = executor.submit(cls.storage.store_metric, metric)
        return future

    @classmethod
    def _get_executor(cls):
        pid = os.getpid()
        if pid not in cls.executors:
            logger.debug("Creating new metrics ThreadPoolExecutor for pid %s.", pid)
            cls.executors[pid] = ThreadPoolExecutor(thread_name_prefix="chouette-iot")
        return cls.executors[pid]

    @staticmethod
    def _prepare_metric(**kwargs):
        value = kwargs.get("value")
        if isinstance(value, set):
            value = list(value)
        metric = {
            "metric": kwargs.get("metric"),
            "type": kwargs.get("type"),
            "value": value,
            "timestamp": kwargs.get("timestamp", time.time()),
            "tags": kwargs.get("tags", {}),
        }
        return metric
