"""
Chouette storages file.
For now it's just a RedisStorage.
It could be made more enterprise-y with a Storage interface, but it'll
work for now as is.
"""
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from redis import Redis, RedisError

logger = logging.getLogger("chouette-iot")

__all__ = ["RedisStorage", "StoragesFactory"]


class StoragesFactory:
    """
    Storages factory that creates a storage of a desired type.
    At the moment there is a single storage type that is Redis.
    """

    @staticmethod
    def get_storage(storage_type: str):
        """
        Generates a storage.

        Returns: RedisStorage instance or None if redis is not reachable.
        """
        if storage_type.lower() == "redis":
            redis_host = os.environ.get("REDIS_HOST", "redis")
            redis_port = int(os.environ.get("REDIS_PORT", "6379"))
            redis_storage = RedisStorage(host=redis_host, port=redis_port)
            return redis_storage
        return None


class RedisStorage(Redis):
    """
    RedisStorage is a wrapper around Redis that stores data into
    its queues.
    """

    metrics_queue = "chouette:metrics:raw"
    logs_queue = "chouette:logs:wrapped"

    def store_metric(self, metric: Dict[str, Any]) -> Optional[str]:
        """
        Stores a metric to Redis.

        Args:
            metric: Metric as a dictionary.
        Return: Message key or None if message was not stored successfully.
        """
        collected_at = metric["timestamp"]
        return self._store(metric, self.metrics_queue, collected_at)

    def store_log(self, log_message: Dict[str, Any]) -> Optional[str]:
        """
        Stores a log message to Redis.

        Args:
            log_message: Log message as a dictionary.
        Return: Message key or None if message was not stored successfully.
        """
        py36_date = re.sub(r"\+(\d{2}):(\d{2})", r"+\1\2", log_message["date"])
        collected_at = datetime.strptime(
            py36_date, "%Y-%m-%dT%H:%M:%S.%f%z"
        ).timestamp()
        return self._store(log_message, self.logs_queue, collected_at)

    def _store(
        self, record: Dict[str, Any], queue: str, timestamp: float
    ) -> Optional[str]:
        """
        Actually stores a message to Redis.

        It generates a key as a unique string, casts a record into json and
        stores it to a specified queue in Redis under a specified timestamp.

        Args:
            record: Record to store as a dict.
            queue: Queue name.
            timestamp: Unix timestamp for a keys sorted set.
        Return: Message key or None if message was not stored successfully.
        """
        key = str(uuid4())
        value = json.dumps(record)
        pipeline = self.pipeline()
        pipeline.zadd(f"{queue}.keys", {key: timestamp})
        pipeline.hset(f"{queue}.values", key, value)
        try:
            pipeline.execute()
        except (RedisError, OSError) as error:
            logger.warning(
                "Could not store a record %s: %s to queue %s. Error: %s",
                key,
                value,
                queue,
                error,
            )
            return None
        logger.debug(
            "Successfully stored a record %s: %s to queue %s.", key, value, queue
        )
        return key
