import logging
import threading
import time
from functools import wraps

import psutil
from flask import Response, g, has_app_context, request
from prometheus_client import (CONTENT_TYPE_LATEST, CollectorRegistry, Counter,
                               Gauge, Histogram, generate_latest)

logger = logging.getLogger(__name__)

# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Application metrics
http_requests_total = Counter(
    "flask_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "flask_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=REGISTRY,
)

blog_generation_requests = Counter(
    "blog_generation_requests_total",
    "Total blog generation requests",
    ["status"],
    registry=REGISTRY,
)

blog_generation_duration = Histogram(
    "blog_generation_duration_seconds",
    "Blog generation duration in seconds",
    registry=REGISTRY,
)

active_users = Gauge("active_users", "Number of active users", registry=REGISTRY)

youtube_urls_processed = Counter(
    "youtube_urls_processed_total",
    "Total YouTube URLs processed",
    ["status"],
    registry=REGISTRY,
)

openai_tokens_used = Counter(
    "openai_tokens_used_total", "Total OpenAI tokens used", registry=REGISTRY
)

pdf_downloads = Counter("pdf_downloads_total", "Total PDF downloads", registry=REGISTRY)

database_operations = Counter(
    "database_operations_total",
    "Total database operations",
    ["operation", "collection", "status"],
    registry=REGISTRY,
)

# System metrics
cpu_usage = Gauge("system_cpu_usage_percent", "CPU usage percentage", registry=REGISTRY)

memory_usage = Gauge(
    "system_memory_usage_bytes", "Memory usage in bytes", registry=REGISTRY
)

memory_usage_percent = Gauge(
    "system_memory_usage_percent", "Memory usage percentage", registry=REGISTRY
)

disk_usage = Gauge(
    "system_disk_usage_percent", "Disk usage percentage", registry=REGISTRY
)

# User activity metrics
user_sessions = Gauge(
    "user_sessions_active", "Number of active user sessions", registry=REGISTRY
)

blog_posts_created = Counter(
    "blog_posts_created_total", "Total blog posts created", registry=REGISTRY
)

user_registrations = Counter(
    "user_registrations_total",
    "Total user registrations",
    ["status"],
    registry=REGISTRY,
)

user_logins = Counter(
    "user_logins_total", "Total user login attempts", ["status"], registry=REGISTRY
)

# Error metrics
application_errors = Counter(
    "application_errors_total",
    "Total application errors",
    ["error_type"],
    registry=REGISTRY,
)

api_errors = Counter(
    "api_errors_total", "Total API errors", ["api", "error_type"], registry=REGISTRY
)

# Log metrics for Loki integration
log_entries_total = Counter(
    "log_entries_total",
    "Total log entries by level",
    ["level", "logger"],
    registry=REGISTRY,
)


def collect_system_metrics(app):
    """Collect system metrics periodically"""
    while True:
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage.set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.used)
            memory_usage_percent.set(memory.percent)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_usage.set((disk.used / disk.total) * 100)

            # Active sessions (estimate from temp storage)
            with app.app_context():
                user_sessions.set(len(app.temp_storage))

            time.sleep(30)  # Collect every 30 seconds
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            time.sleep(30)


class ContextAwareLogMetricsFilter(logging.Filter):
    """Filter to track log metrics for Prometheus with context awareness"""

    def filter(self, record):
        # Track log entries by level
        log_entries_total.labels(level=record.levelname, logger=record.name).inc()

        # Add context information to log records safely
        if has_app_context():
            try:
                if not hasattr(record, "request_id"):
                    record.request_id = getattr(g, "request_id", "no-request")

                if not hasattr(record, "user_id"):
                    record.user_id = getattr(g, "user_id", "anonymous")

                if not hasattr(record, "endpoint"):
                    record.endpoint = request.endpoint if request else "unknown"
            except:
                record.request_id = "no-request"
                record.user_id = "anonymous"
                record.endpoint = "unknown"
        else:
            record.request_id = "no-request"
            record.user_id = "anonymous"
            record.endpoint = "unknown"

        return True


def track_requests(f):
    """Decorator to track HTTP requests with enhanced Loki logging"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        try:
            response = f(*args, **kwargs)

            # Extract status code
            if isinstance(response, tuple):
                status_code = str(response[1]) if len(response) > 1 else "200"
            elif hasattr(response, "status_code"):
                status_code = str(response.status_code)
            else:
                status_code = "200"

            # Track metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown",
                status_code=status_code,
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method, endpoint=request.endpoint or "unknown"
            ).observe(duration)

            return response

        except Exception as e:
            # Track error
            http_requests_total.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown",
                status_code="500",
            ).inc()

            application_errors.labels(error_type=type(e).__name__).inc()
            raise

    return decorated_function


def setup_metrics(app):
    """Setup Prometheus metrics for the Flask app"""

    # Add metrics endpoint
    @app.route("/metrics")
    def metrics():
        """Prometheus metrics endpoint"""
        try:
            return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)
        except Exception as e:
            logger.error(f"Error generating metrics: {e}", exc_info=True)
            return "Error generating metrics", 500

    # Start system metrics collection thread
    metrics_thread = threading.Thread(
        target=collect_system_metrics, args=(app,), daemon=True
    )
    metrics_thread.start()

    # Add the metrics filter to all handlers
    metrics_filter = ContextAwareLogMetricsFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(metrics_filter)

    logger.info("Prometheus metrics setup completed")
