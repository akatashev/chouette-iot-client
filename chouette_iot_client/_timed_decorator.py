from functools import wraps
from time import time
from typing import Any, Callable, Dict

from ._chouette_client import ChouetteClient


class TimedDecorator:
    __slots__ = ("metric", "tags", "use_ms", "_start")

    def __init__(self, metric: str, tags: Dict[str, str] = None, use_ms: bool = False):
        self.metric = metric
        self.tags = tags
        self.use_ms = use_ms
        self._start = None

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any):
            started = time()
            try:
                return func(*args, *kwargs)
            finally:
                self._store(started)

        return wrapped

    def _store(self, started: float):
        duration = time() - started
        value = int(round(1000 * duration)) if self.use_ms else duration
        ChouetteClient.histogram(self.metric, value, tags=self.tags)

    def __enter__(self):
        if not self.metric:
            raise TypeError("Cannot used timed without a metric!")
        self._start = time()
        return self

    def __exit__(self, metric_type, value, traceback):
        # Report the elapsed time of the context manager.
        self._store(self._start)

    def start(self):
        self.__enter__()

    def stop(self):
        self.__exit__(None, None, None)
