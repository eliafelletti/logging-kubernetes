import logging
import sys
from pythonjsonlogger import jsonlogger
from datetime import datetime

'''
    This module sets up logging for the application using the python-json-logger library. 
    It configures a JSON formatter that includes a timestamp, log level, and message.
'''

def setup_logging():
    # In k8s, logs are typically collected from stdout, so we set up a StreamHandler to output logs to stdout
    # Loki will read from stdout and parse the JSON logs for better querying and visualization in Grafana
    log_handler = logging.StreamHandler(sys.stdout)

    # Configure the JSON formatter to include timestamp, log level, and message
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(method)s %(path)s',
        json_ensure_ascii=False
    )

    formatter.default_time_format = '%Y-%m-%dT%H:%M:%S%z'  # ISO 8601 format with timezone
    formatter.default_msec_format = '%s.%03dZ'  # Milliseconds with 'Z' to indicate UTC time

    log_handler.setFormatter(formatter)

    # Add the handler to the root logger so that all logs are formatted as JSON and sent to stdout
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    # Set the default log level to INFO
    root_logger.setLevel(logging.INFO) 

    # Suppress Flask's default request logging to avoid cluttering logs with non-JSON format
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  

    logging.info("✅ Logging is configured to output JSON format to stdout for Loki ingestion.")

    return root_logger