import datetime
import json
import logging
import os
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from queue import Empty, Queue

import requests

logger = logging.getLogger(__name__)


class LokiHandler(logging.Handler):
    """Custom Loki handler for Flask application logs"""

    def __init__(
        self, loki_url, tags=None, timeout=5, batch_size=100, flush_interval=5
    ):
        super().__init__()
        self.loki_url = loki_url.rstrip("/") + "/loki/api/v1/push"
        self.tags = tags or {}
        self.timeout = timeout
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Batch processing
        self.log_queue = Queue()
        self.batch_thread = threading.Thread(
            target=self._batch_sender, daemon=True)
        self.batch_thread.start()

    def emit(self, record):
        """Emit a log record to Loki"""
        try:
            # Format the record
            log_entry = self.format(record)

            # Create timestamp in nanoseconds
            timestamp = str(int(time.time() * 1_000_000_000))

            # Prepare labels
            labels = dict(self.tags)
            labels.update(
                {
                    "level": record.levelname.lower(),
                    "logger": record.name,
                    "filename": record.filename,
                    "function": record.funcName,
                    "application": "flask-blog-app",
                }
            )

            # Add extra labels from record
            if hasattr(record, "request_id"):
                labels["request_id"] = record.request_id
            if hasattr(record, "user_id"):
                labels["user_id"] = record.user_id
            if hasattr(record, "endpoint"):
                labels["endpoint"] = record.endpoint
            if hasattr(record, "error_type"):
                labels["error_type"] = record.error_type

            # Create Loki entry
            loki_entry = {"streams": [
                {"stream": labels, "values": [[timestamp, log_entry]]}]}

            # Add to queue for batch processing
            self.log_queue.put(loki_entry)

        except Exception as e:
            # Don't let logging errors break the application
            print(f"Loki handler error: {e}")

    def _batch_sender(self):
        """Background thread to send logs in batches"""
        batch = []
        last_flush = time.time()

        while True:
            try:
                # Try to get log entry with timeout
                try:
                    entry = self.log_queue.get(timeout=1)
                    batch.append(entry)
                except Empty:
                    pass

                # Check if we should flush the batch
                should_flush = len(batch) >= self.batch_size or (
                    batch and time.time() - last_flush >= self.flush_interval
                )

                if should_flush and batch:
                    self._send_batch(batch)
                    batch = []
                    last_flush = time.time()

            except Exception as e:
                print(f"Batch sender error: {e}")
                batch = []  # Clear batch on error

    def _send_batch(self, batch):
        """Send a batch of log entries to Loki"""
        if not batch:
            return

        try:
            # Merge all streams
            merged_streams = {}
            for entry in batch:
                for stream in entry["streams"]:
                    stream_key = json.dumps(stream["stream"], sort_keys=True)
                    if stream_key not in merged_streams:
                        merged_streams[stream_key] = {
                            "stream": stream["stream"],
                            "values": [],
                        }
                    merged_streams[stream_key]["values"].extend(
                        stream["values"])

            # Create final payload
            payload = {"streams": list(merged_streams.values())}

            # Send to Loki
            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.loki_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code != 204:
                print(
                    f"Loki push failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Failed to send logs to Loki: {e}")


class LokiJsonFormatter(logging.Formatter):
    """JSON formatter for Loki with structured data"""

    def format(self, record):
        # Create base log entry
        log_entry = {
            "timestamp": datetime.datetime.fromtimestamp(
                record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "function": record.funcName,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = str(value)

        return json.dumps(log_entry)


def setup_basic_logging():
    """Setup basic logging before Flask app initialization"""

    # Create logs directory
    log_dir = Path("/var/log/flask-app")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fall back to local directory if /var/log is not writable
        log_dir = Path("./logs")
        log_dir.mkdir(parents=True, exist_ok=True)

    # Set log level from environment
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())

    # Simple formatter for initial setup
    basic_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d"
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(basic_formatter)
    root_logger.addHandler(console_handler)

    # File handler for application logs (if directory exists)
    if log_dir.exists():
        app_log_file = log_dir / "app.log"
        app_handler = RotatingFileHandler(
            app_log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        app_handler.setLevel(log_level)
        app_handler.setFormatter(basic_formatter)
        root_logger.addHandler(app_handler)

    # Set specific loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    print("Basic logging configuration completed")
    return root_logger


def setup_logging(app):
    """Setup enhanced logging with Loki integration"""

    # Get Loki URL from environment
    loki_url = os.getenv("LOKI_URL", "http://YOUR_DROPLET_IP:3100")

    # Determine log directory based on environment
    shared_log_path = os.getenv("SHARED_LOG_PATH", "/shared-logs")
    log_dir = (Path(shared_log_path) if os.path.exists(
        shared_log_path) else Path("./logs"))

    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set log level from environment
    log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Loki handler for centralized logging
    if loki_url and loki_url != "http://YOUR_DROPLET_IP:3100":
        try:
            loki_handler = LokiHandler(
                loki_url=loki_url,
                tags={
                    "application": "flask-blog-app",
                    "environment": os.getenv("FLASK_ENV", "production"),
                    "service": "web-app",
                },
            )
            loki_handler.setLevel(log_level)
            loki_handler.setFormatter(LokiJsonFormatter())
            root_logger.addHandler(loki_handler)
            logger.info(f"Loki handler configured successfully: {loki_url}")
        except Exception as e:
            logger.error(f"Failed to configure Loki handler: {e}")
    else:
        logger.warning("Loki URL not configured, skipping Loki integration")

    # Enhanced JSON logs for local file storage (backup)
    json_log_file = log_dir / "app.json"
    json_handler = RotatingFileHandler(
        json_log_file, maxBytes=50 * 1024 * 1024, backupCount=5  # 50MB
    )
    json_handler.setLevel(log_level)
    json_handler.setFormatter(LokiJsonFormatter())
    root_logger.addHandler(json_handler)

    # Enhanced access logs
    access_log_file = log_dir / "access.log"
    access_handler = RotatingFileHandler(
        access_log_file, maxBytes=50 * 1024 * 1024, backupCount=5
    )
    access_handler.setLevel(logging.INFO)
    access_formatter = logging.Formatter(
        '%(asctime)s - %(remote_addr)s - "%(method)s %(url)s %(protocol)s" %(status_code)s %(response_size)s "%(user_agent)s" %(duration_ms)sms'
    )
    access_handler.setFormatter(access_formatter)

    # Create access logger
    access_logger = logging.getLogger("access")
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False

    logger.info(f"Enhanced logging configured - Log directory: {log_dir}")
