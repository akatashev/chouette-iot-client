"""
ChouetteClient module entry point.
"""
from typing import Callable, Dict

from ._chouette_client import ChouetteClient
from ._timed import TimedContentManagerDecorator

__all__ = ["ChouetteClient", "timed"]


def timed(metric: str, tags: Dict[str, str] = None, use_ms: bool = False) -> Callable:
    """
    A decorator/content managerthat can be used to calculate the duration
    of code execution. Sends a HISTOGRAM metric.

    Args:
        metric: Name of the metric.
        tags: Tags as a dict.
        use_ms: Whether values should be sent as seconds or milliseconds.
    Returns: Decorator object.
    """
    return TimedContentManagerDecorator(metric, tags, use_ms)
