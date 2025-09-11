import datetime
import logging
import os
import time

import psutil
from flask import Blueprint, Response, current_app, jsonify

from app.models.user import mongo_manager

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check():
    """Health check endpoint with detailed system information"""
    try:
        # Check database connection
        db_connected = mongo_manager.is_connected()

        # Get system information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        health_data = {
            "status": "healthy" if db_connected else "unhealthy",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "database": "connected" if db_connected else "disconnected",
            "secret_key_set": bool(current_app.secret_key),
            "temp_storage_items": len(current_app.temp_storage),
            "loki_url": os.getenv("LOKI_URL", "not_configured"),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
            },
            "application": {
                "version": "1.0.0",
                "environment": os.getenv("FLASK_ENV", "production"),
                "uptime_seconds": (
                    int(time.time() - current_app.start_time)
                    if hasattr(current_app, "start_time")
                    else 0
                ),
            },
        }

        status_code = 200 if db_connected else 503

        # Enhanced health check logging
        logger.info(
            "Health check performed",
            extra={
                "event": "health_check",
                "status": health_data["status"],
                "database": health_data["database"],
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "loki_configured": bool(os.getenv("LOKI_URL")),
            },
        )

        return jsonify(health_data), status_code

    except Exception as e:
        logger.error(
            "Health check error",
            extra={
                "event": "health_check_error",
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "error": str(e),
                    "secret_key_set": bool(current_app.secret_key),
                }
            ),
            503,
        )


@health_bp.route("/health-metrics")
def health_metrics():
    """Prometheus-compatible health metrics endpoint"""
    try:
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Check database connection
        db_connected = mongo_manager.is_connected()

        # Generate Prometheus metrics format
        metrics = []

        # Health status (1 = healthy, 0 = unhealthy)
        health_status = 1 if db_connected else 0
        metrics.append(f"app_health_status {health_status}")

        # Database status (1 = connected, 0 = disconnected)
        db_status = 1 if db_connected else 0
        metrics.append(f"app_database_status {db_status}")

        # System metrics
        metrics.append(f"app_cpu_percent {cpu_percent}")
        metrics.append(f"app_memory_percent {memory.percent}")
        metrics.append(f"app_memory_used_bytes {memory.used}")
        metrics.append(f"app_memory_total_bytes {memory.total}")
        metrics.append(
            f"app_disk_percent {round((disk.used / disk.total) * 100, 2)}")
        metrics.append(f"app_disk_used_bytes {disk.used}")
        metrics.append(f"app_disk_total_bytes {disk.total}")

        # Application metrics
        metrics.append(
            f"app_temp_storage_items {len(current_app.temp_storage)}")
        metrics.append(
            f'app_uptime_seconds {
                int(
                    time.time() -
                    current_app.start_time) if hasattr(
                    current_app,
                    "start_time") else 0}')

        # Join all metrics
        response_text = "\n".join(metrics) + "\n"

        return Response(response_text, mimetype="text/plain")

    except Exception as e:
        logger.error(f"Health metrics error: {e}", exc_info=True)
        # Return error metric
        error_response = f'app_health_status 0\napp_error {{error="{
            str(e)}"}} 1\n'
        return Response(error_response, mimetype="text/plain"), 503
