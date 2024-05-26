#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false

"""Openstack Swift Exporter"""

import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict
from wsgiref.simple_server import make_server

import pytz
import requests
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, CollectorRegistry, Metric
from prometheus_client.exposition import _bake_output, _SilentHandler, parse_qs
from swiftclient.exceptions import ClientException
from swiftclient.service import SwiftError, SwiftService


# OWASP ZAP ENHANCEMENT
def make_wsgi_app(
    registry: CollectorRegistry = REGISTRY, disable_compression: bool = False
) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        # Prepare parameters
        accept_header = environ.get("HTTP_ACCEPT")
        accept_encoding_header = environ.get("HTTP_ACCEPT_ENCODING")
        params = parse_qs(environ.get("QUERY_STRING", ""))
        headers = [
            ("Server", ""),
            ("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        if environ["PATH_INFO"] == "/":
            status = "301 Moved Permanently"
            headers.append(("Location", "/metrics"))
            output = b""
        elif environ["PATH_INFO"] == "/favicon.ico":
            status = "200 OK"
            output = b""
        elif environ["PATH_INFO"] == "/metrics":
            status, tmp_headers, output = _bake_output(
                registry,
                accept_header,
                accept_encoding_header,
                params,
                disable_compression,
            )
            headers += tmp_headers
        else:
            status = "404 Not Found"
            output = b""
        start_response(status, headers)
        return [output]

    return prometheus_app


def start_wsgi_server(
    port: int,
    addr: str = "0.0.0.0",  # nosec B104
    registry: CollectorRegistry = REGISTRY,
) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()


start_http_server = start_wsgi_server

# OPENSTACK SWIFT AUTHENTICATION CASE
OS_AUTH = [
    {
        "auth_type": "legacy",
        "auth_version": "1.0",
        "envs": [
            "ST_AUTH_VERSION",
            "ST_AUTH",
            "ST_USER",
            "ST_KEY",
            "OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER",
        ],
    },
    {
        "auth_type": "keystone-v2",
        "auth_version": "2.0",
        "envs": [
            "ST_AUTH_VERSION",
            "OS_USERNAME",
            "OS_PASSWORD",
            "OS_TENANT_NAME",
            "OS_AUTH_URL",
            "OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER",
        ],
    },
    {
        "auth_type": "keystone-v3",
        "auth_version": "3",
        "envs": [
            "ST_AUTH_VERSION",
            "OS_USERNAME",
            "OS_PASSWORD",
            "OS_PROJECT_NAME",
            "OS_PROJECT_DOMAIN_NAME",
            "OS_AUTH_URL",
            "OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER",
        ],
    },
]

# OPENSTACK SWIFT EXPORTER VARIABLES
OPENSTACK_SWIFT_EXPORTER_NAME = os.environ.get(
    "OPENSTACK_SWIFT_EXPORTER_NAME", "openstack-swift-exporter"
)
OPENSTACK_SWIFT_EXPORTER_LOGLEVEL = os.environ.get(
    "OPENSTACK_SWIFT_EXPORTER_LOGLEVEL", "INFO"
).upper()
OPENSTACK_SWIFT_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")
OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER = os.environ.get(
    "OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER"
)
OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS = {
    "delimiter": os.environ.get("OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS_DELIMITER"),
    "prefix": os.environ.get("OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS_PREFIX"),
}  # type: dict
try:
    OPENSTACK_SWIFT_EXPORTER_PORT = int(
        os.environ.get("OPENSTACK_SWIFT_EXPORTER_PORT", "8124").upper()
    )
except ValueError:
    logging.error("OPENSTACK_SWIFT_EXPORTER_PORT must be int !")
    os._exit(1)

# LOGGING CONFIGURATION
logging.getLogger("swiftclient").setLevel(logging.CRITICAL)
try:
    pytz.timezone(OPENSTACK_SWIFT_EXPORTER_TZ)
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone(OPENSTACK_SWIFT_EXPORTER_TZ)
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level=OPENSTACK_SWIFT_EXPORTER_LOGLEVEL,
    )
except pytz.exceptions.UnknownTimeZoneError:
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone("Europe/Paris")
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("TZ invalid : %s !", OPENSTACK_SWIFT_EXPORTER_TZ)
    os._exit(1)
except ValueError:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("OPENSTACK_SWIFT_EXPORTER_LOGLEVEL invalid !")

# MANAGE AUTHENTICATION TYPE
AUTH_TYPE = os.environ.get("AUTH_TYPE", "keystone-v3")

if AUTH_TYPE not in [auth["auth_type"] for auth in OS_AUTH]:
    logging.error(
        "Invalid AUTH_TYPE environment variable (available: %s)",
        ", ".join([str(auth["auth_type"]) for auth in OS_AUTH]),
    )
    os._exit(1)
logging.debug("AUTH_TYPE: %s", AUTH_TYPE)

ST_AUTH_VERSION = [
    auth["auth_version"] for auth in OS_AUTH if AUTH_TYPE == auth["auth_type"]
][0]
os.environ["ST_AUTH_VERSION"] = str(ST_AUTH_VERSION)

# MANAGE _OPTS DICT
_OPTS: Dict[Any, Any] = {}
_OPTS["auth_version"] = ST_AUTH_VERSION
for environment in [auth["envs"] for auth in OS_AUTH if AUTH_TYPE == auth["auth_type"]][
    0
]:
    if os.environ.get(environment) is not None:
        logging.debug("%s: %s", environment, os.environ.get(environment))
        _OPTS[environment.lower()] = str(os.environ.get(environment))
    else:
        logging.error("%s environment variable must exist !", environment)
        os._exit(1)

_OPTS["retries"] = int(os.environ.get("OPENSTACK_SWIFT_EXPORTER_RETRIES", 1))

# METRICS CONFIGURATION
METRICS = [
    {
        "name": "bytes",
        "description": "Openstack Swift Object Size in bytes.",
        "type": "gauge",
    },
    {
        "name": "last_modified",
        "description": "Openstack Swift Object Last Modified Datetime.",
        "type": "counter",
    },
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors["python_gc_objects_collected_total"])


class OpenstackSwiftCollector:
    """Openstack Swift Collector"""

    def __init__(self):
        """Init"""
        pass

    @staticmethod
    def _list_swift_container():
        """Generate List Of Container Object"""
        swift_objects = []
        with SwiftService(options=_OPTS) as swift:
            list_parts_gen = swift.list(
                container=OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER,
                options=OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS,
            )
            try:
                for page in list_parts_gen:
                    if page["success"]:
                        for item in page["listing"]:
                            swift_object = {}
                            swift_object["bytes"] = item["bytes"]
                            swift_object["name"] = item["name"]
                            swift_object["last_modified"] = datetime.fromisoformat(
                                item["last_modified"]
                            ).timestamp()
                            swift_objects.append(swift_object)
                    else:
                        raise page["error"]
            except SwiftError as exception:
                logging.error(exception.value)
                os._exit(1)
            except ClientException as exception:
                logging.error(exception.msg)
                os._exit(1)
            except requests.exceptions.ConnectionError as exception:
                logging.error(exception)
                os._exit(1)
        return swift_objects

    def get_metrics(self):
        """Generate Prometheus Metrics"""
        metrics = []
        swift_objects = self._list_swift_container()
        logging.debug(swift_objects)
        for swift_object in swift_objects:
            labels = {
                "job": OPENSTACK_SWIFT_EXPORTER_NAME,
                "container": OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER,
                "name": swift_object["name"],
            }
            for key, value in swift_object.items():
                if key in [i["name"] for i in METRICS]:
                    description = [
                        i["description"] for i in METRICS if key == i["name"]
                    ][0]
                    metric_type = [i["type"] for i in METRICS if key == i["name"]][0]
                    metrics.append(
                        {
                            "name": f"openstack_swift_object_{key.lower()}",
                            "value": float(value),
                            "description": description,
                            "type": metric_type,
                            "labels": labels,
                        }
                    )
        logging.debug(metrics)
        logging.info(
            "Retrieve %s object(s) in container %s.",
            len(swift_objects),
            OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER,
        )
        return metrics

    def collect(self):
        """Collect Prometheus Metrics"""
        metrics = self.get_metrics()
        for metric in metrics:
            prometheus_metric = Metric(
                metric["name"], metric["description"], metric["type"]
            )
            prometheus_metric.add_sample(
                metric["name"], value=metric["value"], labels=metric["labels"]
            )
            yield prometheus_metric


def main():
    """Main Function"""
    logging.info(
        "Starting Openstack Swift Exporter on port %s.", OPENSTACK_SWIFT_EXPORTER_PORT
    )
    logging.debug("OPENSTACK_SWIFT_EXPORTER_PORT: %s.", OPENSTACK_SWIFT_EXPORTER_PORT)
    logging.debug("OPENSTACK_SWIFT_EXPORTER_NAME: %s.", OPENSTACK_SWIFT_EXPORTER_NAME)
    start_http_server(OPENSTACK_SWIFT_EXPORTER_PORT)
    REGISTRY.register(OpenstackSwiftCollector())
    # Infinite Loop
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
