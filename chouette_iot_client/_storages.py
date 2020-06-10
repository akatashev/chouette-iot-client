"""
Chouette storages file.
For now it's just a RedisStorage.
It could be made more enterprise-y with a Storage interface, but it'll
work for now as is.
"""
import json
import logging
import os
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

    def store_metric(self, metric: Dict[str, Any]) -> Optional[str]:
        """
        Stores a metric to Redis.

        It generates a metric key as a random UID4 and stores this key to a
        sorted set with its timestamp and the metric's value to a hash with
        the same key.

        Args:
            metric: Metric as a dictionary.
        Return: Message key or None if message was not stored successfully.
        """
        key = str(uuid4())
        value = json.dumps(metric)
        collected_at = metric["timestamp"]
        pipeline = self.pipeline()
        pipeline.zadd(f"{self.metrics_queue}.keys", {key: collected_at})
        pipeline.hset(f"{self.metrics_queue}.values", key, value)
        try:
            pipeline.execute()
        except (RedisError, OSError) as error:
            logger.warning(
                "Could not store a metric %s: %s to Redis. Error: %s", key, value, error
            )
            return None
        logger.debug("Successfully stored a metric %s: %s to Redis.", key, value)
        return key
