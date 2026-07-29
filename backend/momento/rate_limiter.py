"""Scope-based rate limiting with multiple algorithms.

This module implements:
- Token bucket algorithm (for high-frequency scopes)
- Leaky bucket algorithm (for premium scopes)
- Fixed window algorithm (for basic scopes)
- Sliding window algorithm (for admin scopes)
- Per-scope rate limit configuration
- Distributed rate limiting (Redis-ready)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status

from . import db
from .multi_scope_schema import SCOPES


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    
    TOKEN_BUCKET = "token-bucket"
    LEAKY_BUCKET = "leaky-bucket"
    FIXED_WINDOW = "fixed-window"
    SLIDING_WINDOW = "sliding-window"
    NONE = "none"  # Unlimited


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a scope."""
    
    requests_per_minute: int
    burst: int
    algorithm: RateLimitAlgorithm
    window_seconds: int = 60


# Scope-specific rate limit configurations
SCOPE_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    "my_scope": RateLimitConfig(
        requests_per_minute=0,  # Unlimited
        burst=0,
        algorithm=RateLimitAlgorithm.NONE,
    ),
    "admin_scope": RateLimitConfig(
        requests_per_minute=10000,
        burst=15000,
        algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
    ),
    "fx_user_scope": RateLimitConfig(
        requests_per_minute=5000,
        burst=7500,
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
    ),
    "big_better_scope": RateLimitConfig(
        requests_per_minute=1000,
        burst=1500,
        algorithm=RateLimitAlgorithm.LEAKY_BUCKET,
    ),
    "regular_low_budget_scope": RateLimitConfig(
        requests_per_minute=100,
        burst=200,
        algorithm=RateLimitAlgorithm.FIXED_WINDOW,
    ),
    "public_consumer_scope": RateLimitConfig(
        requests_per_minute=50,
        burst=100,
        algorithm=RateLimitAlgorithm.FIXED_WINDOW,
    ),
}


