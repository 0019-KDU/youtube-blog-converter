import time
from unittest.mock import Mock, patch

import pytest


class TestRateLimiter:
    """Test cases for RateLimiter"""
    
    def test_init_default_values(self):
        """Test RateLimiter initialization with default values"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        assert limiter.requests_per_minute == 60
        assert limiter.requests_per_hour == 1000
    
    def test_init_custom_values(self):
        """Test RateLimiter initialization with custom values"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=30, requests_per_hour=500)
        
        assert limiter.requests_per_minute == 30
        assert limiter.requests_per_hour == 500
    
    def test_is_allowed_first_request(self, request_context):
        """Test that first request is allowed"""
        from flask import request

        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        
        with patch.object(request, 'remote_addr', '127.0.0.1'):
            result = limiter.is_allowed()
        
        assert result is True
    
    def test_is_allowed_within_limits(self):
        """Test requests within limits are allowed"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=10)
        identifier = '127.0.0.1'
        
        # Make 3 requests - should all be allowed
        for _ in range(3):
            result = limiter.is_allowed(identifier)
            assert result is True
    
    def test_is_allowed_exceeds_minute_limit(self):
        """Test requests exceeding minute limit are denied"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=10)
        identifier = '127.0.0.1'
        
        # Make requests up to limit
        for _ in range(2):
            result = limiter.is_allowed(identifier)
            assert result is True
        
        # Next request should be denied
        result = limiter.is_allowed(identifier)
        assert result is False
    
    def test_is_allowed_exceeds_hour_limit(self):
        """Test requests exceeding hour limit are denied"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=100, requests_per_hour=2)
        identifier = '127.0.0.1'
        
        # Make requests up to hour limit
        for _ in range(2):
            result = limiter.is_allowed(identifier)
            assert result is True
        
        # Next request should be denied
        result = limiter.is_allowed(identifier)
        assert result is False
    
    def test_clean_old_entries(self):
        """Test cleaning of old entries"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter()
        identifier = '127.0.0.1'
        current_time = time.time()
        
        # Add old entries manually
        limiter.minute_buckets[identifier].append(current_time - 120)  # 2 minutes ago
        limiter.hour_buckets[identifier].append(current_time - 7200)   # 2 hours ago
        
        with patch('time.time', return_value=current_time):
            limiter._clean_old_entries(identifier, current_time)
        
        assert len(limiter.minute_buckets[identifier]) == 0
        assert len(limiter.hour_buckets[identifier]) == 0
        
    def test_rate_limit_exceeded(self, request_context):
        """Test rate limit exceeded scenario"""
        from flask import request

        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=2) 
    def test_get_remaining_requests(self, request_context):
        """Test getting remaining request counts"""
        from flask import request

        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=10)
        
        with patch.object(request, 'remote_addr', '127.0.0.1'):
            # Make one request
            limiter.is_allowed()
            
            remaining = limiter.get_remaining_requests()
            
            assert remaining['minute_remaining'] == 9
            assert remaining['hour_remaining'] == 999
    
    def test_different_identifiers_separate_limits(self):
        """Test different identifiers have separate limits"""
        from app.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=5)
        
        # Exhaust limit for first identifier
        for _ in range(2):
            result = limiter.is_allowed('127.0.0.1')
            assert result is True
        
        # First identifier should be denied
        result = limiter.is_allowed('127.0.0.1')
        assert result is False
        
        # Second identifier should still be allowed
        result = limiter.is_allowed('192.168.1.1')
        assert result is True
