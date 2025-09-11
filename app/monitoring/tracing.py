import logging
import time
import uuid

from flask import g, request

logger = logging.getLogger(__name__)


def setup_tracing(app):
    """Setup request tracing for the Flask app"""

    @app.before_request
    def before_request():
        """Setup tracing context for each request"""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()
        g.user_id = "anonymous"  # Will be updated if user is authenticated

        # Enhanced request logging with structured data for Loki
        logger.info(
            "Request started",
            extra={
                "event": "request_started",
                "request_id": request_id,
                "method": request.method,
                "url": request.url,
                "path": request.path,
                "query_string": request.query_string.decode("utf-8"),
                "user_agent": request.headers.get("User-Agent", ""),
                "remote_addr": request.remote_addr,
                "content_type": request.content_type,
                "content_length": request.content_length,
                "endpoint": request.endpoint or "unknown",
            },
        )

    @app.after_request
    def after_request(response):
        """Log response details after each request"""
        duration = time.time() - getattr(g, "start_time", time.time())
        request_id = getattr(g, "request_id", "unknown")

        # Safely calculate response size
        def get_safe_response_size(response):
            try:
                # Check if response has content_length
                if (
                    hasattr(response, "content_length")
                    and response.content_length is not None
                ):
                    return response.content_length

                # For responses that support get_data()
                if hasattr(response, "get_data"):
                    # Check if response is in direct passthrough mode
                    if (
                        hasattr(response, "direct_passthrough")
                        and response.direct_passthrough
                    ):
                        return -1  # Indicate unknown size for passthrough responses

                    try:
                        return len(response.get_data())
                    except RuntimeError:
                        # Fallback for responses in passthrough mode
                        return -1

                # Fallback for other response types
                return 0

            except Exception:
                return 0

        response_size = get_safe_response_size(response)

        # Enhanced response logging for Loki
        logger.info(
            "Request completed",
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_size": response_size,
                "content_type": getattr(response, "content_type", "unknown"),
                "method": request.method,
                "endpoint": request.endpoint or "unknown",
                "success": response.status_code < 400,
            },
        )

        return response

    logger.info("Request tracing setup completed")
