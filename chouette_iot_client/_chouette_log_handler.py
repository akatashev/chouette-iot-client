"""
ChouetteLogHandler - sends log lines to Chouette to be transferred to Datadog.
"""
import os
from datetime import datetime, timezone
from logging import getLevelName, Formatter, Handler, LogRecord
from typing import Any, Dict, Optional, Tuple

from ._storages import StoragesFactory, RedisStorage
from ._chouette_client import ChouetteClient


class ChouetteLogHandler(Handler):
    """
    ChouetteLogHandler is a custom LogHandler that sends logs to a storage
    so they can be retrieved by Chouette-IoT server, compressed and sent to
    Datadog logs API endpoint.

    Since it's highly likely that not all the logs should be sent to Datadog,
    especially if your connectivity is bad and traffic is expensive, this
    log handler has an environment variable that determines what log message
    should be sent to DataDog.

    This environment variable's name is CHOUETTE_LOG_LEVEL.
    Its default value is NOTSET and it means, that it will send every message
    that it receives.

    Examples:
        1. If your application's standard log level is DEBUG, and Chouette's
        CHOUETTE_LOG_LEVEL variable is not set, all the messages up to DEBUG
        level will be sent to Datadog.
        2. If your application's standard log level is DEBUG, but Chouette's
        CHOUETTE_LOG_LEVEL variable is WARNING, only WARNING, ERROR and
        CRITICAL messages will be sent to Datadog.

    Regardless of your actual log formatter, messages in this handler are
    being send as a JSON for a better data representation in Datadog.
    """

    standard_record_keys: Tuple = (
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "tags",  # Chouette specific, not a standard one.
        "thread",
        "threadName",
        "processName",
        "process",
    )

    def __init__(self, service_name: str):
        """
        Service_name parameter defines both 'ddsource' and 'service' fields
        content in a message that is sent to Datadog.
        """
        super().__init__()

        self.formatter: Formatter = Formatter()
        self.log_level: int = getLevelName(
            os.environ.get("CHOUETTE_LOG_LEVEL", "NOTSET")
        )
        self.storage: Optional[RedisStorage] = StoragesFactory.get_storage("redis")
        self.service_name = service_name

    def emit(self, record: LogRecord) -> None:
        """
        Checks, whether we have a suitable storage object and whether this
        record's level meets our configured log_level.

        If that's true, message is being formatted and stored to a storage.
        Otherwise nothing happens.

        To store data in a non-blocking manner, it gets an executor from
        ChouetteClient.

        Args:
            record: LogRecord instance.
        Returns: None
        """
        if self.storage and record.levelno >= self.log_level:
            log_message = self._format_message(record)
            executor = ChouetteClient.get_executor()
            executor.submit(self.storage.store_log, log_message)

    def _format_message(self, record: LogRecord) -> Dict[str, Any]:
        """
        Takes a LogRecord instance and formats it to a dict that can be sent
        to Datadog. To see all the message attributes in a JSON format in
        Datadog, you needs to send a 'message' as a JSON. All other attributes
        will be shown in the resulting JSON automatically.

        Args:
            record: LogRecord instance.
        Returns: Dict representing a suitable message for Datadog.
        """
        # Tags:
        ddtags = record.__dict__.get("tags", [])
        if isinstance(ddtags, dict):
            ddtags = [f"{key}:{value}" for key, value in ddtags.items()]

        # Base message structure:
        log_message = {
            "date": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "ddsource": self.service_name,
            "ddtags": ddtags,
            "level": record.levelname,
            "message": {"msg": record.msg},
            "service": self.service_name,
        }

        # Adding exception info if we have it:
        if record.exc_info:
            log_message["exc_info"] = self.formatter.formatException(record.exc_info)
        if not log_message.get("exc_info") and record.exc_text:
            log_message["exc_info"] = record.exc_text  # pragma: no cover

        # Adding extras if they are specified:
        for name, value in record.__dict__.items():
            if name not in self.standard_record_keys:
                log_message[name] = value

        return log_message
