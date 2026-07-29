"""Security Monitoring and Intrusion Detection System.

Implements real-time security monitoring, anomaly detection, and intrusion prevention
following NIST SP 800-94 (Guide to Intrusion Detection and Prevention Systems).
"""

from __future__ import annotations

import time
import json
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import logging
import re

logger = logging.getLogger(__name__)


class SecurityEventSeverity(str, Enum):
    """Security event severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(str, Enum):
    """Types of security events."""

    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_LOCKOUT = "auth_lockout"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_FAILURE = "mfa_failure"

    # Authorization events
    PERMISSION_DENIED = "permission_denied"
    SCOPE_DENIED = "scope_denied"
    PRIVILEGE_ESCALATION = "privilege_escalation"

    # Network events
    SUSPICIOUS_IP = "suspicious_ip"
    BLOCKED_IP = "blocked_ip"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PORT_SCAN = "port_scan"
    DDoS_ATTEMPT = "ddos_attempt"

    # Data events
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"

    # System events
    CONFIG_CHANGE = "config_change"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_MODIFIED = "user_modified"

    # Anomaly events
    ANOMALY_DETECTED = "anomaly_detected"
    BEHAVIOR_ANOMALY = "behavior_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"


@dataclass
class SecurityEvent:
    """A security event with full context."""

    event_type: SecurityEventType
    severity: SecurityEventSeverity
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[int] = None
    email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging/storage."""
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "email": self.email,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "details": self.details,
            "metadata": self.metadata,
        }


@dataclass
class AnomalyDetectionRule:
    """Rule for detecting security anomalies."""

    name: str
    description: str
    severity: SecurityEventSeverity
    check_function: Callable[[Dict[str, Any]], bool]
    enabled: bool = True