class TokenBucket:
    """Token bucket rate limiter.
    
    Allows bursts up to burst capacity, then refills at rate_per_second.
    """
    
    def __init__(self, rate: int, burst: int):
        """Initialize token bucket.
        
        Args:
            rate: Tokens per second
            burst: Maximum bucket capacity
        """
        self.rate = rate
        self.burst = burst
        self._tokens: Dict[str, float] = defaultdict(lambda: float(burst))
        self._last_update: Dict[str, float] = defaultdict(time.time)
    
    def allow(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed.
        
        Args:
            key: Client identifier
            
        Returns:
            Tuple of (allowed, metadata)
        """
        now = time.time()
        last = self._last_update[key]
        elapsed = now - last
        
        # Refill tokens
        self._tokens[key] = min(self.burst, self._tokens[key] + elapsed * self.rate)
        self._last_update[key] = now
        
        if self._tokens[key] >= 1:
            self._tokens[key] -= 1
            return True, {
                "remaining": int(self._tokens[key]),
                "limit": self.burst,
                "reset": int(now + (self.burst - self._tokens[key]) / self.rate),
            }
        
        return False, {
            "remaining": 0,
            "limit": self.burst,
            "reset": int(now + (1 - self._tokens[key]) / self.rate),
        }


class LeakyBucket:
    """Leaky bucket rate limiter.
    
    Processes requests at a constant rate, queueing excess requests.
    """
    
    def __init__(self, rate: int, burst: int):
        """Initialize leaky bucket.
        
        Args:
            rate: Requests per second
            burst: Maximum queue size
        """
        self.rate = rate
        self.burst = burst
        self._queue_size: Dict[str, int] = defaultdict(int)
        self._last_leak: Dict[str, float] = defaultdict(time.time)
    
    def allow(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed.
        
        Args:
            key: Client identifier
            
        Returns:
            Tuple of (allowed, metadata)
        """
        now = time.time()
        last = self._last_leak[key]
        elapsed = now - last
        
        # Leak requests
        leaked = int(elapsed * self.rate)
        self._queue_size[key] = max(0, self._queue_size[key] - leaked)
        self._last_leak[key] = now
        
        if self._queue_size[key] < self.burst:
            self._queue_size[key] += 1
            return True, {
                "remaining": self.burst - self._queue_size[key],
                "limit": self.burst,
                "reset": int(now + self._queue_size[key] / self.rate),
            }
        
        return False, {
            "remaining": 0,
            "limit": self.burst,
            "reset": int(now + self._queue_size[key] / self.rate),
        }


class FixedWindow:
    """Fixed window rate limiter.
    
    Counts requests in fixed time windows.
    """
    
    def __init__(self, requests_per_minute: int, window_seconds: int = 60):
        """Initialize fixed window.
        
        Args:
            requests_per_minute: Requests allowed per window
            window_seconds: Window duration in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._counts: Dict[str, int] = defaultdict(int)
        self._window_start: Dict[str, float] = defaultdict(time.time)
    
    def allow(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed.
        
        Args:
            key: Client identifier
            
        Returns:
            Tuple of (allowed, metadata)
        """
        now = time.time()
        window_start = self._window_start[key]
        
        # Reset window if expired
        if now - window_start >= self.window_seconds:
            self._counts[key] = 0
            self._window_start[key] = now
            window_start = now
        
        if self._counts[key] < self.requests_per_minute:
            self._counts[key] += 1
            return True, {
                "remaining": self.requests_per_minute - self._counts[key],
                "limit": self.requests_per_minute,
                "reset": int(window_start + self.window_seconds),
            }
        
        return False, {
            "remaining": 0,
            "limit": self.requests_per_minute,
            "reset": int(window_start + self.window_seconds),
        }


class SlidingWindow:
    """Sliding window rate limiter.
    
    Counts requests in a sliding time window for smoother rate limiting.
    """
    
    def __init__(self, requests_per_minute: int, window_seconds: int = 60):
        """Initialize sliding window.
        
        Args:
            requests_per_minute: Requests allowed per window
            window_seconds: Window duration in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
    
    def allow(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed.
        
        Args:
            key: Client identifier
            
        Returns:
            Tuple of (allowed, metadata)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove old requests
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        
        if len(self._requests[key]) < self.requests_per_minute:
            self._requests[key].append(now)
            return True, {
                "remaining": self.requests_per_minute - len(self._requests[key]),
                "limit": self.requests_per_minute,
                "reset": int(self._requests[key][0] + self.window_seconds) if self._requests[key] else int(now),
            }
        
        return False, {
            "remaining": 0,
            "limit": self.requests_per_minute,
            "reset": int(self._requests[key][0] + self.window_seconds),
        }


class RateLimiter:
    """Scope-based rate limiter with multiple algorithms.
    
    This class manages rate limiting for different scopes using
    appropriate algorithms based on the scope's requirements.
    """
    
    def __init__(self):
        """Initialize rate limiter with all algorithms."""
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._leaky_buckets: Dict[str, LeakyBucket] = {}
        self._fixed_windows: Dict[str, FixedWindow] = {}
        self._sliding_windows: Dict[str, SlidingWindow] = {}
    
    def _get_algorithm(self, config: RateLimitConfig) -> object:
        """Get or create algorithm instance for config.
        
        Args:
            config: Rate limit configuration
            
        Returns:
            Algorithm instance
        """
        key = f"{config.requests_per_minute}:{config.burst}:{config.algorithm.value}"
        
        if config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            if key not in self._token_buckets:
                rate = config.requests_per_minute / 60  # per second
                self._token_buckets[key] = TokenBucket(rate, config.burst)
            return self._token_buckets[key]
        
        elif config.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            if key not in self._leaky_buckets:
                rate = config.requests_per_minute / 60  # per second
                self._leaky_buckets[key] = LeakyBucket(rate, config.burst)
            return self._leaky_buckets[key]
        
        elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            if key not in self._fixed_windows:
                self._fixed_windows[key] = FixedWindow(config.requests_per_minute, config.window_seconds)
            return self._fixed_windows[key]
        
        elif config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            if key not in self._sliding_windows:
                self._sliding_windows[key] = SlidingWindow(config.requests_per_minute, config.window_seconds)
            return self._sliding_windows[key]
        
        # NONE (unlimited)
        return None
    
    def check_rate_limit(
        self,
        scope: str,
        client_id: str,
        endpoint: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed based on scope rate limit.
        
        Args:
            scope: User scope
            client_id: Client identifier (tenant_id or IP)
            endpoint: Optional endpoint for endpoint-specific limits
            
        Returns:
            Tuple of (allowed, metadata)
        """
        config = SCOPE_RATE_LIMITS.get(scope)
        if not config:
            # Default to conservative limits
            config = RateLimitConfig(
                requests_per_minute=100,
                burst=200,
                algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            )
        
        # Unlimited for My Scope
        if config.algorithm == RateLimitAlgorithm.NONE:
            return True, {
                "remaining": -1,  # Unlimited
                "limit": -1,
                "reset": 0,
            }
        
        # Get algorithm
        algorithm = self._get_algorithm(config)
        if not algorithm:
            return True, {
                "remaining": -1,
                "limit": -1,
                "reset": 0,
            }
        
        # Check rate limit
        key = f"{client_id}:{endpoint}" if endpoint else client_id
        allowed, metadata = algorithm.allow(key)
        
        return allowed, metadata
    
    def get_rate_limit_info(self, scope: str) -> Dict[str, Any]:
        """Get rate limit information for a scope.
        
        Args:
            scope: User scope
            
        Returns:
            Rate limit information
        """
        config = SCOPE_RATE_LIMITS.get(scope)
        if not config:
            config = RateLimitConfig(
                requests_per_minute=100,
                burst=200,
                algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            )
        
        return {
            "scope": scope,
            "requests_per_minute": config.requests_per_minute,
            "burst": config.burst,
            "algorithm": config.algorithm.value,
            "window_seconds": config.window_seconds,
        }
    
    def reset_client(self, scope: str, client_id: str) -> None:
        """Reset rate limit for a specific client.
        
        Args:
            scope: User scope
            client_id: Client identifier
        """
        # In production with Redis, this would delete the client's keys
        # For in-memory, we can't easily reset without tracking all keys
        pass
    
    def get_usage_stats(self, scope: str, client_id: str) -> Dict[str, Any]:
        """Get usage statistics for a client.
        
        Args:
            scope: User scope
            client_id: Client identifier
            
        Returns:
            Usage statistics
        """
        # In production, this would query Redis for current usage
        # For in-memory, return estimated stats
        config = SCOPE_RATE_LIMITS.get(scope)
        if not config:
            return {"scope": scope, "client_id": client_id, "usage": "unknown"}
        
        return {
            "scope": scope,
            "client_id": client_id,
            "limit": config.requests_per_minute,
            "algorithm": config.algorithm.value,
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit_or_raise(
    scope: str,
    client_id: str,
    endpoint: Optional[str] = None,
) -> Dict[str, Any]:
    """Check rate limit and raise HTTPException if exceeded.
    
    Args:
        scope: User scope
        client_id: Client identifier
        endpoint: Optional endpoint for endpoint-specific limits
        
    Returns:
        Rate limit metadata
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    allowed, metadata = rate_limiter.check_rate_limit(scope, client_id, endpoint)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(metadata["limit"]),
                "X-RateLimit-Remaining": str(metadata["remaining"]),
                "X-RateLimit-Reset": str(metadata["reset"]),
            },
        )
    
    return metadata


def persist_rate_limit_to_db(
    tenant_id: str,
    scope: str,
    endpoint: str,
    window_start: str,
    request_count: int,
    blocked: bool = False,
) -> None:
    """Persist rate limit data to database for analytics.
    
    Args:
        tenant_id: Tenant ID
        scope: User scope
        endpoint: API endpoint
        window_start: Window start timestamp
        request_count: Number of requests in window
        blocked: Whether requests were blocked
    """
    try:
        db.execute(
            """INSERT INTO rate_limits (client_id, scope, endpoint, window_start, request_count, blocked, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(client_id, scope, endpoint, window_start)
               DO UPDATE SET request_count = request_count + excluded.request_count,
                              blocked = blocked OR excluded.blocked""",
            (tenant_id, scope, endpoint, window_start, request_count, 1 if blocked else 0, db.utc_now()),
        )
    except Exception:
        # Don't fail the request if persistence fails
        pass


def get_rate_limit_stats(tenant_id: str, hours: int = 24) -> Dict[str, Any]:
    """Get rate limit statistics for a tenant.
    
    Args:
        tenant_id: Tenant ID
        hours: Number of hours to look back
        
    Returns:
        Rate limit statistics
    """
    rows = db.query(
        """SELECT scope, endpoint, SUM(request_count) as total_requests, SUM(blocked) as total_blocked
           FROM rate_limits
           WHERE client_id = ? AND created_at >= datetime('now', '-{} hours')
           GROUP BY scope, endpoint
           ORDER BY total_requests DESC""".format(hours),
        (tenant_id,),
    )
    
    return {
        "tenant_id": tenant_id,
        "period_hours": hours,
        "by_scope": {row["scope"]: {"total_requests": row["total_requests"], "total_blocked": row["total_blocked"]} for row in rows},
    }
