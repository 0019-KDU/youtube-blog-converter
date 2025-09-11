import logging
import time
from collections import defaultdict, deque

from flask import request

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute=60, requests_per_hour=1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets = defaultdict(deque)
        self.hour_buckets = defaultdict(deque)

    def is_allowed(self, identifier=None):
        """Check if request is allowed"""
        if identifier is None:
            identifier = request.remote_addr

        current_time = time.time()

        # Clean old entries
        self._clean_old_entries(identifier, current_time)

        # Check minute limit
        minute_requests = len(self.minute_buckets[identifier])
        if minute_requests >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded (per minute) for {identifier}")
            return False

        # Check hour limit
        hour_requests = len(self.hour_buckets[identifier])
        if hour_requests >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded (per hour) for {identifier}")
            return False

        # Add current request
        self.minute_buckets[identifier].append(current_time)
        self.hour_buckets[identifier].append(current_time)

        return True

    def _clean_old_entries(self, identifier, current_time):
        """Remove entries older than the time window"""
        minute_ago = current_time - 60
        hour_ago = current_time - 3600

        # Clean minute bucket
        while (
            self.minute_buckets[identifier]
            and self.minute_buckets[identifier][0] < minute_ago
        ):
            self.minute_buckets[identifier].popleft()

        # Clean hour bucket
        while (
            self.hour_buckets[identifier]
            and self.hour_buckets[identifier][0] < hour_ago
        ):
            self.hour_buckets[identifier].popleft()

    def get_remaining_requests(self, identifier=None):
        """Get remaining requests for identifier"""
        if identifier is None:
            identifier = request.remote_addr

        current_time = time.time()
        self._clean_old_entries(identifier, current_time)

        minute_remaining = max(
            0, self.requests_per_minute - len(self.minute_buckets[identifier])
        )
        hour_remaining = max(
            0, self.requests_per_hour - len(self.hour_buckets[identifier])
        )

        return {"minute_remaining": minute_remaining, "hour_remaining": hour_remaining}
