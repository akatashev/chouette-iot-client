# Chouette-IoT-Client

Python client library for [Chouette-IoT](https://github.com/akatashev/chouette-iot) metrics collection agent.

This library can be used in applications to send Datadog-ish like messages to a Chouette-IoT metrics aggregator.  
It uses Redis as a broker. Metrics are being stored in Redis and then they are collected, processed and dispatched by Chouette-IoT.

This library is able to send follow metric types: `count`, `gauge`, `histogram`, `rate` and `set`. `distribution` metric is **NOT** supported.

## Examples

Usage example:
```
from time import time
from chouette_iot_client import ChouetteClient

# These metrics takes a float as their value:
ChouetteClient.count(metric="my.count.metric", value=1, timestamp=time(), tags={"importance": "high"})
ChouetteClient.gauge("my.gauge.metric", 1)
ChouetteClient.histogram("my.histogram.metric", 1.5)
ChouetteClient.rate("my.rate.metric", 1)

# Set metric takes a list or a set as its value:
ChouetteClient.set("my.set.metric.set", {1, 2, 3})
ChouetteClient.set("my.set.metric.list", [1, 2, 3])
```

Metric name `metric` and `value` are mandatory parameters. `timestamp` and `tags` are optional.  
When no `timestamp` is specified, actual time is automatically taken. When no `tags` are specified, empty dict is being sent.

Also ChouetteClient supports `timed` both as a context manager and a decorator:
```
from time import sleep
from chouette_iot_client import timed

# ContextManager:
with timed(metric="my.timed.context_manager", tags={"units": "seconds"}, use_ms=False):
    sleep(1)

# Decorator:
@timed(metric="my.timed.decorator", tags={"units": "milliseconds"}, use_ms=True)
def rest():
    sleep(1)

rest()
```

Both these options will send the same data. But in one case it's going to be a value in seconds (~1.0) and in another case it will be a value in milliseconds (~1000). 

## License

Chouette-IoT-Client is licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).