class SecurityMonitor:
    """Real-time security monitoring and intrusion detection.

    Implements:
    - Event collection and correlation
    - Anomaly detection based on behavioral patterns
    - Rate-based detection (brute force, DDoS)
    - Geographic anomaly detection
    - Alert generation and escalation
    """

    def __init__(
        self,
        event_retention_hours: int = 168,  # 7 days
        anomaly_window_minutes: int = 60,
        alert_threshold: int = 5,
    ):
        """Initialize security monitor.

        Args:
            event_retention_hours: How long to retain events in memory
            anomaly_window_minutes: Time window for anomaly detection
            alert_threshold: Number of anomalies before alerting
        """
        self.event_retention_hours = event_retention_hours
        self.anomaly_window_minutes = anomaly_window_minutes
        self.alert_threshold = alert_threshold

        # Event storage (in-memory - use database in production)
        self._events: deque[SecurityEvent] = deque(maxlen=10000)

        # Tracking for anomaly detection
        self._auth_failures: Dict[str, List[datetime]] = defaultdict(list)
        self._rate_tracking: Dict[str, List[float]] = defaultdict(list)
        self._user_behavior: Dict[int, Dict[str, Any]] = defaultdict(dict)

        # Anomaly detection rules
        self._anomaly_rules: List[AnomalyDetectionRule] = []
        self._initialize_default_rules()

        # Alert callbacks
        self._alert_callbacks: List[Callable[[SecurityEvent], None]] = []

    def _initialize_default_rules(self) -> None:
        """Initialize default anomaly detection rules."""

        # Rule: Multiple auth failures from same IP
        def check_auth_failures(context: Dict[str, Any]) -> bool:
            ip = context.get("ip_address")
            if not ip:
                return False
            failures = self._auth_failures.get(ip, [])
            recent_failures = [
                f for f in failures if datetime.now(timezone.utc) - f < timedelta(minutes=15)
            ]
            return len(recent_failures) >= 5

        self._anomaly_rules.append(
            AnomalyDetectionRule(
                name="Multiple Auth Failures",
                description="5+ authentication failures from same IP in 15 minutes",
                severity=SecurityEventSeverity.HIGH,
                check_function=check_auth_failures,
            )
        )

        # Rule: High rate of requests from single IP
        def check_high_rate(context: Dict[str, Any]) -> bool:
            ip = context.get("ip_address")
            if not ip:
                return False
            requests = self._rate_tracking.get(ip, [])
            recent_requests = [
                r for r in requests if time.time() - r < 60
            ]  # Last 60 seconds
            return len(recent_requests) >= 100

        self._anomaly_rules.append(
            AnomalyDetectionRule(
                name="High Request Rate",
                description="100+ requests from same IP in 60 seconds",
                severity=SecurityEventSeverity.HIGH,
                check_function=check_high_rate,
            )
        )

        # Rule: Access from multiple geographic locations
        def check_geo_anomaly(context: Dict[str, Any]) -> bool:
            user_id = context.get("user_id")
            if not user_id:
                return False
            behavior = self._user_behavior.get(user_id, {})
            locations = behavior.get("locations", set())
            return len(locations) >= 3

        self._anomaly_rules.append(
            AnomalyDetectionRule(
                name="Geographic Anomaly",
                description="Access from 3+ different geographic locations",
                severity=SecurityEventSeverity.MEDIUM,
                check_function=check_geo_anomaly,
            )
        )

    def add_alert_callback(self, callback: Callable[[SecurityEvent], None]) -> None:
        """Add a callback function for security alerts.

        Args:
            callback: Function to call when security event occurs
        """
        self._alert_callbacks.append(callback)

    def record_event(self, event: SecurityEvent) -> None:
        """Record a security event.

        Args:
            event: SecurityEvent to record
        """
        # Add to event storage
        self._events.append(event)

        # Update tracking data
        self._update_tracking(event)

        # Check for anomalies
        self._check_anomalies(event)

        # Trigger alerts for high-severity events
        if event.severity in (SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL):
            self._trigger_alerts(event)

        # Log event
        self._log_event(event)

    def _update_tracking(self, event: SecurityEvent) -> None:
        """Update tracking data based on event.

        Args:
            event: SecurityEvent
        """
        # Track auth failures
        if event.event_type == SecurityEventType.AUTH_FAILURE and event.ip_address:
            self._auth_failures[event.ip_address].append(event.timestamp)

        # Track request rates
        if event.ip_address:
            self._rate_tracking[event.ip_address].append(time.time())

        # Track user behavior
        if event.user_id:
            behavior = self._user_behavior[event.user_id]
            if "first_seen" not in behavior:
                behavior["first_seen"] = event.timestamp
            behavior["last_seen"] = event.timestamp
            behavior["event_count"] = behavior.get("event_count", 0) + 1

            # Track locations (simplified - in production use GeoIP)
            if event.ip_address:
                locations = behavior.get("locations", set())
                locations.add(event.ip_address[:8])  # Group by /24 subnet
                behavior["locations"] = locations

    def _check_anomalies(self, event: SecurityEvent) -> None:
        """Check event against anomaly detection rules.

        Args:
            event: SecurityEvent to check
        """
        context = {
            "user_id": event.user_id,
            "email": event.email,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "resource": event.resource,
            "action": event.action,
        }

        for rule in self._anomaly_rules:
            if not rule.enabled:
                continue

            try:
                if rule.check_function(context):
                    # Create anomaly event
                    anomaly_event = SecurityEvent(
                        event_type=SecurityEventType.ANOMALY_DETECTED,
                        severity=rule.severity,
                        user_id=event.user_id,
                        email=event.email,
                        ip_address=event.ip_address,
                        details={
                            "rule_name": rule.name,
                            "rule_description": rule.description,
                            "triggering_event": event.event_type.value,
                        },
                    )
                    self.record_event(anomaly_event)
            except Exception as e:
                logger.error(f"Error checking anomaly rule {rule.name}: {e}")

    def _trigger_alerts(self, event: SecurityEvent) -> None:
        """Trigger alert callbacks for security event.

        Args:
            event: SecurityEvent
        """
        for callback in self._alert_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _log_event(self, event: SecurityEvent) -> None:
        """Log security event to appropriate log level.

        Args:
            event: SecurityEvent
        """
        log_message = (
            f"[{event.event_type.value}] "
            f"User: {event.email or event.user_id} "
            f"IP: {event.ip_address} "
            f"Resource: {event.resource}"
        )

        if event.severity == SecurityEventSeverity.CRITICAL:
            logger.critical(log_message, extra=event.to_dict())
        elif event.severity == SecurityEventSeverity.HIGH:
            logger.error(log_message, extra=event.to_dict())
        elif event.severity == SecurityEventSeverity.MEDIUM:
            logger.warning(log_message, extra=event.to_dict())
        elif event.severity == SecurityEventSeverity.LOW:
            logger.info(log_message, extra=event.to_dict())
        else:
            logger.debug(log_message, extra=event.to_dict())

    def get_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[SecurityEventSeverity] = None,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[SecurityEvent]:
        """Query security events with filters.

        Args:
            event_type: Filter by event type
            severity: Filter by severity
            user_id: Filter by user ID
            ip_address: Filter by IP address
            since: Filter events since timestamp
            limit: Max number of events to return

        Returns:
            List of matching SecurityEvents
        """
        filtered = list(self._events)

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        if ip_address:
            filtered = [e for e in filtered if e.ip_address == ip_address]
        if since:
            filtered = [e for e in filtered if e.timestamp >= since]

        # Sort by timestamp descending
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        return filtered[:limit]

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the specified time period.

        Args:
            hours: Number of hours to summarize

        Returns:
            Dictionary with security metrics
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_events = [e for e in self._events if e.timestamp >= since]

        # Count by type
        by_type: Dict[str, int] = defaultdict(int)
        for event in recent_events:
            by_type[event.event_type.value] += 1

        # Count by severity
        by_severity: Dict[str, int] = defaultdict(int)
        for event in recent_events:
            by_severity[event.severity.value] += 1

        # Top IPs by event count
        ip_counts: Dict[str, int] = defaultdict(int)
        for event in recent_events:
            if event.ip_address:
                ip_counts[event.ip_address] += 1
        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Top users by event count
        user_counts: Dict[str, int] = defaultdict(int)
        for event in recent_events:
            if event.email:
                user_counts[event.email] += 1
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "period_hours": hours,
            "total_events": len(recent_events),
            "by_type": dict(by_type),
            "by_severity": dict(by_severity),
            "top_ips": top_ips,
            "top_users": top_users,
            "unique_ips": len(ip_counts),
            "unique_users": len(user_counts),
        }

    def cleanup_old_events(self) -> None:
        """Remove events older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.event_retention_hours)
        self._events = deque(
            [e for e in self._events if e.timestamp >= cutoff],
            maxlen=self._events.maxlen,
        )

        # Clean up tracking data
        now = datetime.now(timezone.utc)
        for ip in list(self._auth_failures.keys()):
            self._auth_failures[ip] = [
                f for f in self._auth_failures[ip] if now - f < timedelta(hours=1)
            ]
            if not self._auth_failures[ip]:
                del self._auth_failures[ip]

        for ip in list(self._rate_tracking.keys()):
            self._rate_tracking[ip] = [
                r for r in self._rate_tracking[ip] if time.time() - r < 300
            ]  # 5 minutes
            if not self._rate_tracking[ip]:
                del self._rate_tracking[ip]


class IntrusionDetectionEngine:
    """Advanced intrusion detection with pattern matching.

    Implements signature-based and anomaly-based detection.
    """

    def __init__(self):
        """Initialize intrusion detection engine."""
        self._patterns: List[Dict[str, Any]] = []
        self._initialize_patterns()

    def _initialize_patterns(self) -> None:
        """Initialize intrusion detection patterns."""

        # SQL injection patterns
        sql_patterns = [
            r"union\s+select",
            r"or\s+1\s*=\s*1",
            r"drop\s+table",
            r"exec\s*\(",
            r"waitfor\s+delay",
            r"';\s*--",
        ]
        for pattern in sql_patterns:
            self._patterns.append(
                {
                    "name": "SQL Injection",
                    "pattern": re.compile(pattern, re.IGNORECASE),
                    "severity": SecurityEventSeverity.CRITICAL,
                    "category": "injection",
                }
            )

        # XSS patterns
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"onerror\s*=",
            r"onload\s*=",
            r"eval\s*\(",
        ]
        for pattern in xss_patterns:
            self._patterns.append(
                {
                    "name": "XSS Attempt",
                    "pattern": re.compile(pattern, re.IGNORECASE),
                    "severity": SecurityEventSeverity.HIGH,
                    "category": "xss",
                }
            )

        # Path traversal patterns
        path_patterns = [
            r"\.\.\/",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e%5c",
        ]
        for pattern in path_patterns:
            self._patterns.append(
                {
                    "name": "Path Traversal",
                    "pattern": re.compile(pattern, re.IGNORECASE),
                    "severity": SecurityEventSeverity.HIGH,
                    "category": "path_traversal",
                }
            )

    def analyze_input(self, input_data: str, context: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Analyze input for intrusion patterns.

        Args:
            input_data: Input string to analyze
            context: Context information (ip, user, etc.)

        Returns:
            SecurityEvent if pattern detected, None otherwise
        """
        for pattern_def in self._patterns:
            if pattern_def["pattern"].search(input_data):
                return SecurityEvent(
                    event_type=SecurityEventType.ANOMALY_DETECTED,
                    severity=pattern_def["severity"],
                    ip_address=context.get("ip_address"),
                    user_id=context.get("user_id"),
                    email=context.get("email"),
                    resource=context.get("resource"),
                    details={
                        "pattern_name": pattern_def["name"],
                        "category": pattern_def["category"],
                        "matched_input": input_data[:200],  # Truncate for safety
                    },
                )

        return None

    def analyze_request(self, request: Dict[str, Any]) -> List[SecurityEvent]:
        """Analyze a complete request for intrusions.

        Args:
            request: Request dictionary with headers, params, body

        Returns:
            List of detected SecurityEvents
        """
        events = []

        # Analyze query parameters
        for key, value in request.get("params", {}).items():
            if isinstance(value, str):
                event = self.analyze_input(
                    value,
                    {
                        "ip_address": request.get("ip_address"),
                        "user_id": request.get("user_id"),
                        "email": request.get("email"),
                        "resource": f"param:{key}",
                    },
                )
                if event:
                    events.append(event)

        # Analyze body
        body = request.get("body", {})
        if isinstance(body, dict):
            for key, value in body.items():
                if isinstance(value, str):
                    event = self.analyze_input(
                        value,
                        {
                            "ip_address": request.get("ip_address"),
                            "user_id": request.get("user_id"),
                            "email": request.get("email"),
                            "resource": f"body:{key}",
                        },
                    )
                    if event:
                        events.append(event)

        return events


# Global security monitor instance
security_monitor = SecurityMonitor()

# Global intrusion detection engine
intrusion_detection = IntrusionDetectionEngine()
