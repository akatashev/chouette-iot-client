import json
import logging
import time
from typing import Any, Dict, Optional
from uuid import uuid4

from redis import Redis, RedisError

logger = logging.getLogger("chouette-iot")


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
        collected_at = int(metric.get("timestamp", time.time()))
        pipeline = self.pipeline()
        pipeline.zadd(f"{self.metrics_queue}.keys", {key: collected_at})
        pipeline.hset(f"{self.metrics_queue}.values", key, value)
        try:
            pipeline.execute()
        except (RedisError, OSError):
            logger.warning(
                "Could not store a metric %s: %s to Redis.", key, value, exc_info=True
            )
            return None
        logger.debug("Successfully stored a metric %s: %s to Redis.", key, value)
        return key
