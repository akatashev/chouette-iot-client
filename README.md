# Chouette-IoT-Client

Python client library for [Chouette-IoT](https://github.com/akatashev/chouette-iot) metrics and logs collection agent.

This library can be used in applications to send Datadog-ish like messages to a Chouette-IoT metrics and logs aggregator.  
It uses Redis as a broker. Metrics are being stored in Redis and then they are collected, processed and dispatched by Chouette-IoT.

This library is able to send follow metric types: `count`, `gauge`, `histogram`, `rate` and `set`. `distribution` metric is **NOT** supported.

## Metrics Examples

Usage example:
```
from time import time
from chouette_iot_client import ChouetteClient

# These metrics takes a float as their value:
ChouetteClient.count(metric="my.count.metric", value=1, timestamp=time(), tags={"importance": "high"})
ChouetteClient.increment(metric="my.count.metric", value=1)  # Exactly the same as 'count'
ChouetteClient.decrement(metric="my.count.metric", value=1)  # Means `count` for -value
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

## Logs:

Choette-IoT is also able to aggregate logs, compress them and send to Datadog.  
To handle it, Chouette-Iot-Client has a `ChouetteLogHandler` class. It's a custom log handler that catches log messaged, wraps them in a Datadog-consumable message and stores this message for Chouette-Iot.

This Handler has an environment variable to control what messages should be sent to Datadog. Its name is `CHOUETTE_LOG_LEVEL`. If this variable is set, only messages of a specified (and more important) levels will be sent to Datadog. If it isn't set, all the messages that will be logged will be also sent to Datadog.

Examples:
1. If your default log level is `DEBUG` and you added a `ChouetteLogHandler` to your logger without any `CHOUETTE_LOG_LEVEL` value, all the messages (including DEBUG) will be sent to Datadog.
2. If your default log level is `DEBUG`, but you added a `ChouetteLogHandler` to your logger with a `CHOUETTE_LOG_LEVEL` set to `WARNING`, only `WARNING`, `ERROR` and `CRITICAL` messages will be sent to Datadog.

Code example:
```
import logging
fron chouette_iot_client import ChouetteLogHandler

logger = logging.getLogger("my-module")
logger.setLevel("DEBUG")

chouette_handler = ChouetteLogHandler(service_name="my-little-app")
logger.addHandler(chouette_handler)

# Standard message:
looger.info("Message without extras")

# Message with tags, if you want to add specific tags to it:
logger.info("Message with tags", extras={"tags": {"tag_name": "tag_value"}})

# Message with extras:
logger.info("Message with extras", extras={"client": "Alice", "server": "Bob"})
```

`service_name` parameter determines both `ddsource` and `service` attributes for your log messages in Datadog. 

## License

Chouette-IoT-Client is licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).