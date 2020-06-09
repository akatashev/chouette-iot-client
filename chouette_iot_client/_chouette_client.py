import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Dict, List, Optional, Set, Union

from ._storages import RedisStorage, StoragesFactory

logger = logging.getLogger("chouette-iot")

__all__ = ["ChouetteClient"]


class ChouetteClient:
    executors: Dict[int, ThreadPoolExecutor] = {}
    storage: Optional[RedisStorage] = StoragesFactory.get_storage("redis")

    @classmethod
    def count(
        cls,
        metric: str,
        value: float,
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ):
        to_store = cls._prepare_metric(
            metric=metric, type="count", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def gauge(
        cls,
        metric: str,
        value: float,
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ):
        to_store = cls._prepare_metric(
            metric=metric, type="gauge", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def rate(
        cls,
        metric: str,
        value: float,
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ):
        to_store = cls._prepare_metric(
            metric=metric, type="rate", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def set(
        cls,
        metric: str,
        value: Union[List, Set],
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ):
        to_store = cls._prepare_metric(
            metric=metric, type="set", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def histogram(
        cls,
        metric: str,
        value: float,
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ):
        to_store = cls._prepare_metric(
            metric=metric, type="histogram", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def _store(cls, metric: Dict[str, Any]) -> Future:
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
    def _get_executor(cls) -> ThreadPoolExecutor:
        pid = os.getpid()
        if pid not in cls.executors:
            logger.debug("Creating new metrics ThreadPoolExecutor for pid %s.", pid)
            cls.executors[pid] = ThreadPoolExecutor(thread_name_prefix="chouette-iot")
        return cls.executors[pid]

    @staticmethod
    def _prepare_metric(**kwargs: Any) -> Dict[str, Any]:
        value = kwargs.get("value")
        if isinstance(value, set):
            value = list(value)
        timestamp = kwargs.get("timestamp")
        if not timestamp:
            timestamp = time.time()
        tags = kwargs.get("tags")
        if not tags:
            tags = {}
        metric = {
            "metric": kwargs.get("metric"),
            "type": kwargs.get("type"),
            "value": value,
            "timestamp": timestamp,
            "tags": tags,
        }
        return metric
