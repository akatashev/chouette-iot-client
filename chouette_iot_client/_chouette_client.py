"""
ChouetteClient - the main object handling metrics sending.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Dict, List, Optional, Set, Union

from ._storages import RedisStorage, StoragesFactory

logger = logging.getLogger("chouette-iot")

__all__ = ["ChouetteClient"]


class ChouetteClient:
    """
    ChouetteClient is an object that receives metrics requests and sends them
    to a storage.

    To avoid blocking your code, it uses a ThreadPoolExecutor. Any send metric
    request returns a future.
    In some cases it's necessary to send a metric in a blocking way, in this
    case you could just execute 'future.result()' and it will wait till the
    metric is actually sent. Sometimes it helps to avoid locks when a metric
    is sent while another Redis service (like Dramatiq) is starting.

    It uses an executors dictionary to support multiprocessing. It was found
    that child processes can't use a ThreadPoolExecutor that was created by
    their parent if all the slots in an Executor are filled already.
    While the parent process works fine and is ready to use any of these
    threads, child processes see these threads as dead threads and can't
    reuse them or create a new thread (because all the slots are taken).
    It was leading to a situation when a multiprocessing application was
    sending metrics for a half of an hour and then was just stopping.

    With this dictionary ChouetteClient creates a separated executor
    for every process. There is normally no real need for any cleanup, because
    main process doesn't see executors created by its children and these
    executors stop when there processes are stopped.
    """

    executors: Dict[int, ThreadPoolExecutor] = {}
    storage: Optional[RedisStorage] = StoragesFactory.get_storage("redis")

    @classmethod
    def count(
        cls,
        metric: str,
        value: float,
        timestamp: float = None,
        tags: Dict[str, str] = None,
    ) -> Future:
        """
        Handles 'count' metrics.

        Args:
            metric: Metric name.
            value: Metric value as a float.
            timestamp: Metric collection timestamp.
            tags: Metric tags as a dict.
        Return: Future that normally contains this metric's key in a storage.
        """
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
    ) -> Future:
        """
        Handles 'gauge' metrics.

        Args:
            metric: Metric name.
            value: Metric value as a float.
            timestamp: Metric collection timestamp.
            tags: Metric tags as a dict.
        Return: Future that normally contains this metric's key in a storage.
        """
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
    ) -> Future:
        """
        Handles 'rate' metrics.

        Args:
            metric: Metric name.
            value: Metric value as a float.
            timestamp: Metric collection timestamp.
            tags: Metric tags as a dict.
        Return: Future that normally contains this metric's key in a storage.
        """
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
    ) -> Future:
        """
        Handles 'set' metrics.

        Elements in this set or list SHOULD be hashable.
        Unhashable case is handled in _prepare_metric, but it's not the best
        solution.

        Args:
            metric: Metric name.
            value: Metric value as a set or list.
            timestamp: Metric collection timestamp.
            tags: Metric tags as a dict.
        Return: Future that normally contains this metric's key in a storage.
        """
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
    ) -> Future:
        """
        Handles 'histogram' metrics.

        Normally HISTOGRAM metric is being cast into a bunch of different
        metrics on an aggregator's side, so configure it carefully or use
        a custom MetricWrapper for your Chouette server.

        Args:
            metric: Metric name.
            value: Metric value as a float.
            timestamp: Metric collection timestamp.
            tags: Metric tags as a dict.
        Return: Future that normally contains this metric's key in a storage.
        """
        to_store = cls._prepare_metric(
            metric=metric, type="histogram", value=value, timestamp=timestamp, tags=tags
        )
        return cls._store(to_store)

    @classmethod
    def _store(cls, metric: Dict[str, Any]) -> Future:
        """
        Tries to "send" a metric - store it to a broker.

        Normally this future contains the key of the metric in a storage.
        If a metric wasn't stored, its content is None.
        There are two cases when it can be none:
        1. For some reason Storage object wasn't returned.
        2. Storage wasn't able to store data because its broker is down.

        Args:
            metric: Dictionary that contains a metric prepared for storing.
        Returns: Future.
        """
        if not cls.storage:
            empty_future: Future = Future()
            empty_future.set_result(result=None)
            return empty_future
        executor = cls._get_executor()
        future = executor.submit(cls.storage.store_metric, metric)
        return future

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """
        Gets ThreadPoolExecutor from a dict or creates a new one for this
        process.

        Returns: ThreadPoolExecutor.
        """
        pid = os.getpid()
        if pid not in cls.executors:
            logger.debug("Creating new metrics ThreadPoolExecutor for pid %s.", pid)
            cls.executors[pid] = ThreadPoolExecutor(thread_name_prefix="chouette-iot")
        return cls.executors[pid]

    @staticmethod
    def _prepare_metric(**kwargs: Any) -> Dict[str, Any]:
        """
        Takes a metric data and created a dict representing this metric.

        If there are no tags specified, it makes it an empty dict.
        If there is no timestamp specified, it takes actual time.

        For a 'set' metric it has 2 workarounds:
        1. If there is a list specified, it checks whether elements of this
        list are hashable. If they are not - it sends representations of these
        elements instead of them. It's necessary because on the Chouette side
        this data is used in an actual set and unhashable elements would break
        data aggregation.
        2. If there is a set specified, it's converted to a list, because
        Chouette sends a data as a JSON string and sets are not JSON
        compatible.

        Args:
            kwargs: Kwargs where we pass all the metric data.
        Returns: Dictionary that represents a metric.
        """
        value = kwargs.get("value")
        # Unhashable list content workaround:
        if isinstance(value, list):
            try:
                set(value)
            except TypeError:
                value = [repr(elem) for elem in value]
        # If it was a set already, looks like it was hashable.
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
