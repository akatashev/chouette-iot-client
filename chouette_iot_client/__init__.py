"""
Chouette clint module facade and definition.
"""
from concurrent.futures import Future
from typing import Callable, Dict, Union

# pylint: disable=redefined-builtin
from ._chouette_client import ChouetteClient
from ._timed_decorator import TimedDecorator

__all__ = ["ChouetteClient", "timed"]


def timed(metric: str, tags: Dict[str, str] = None, use_ms: bool = False) -> Callable:
    """
    A decorator that can be used to calculate the duration of code execution.
    Sends a HISTOGRAM metric.

    Args:
        metric: Name of the metric.
        tags: Tags as a dict.
        use_ms: Whether values should be sent as seconds or milliseconds.
    Returns: Decorator object.
    """
    return TimedDecorator(metric, tags, use_ms)
