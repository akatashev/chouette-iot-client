"""
TimedContentManagerDecorator implementation is based on original Datadog code:
https://github.com/DataDog/datadogpy/blob/master/datadog/dogstatsd/context.py
"""
from functools import wraps
from time import time
from typing import Any, Callable, Dict, Optional

from ._chouette_client import ChouetteClient


class TimedContentManagerDecorator:
    """
    A decorator that reports the duration of a function call or context
    execution.
    It doesn't have a fancy coroutine compatibility like the original
    Datadog TimedContextManagerDecorator.
    Basically, it's its "cheap and nasty" version.
    """

    def __init__(self, metric: str, tags: Dict[str, str] = None, use_ms: bool = False):
        self.metric = metric
        self.tags = tags
        self.use_ms = use_ms
        self._started = time()  # Just to make mypy happier.

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator that sends to Chouette the duration of a function call.

        Args:
            func: Function whose duration should be stored.
        Returns: Decorated function.
        """

        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any):
            """
            Wraps a function into our calculate-and-send logic.
            """
            started = time()
            try:
                return func(*args, *kwargs)
            finally:
                self._send(started)

        return wrapped

    def _send(self, started: float) -> None:
        """
        Calculates actual execution duration time.
        Sends a value in seconds if use_ms was set to False or in
        milliseconds if it was set to True.

        This method sends a HISTOGRAM metric. If you want to avoid sending
        all 5 default metrics corresponding to a HISTOGRAM metric type, you
        need to configure your Chouette MetricWrapper by setting appropriate
        HISTOGRAM settings or using a custom MetricWrapper.

        This function is one big side effect and it returns nothing.

        Args:
            started: Unix timestamp of a moment when execution was started.
        Return: None.
        """
        duration = time() - started
        value = int(round(1000 * duration)) if self.use_ms else duration
        ChouetteClient.histogram(self.metric, value, tags=self.tags)

    def __enter__(self) -> "TimedContentManagerDecorator":
        """
        Content manager entry point.
        """
        self._started = time()
        return self

    def __exit__(
        self, metric_type: Optional[str], value: Optional[float], traceback: Any
    ) -> None:
        """
        Actually sends execution time to ChouetteClient.
        """
        self._send(self._started)
