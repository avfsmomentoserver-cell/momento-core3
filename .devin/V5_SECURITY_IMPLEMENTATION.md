# V5 Security Implementation Guide

## Overview

This document describes the military-grade security implementation for the Momento Core V5 transformation, following NIST SP 800-53, ISO 27001, SOC 2, and other compliance standards.

## Security Architecture

### Defense in Depth

The V5 security implementation follows a defense-in-depth approach with multiple layers of protection:

1. **Network Security** - TLS 1.3, IP filtering, DDoS protection
2. **Authentication** - JWT with RS256, MFA, session management
3. **Authorization** - RBAC + ABAC, least privilege
4. **Application Security** - Input validation, output encoding, security headers
5. **Data Security** - AES-256-GCM encryption at rest, TLS in transit
6. **Monitoring** - Real-time security monitoring, intrusion detection
7. **Audit** - Comprehensive audit logging for compliance

### Zero-Trust Architecture

The platform implements zero-trust principles:

- **Never trust, always verify** - Every request is authenticated and authorized
- **Least privilege** - Users have minimum required permissions
- **Micro-segmentation** - Scope-based access control
- **Continuous authentication** - Session validation and risk assessment
- **Risk-based authorization** - Dynamic access decisions based on context

## Security Components

### 1. Authentication System

#### JWT Authentication (jwt_auth.py)

Implements JWT with RS256 asymmetric signatures:

```python
from momento.security import jwt_auth, TokenPayload, TokenType

# Create access token
token = jwt_auth.create_access_token(
    user_id=123,
    email="user@example.com",
    role="analyst",
    tier="premium",
    scope="data:private"
)

# Decode and verify token
payload = jwt_auth.decode_token(token)
```

**Features:**
- RS256 asymmetric signatures (private key for signing, public for verification)
- Access tokens (1 hour TTL)
- Refresh tokens (7 days TTL)
- API keys (30 days TTL)
- Token revocation support
- JTI (JWT ID) for tracking

**Compliance:**
- NIST SP 800-63B (Digital Identity)
- OAuth 2.0 / OpenID Connect

#### Multi-Factor Authentication (mfa.py)

Implements TOTP-based MFA following RFC 6238:

```python
from momento.security import mfa, MFAConfig, MFAStatus

# Initiate enrollment
enrollment = mfa.initiate_enrollment(user_id=123, email="user@example.com")
# Returns: secret, QR code URL, backup codes

# Verify code and enable MFA
config = MFAConfig(user_id=123, secret=enrollment.secret)
result = mfa.enable_mfa(config, verification_code="123456")

# Verify MFA during login
result = mfa.verify_code(config, code="123456")
```

**Features:**
- TOTP (Time-based One-Time Password) with 6-digit codes
- 30-second time intervals
- QR code generation for easy setup
- 10 backup recovery codes
- Account lockout after failed attempts
- Backup code tracking

**Compliance:**
- NIST SP 800-63B Section 5.1.3.2
- RFC 6238 (TOTP)

### 2. Authorization System

#### Role-Based Access Control (rbac.py)

Implements hierarchical RBAC with fine-grained permissions:

```python
from momento.security import rbac, Permission, Role, Scope

# Check if role has permission
role = rbac.get_role("analyst")
has_permission = role.has_permission(Permission.ANALYSIS_RUN)

# Check if role has scope access
has_scope = role.has_scope_access(Scope.ANALYSIS_ADVANCED)

# Check user permission
user_role = "analyst"
has_perm = rbac.user_has_permission(user_role, Permission.DATA_EXPORT)
```

**Default Roles:**
- **guest** - Read-only public data
- **user** - Basic data and analysis access
- **analyst** - Advanced analysis and forecasts
- **operator** - System management
- **admin** - Full system access

**Permissions:**
- User management (create, read, update, delete, list)
- Data operations (read, write, delete, export, import)
- Analysis operations (run, read, delete, config)
- Forecast operations (run, read, delete, config)
- System operations (config, monitor, backup, restore)
- Security operations (audit, manage, monitor)
- API operations (create, read, delete, config)
- Scope operations (create, read, update, delete)

**Compliance:**
- NIST SP 800-53 AC-3 (Access Enforcement)
- NIST SP 800-53 AC-6 (Least Privilege)

#### Attribute-Based Access Control (abac.py)

Implements fine-grained ABAC based on user, resource, and environment attributes:

```python
from momento.security import abac, Subject, Resource, Environment, AccessRequest

# Create access request
subject = Subject(user_id=123, email="user@example.com", role="analyst", tier="premium")
resource = Resource(
    resource_type="forecast",
    resource_id="forecast-123",
    sensitivity=ResourceSensitivity.CONFIDENTIAL
)
environment = Environment(
    ip_address="192.168.1.100",
    network_trust=NetworkTrust.TRUSTED,
    risk_score=0.2
)

request = AccessRequest(subject=subject, resource=resource, environment=environment, action="read")

# Evaluate access
decision = abac.evaluate(request)
# Returns: PERMIT, DENY, or NOT_APPLICABLE
```

**Attributes:**
- User: ID, email, role, tier, department, location, MFA status
- Resource: Type, ID, owner, sensitivity, classification, scope
- Environment: Time, IP, user agent, geolocation, network trust, risk score

**Policy Conditions:**
- Operators: eq, ne, gt, lt, gte, lte, in, contains, regex

**Compliance:**
- NIST SP 800-162 (ABAC)
- XACML standard

### 3. Encryption System

#### AES-256-GCM Encryption (encryption.py)

Implements FIPS-140-2 compliant encryption for data at rest:

```python
from momento.security import encryption, EncryptedData

# Encrypt data
encrypted = encryption.encrypt(
    plaintext="sensitive data",
    context="user:123:api_key"
)

# Decrypt data
decrypted = encryption.decrypt(encrypted, context="user:123:api_key")

# Encrypt dictionary
data = {"key": "value", "secret": "hidden"}
encrypted_dict = encryption.encrypt_dict(data, context="user:123")

# Encrypt specific field
encrypted_field = encryption.encrypt_field(
    value="secret-value",
    field_name="api_key",
    resource_id="user-123"
)
```

**Features:**
- AES-256-GCM (NIST SP 800-38D)
- 96-bit nonce for GCM
- 16-byte authentication tag
- PBKDF2 key derivation (100,000 iterations)
- Key rotation support
- Context-aware key derivation

**Compliance:**
- NIST SP 800-38D (GCM)
- NIST SP 800-57 (Key Management)
- FIPS-140-2

### 4. Zero-Trust Middleware

#### Zero-Trust Security Middleware (zero_trust.py)

Implements continuous verification and risk-based access control:

```python
from momento.security import ZeroTrustMiddleware, SecurityContext

# Middleware is automatically added to FastAPI app
# Access security context in endpoints
from fastapi import Request

@app.get("/api/v1/data")
async def get_data(request: Request):
    context: SecurityContext = request.state.security_context
    if context.risk_level == RiskLevel.HIGH:
        # Require additional verification
        pass
```

**Features:**
- Continuous authentication verification
- Network trust assessment
- Risk-based authorization
- IP-based filtering
- Rate limiting
- Session age tracking
- Geographic anomaly detection

**Security Levels:**
- PUBLIC - No authentication required
- INTERNAL - Authenticated users
- CONFIDENTIAL - MFA required
- RESTRICTED - Additional verification

**Risk Levels:**
- LOW - Normal access
- MEDIUM - Monitor closely
- HIGH - Require re-authentication
- CRITICAL - Block access

**Compliance:**
- NIST SP 800-207 (Zero Trust Architecture)
- DoD Zero Trust Reference Architecture

### 5. Security Monitoring

#### Security Monitoring System (monitoring.py)

Implements real-time security monitoring and intrusion detection:

```python
from momento.security import security_monitor, SecurityEvent, SecurityEventType

# Record security event
event = SecurityEvent(
    event_type=SecurityEventType.AUTH_FAILURE,
    severity=SecurityEventSeverity.HIGH,
    user_id=123,
    email="user@example.com",
    ip_address="192.168.1.100",
    details={"attempts": 5}
)
security_monitor.record_event(event)

# Query events
events = security_monitor.get_events(
    event_type=SecurityEventType.AUTH_FAILURE,
    since=datetime.now(timezone.utc) - timedelta(hours=24)
)

# Get security summary
summary = security_monitor.get_security_summary(hours=24)
```

**Event Types:**
- Authentication (success, failure, lockout, MFA)
- Authorization (permission denied, scope denied)
- Network (suspicious IP, blocked IP, rate limit, DDoS)
- Data (access, export, deletion, sensitive access)
- System (config change, user management)
- Anomaly (detected, behavior, volume)

**Anomaly Detection Rules:**
- Multiple auth failures from same IP
- High request rate from single IP
- Geographic anomalies
- Behavioral anomalies

**Compliance:**
- NIST SP 800-94 (Intrusion Detection)
- ISO 27001 A.12.4.1

#### Intrusion Detection Engine

Signature-based detection for common attacks:

```python
from momento.security import intrusion_detection

# Analyze input for attack patterns
request = {
    "params": {"id": "1' OR '1'='1"},
    "body": {"data": "<script>alert('xss')</script>"},
    "ip_address": "192.168.1.100"
}

events = intrusion_detection.analyze_request(request)
# Returns list of detected security events
```

**Attack Patterns:**
- SQL injection
- XSS (Cross-Site Scripting)
- Path traversal
- Command injection

### 6. Audit Logging

#### Compliance Audit Logging (audit.py)

Implements comprehensive audit logging for regulatory compliance:

```python
from momento.security import audit_logger, AuditCategory, AuditOutcome

# Log authentication
audit_logger.log_authentication(
    email="user@example.com",
    success=True,
    ip_address="192.168.1.100",
    user_id=123,
    method="password"
)

# Log authorization
audit_logger.log_authorization(
    user_id=123,
    email="user@example.com",
    role="analyst",
    resource_type="forecast",
    resource_id="forecast-123",
    action="read",
    permitted=True
)

# Log data access
audit_logger.log_data_access(
    user_id=123,
    email="user@example.com",
    resource_type="rounds",
    resource_id="round-456",
    action="read",
    sensitive=False
)

# Generate compliance report
report = audit_logger.generate_compliance_report(
    standard="nist_800_53",
    since=datetime.now(timezone.utc) - timedelta(days=30)
)
```

**Audit Categories:**
- Authentication & Authorization
- Data Access & Operations
- System Operations
- Security Events
- Compliance & Governance

**Compliance Standards:**
- NIST SP 800-53 (AU-2, AU-3, AU-12)
- ISO 27001 (A.12.3)
- SOC 2 (CC6.1, CC6.6, CC6.7)
- PCI DSS (Requirement 10)
- HIPAA (45 CFR §164.312)

### 7. TLS Configuration

#### Security Headers Middleware (tls_config.py)

Implements OWASP recommended security headers:

```python
from momento.security import SecurityHeadersMiddleware, SecurityHeaderConfig

# Middleware is automatically added to FastAPI app
# Headers added to all responses:
# - Strict-Transport-Security (HSTS)
# - Content-Security-Policy (CSP)
# - X-Content-Type-Options
# - X-Frame-Options
# - X-XSS-Protection
# - Referrer-Policy
# - Permissions-Policy
# - Cross-Origin-Opener-Policy
# - Cross-Origin-Embedder-Policy
```

**Security Headers:**
- HSTS: max-age=31536000; includeSubDomains; preload
- CSP: default-src 'self'; script-src 'self' 'unsafe-inline'...
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: geolocation=(), microphone=(), camera=()...

**Compliance:**
- NIST SP 800-52 Rev. 2 (TLS Configuration)
- OWASP Secure Headers
- RFC 8446 (TLS 1.3)

### 8. Security Configuration

#### Centralized Security Configuration (security_config.py)

Environment-based security configuration:

```python
from momento.security_config import security_config, SecurityLevel

# Security level (environment variable: MOMENTO_SECURITY_LEVEL)
# Options: development, staging, production, high_security

# Access configuration
print(f"Security Level: {security_config.level}")
print(f"MFA Enabled: {security_config.authentication.mfa_enabled}")
print(f"Zero-Trust: {security_config.zero_trust_enabled}")
print(f"Rate Limiting: {security_config.network.rate_limiting_enabled}")
```

**Configuration Options:**

**Authentication:**
- `MOMENTO_MFA_ENABLED` - Enable MFA (default: true)
- `MOMENTO_MFA_REQUIRED_ADMIN` - Require MFA for admins (default: true)
- `MOMENTO_PASSWORD_MIN_LENGTH` - Minimum password length (default: 12)

**Network:**
- `MOMENTO_RATE_LIMITING` - Enable rate limiting (default: true)
- `MOMENTO_DDOS_PROTECTION` - Enable DDoS protection (default: true)

**Monitoring:**
- `MOMENTO_ANOMALY_DETECTION` - Enable anomaly detection (default: true)

**Zero-Trust:**
- `MOMENTO_ZERO_TRUST_STRICT` - Enable strict zero-trust mode (default: false)

**Security Headers:**
- `MOMENTO_HSTS_ENABLED` - Enable HSTS (default: true)
- `MOMENTO_HSTS_PRELOAD` - Enable HSTS preload (default: false)

## Deployment Guide

### Environment Variables

Configure security via environment variables:

```bash
# Security Level
export MOMENTO_SECURITY_LEVEL=production

# Authentication
export MOMENTO_MFA_ENABLED=true
export MOMENTO_MFA_REQUIRED_ADMIN=true
export MOMENTO_PASSWORD_MIN_LENGTH=12

# Network Security
export MOMENTO_RATE_LIMITING=true
export MOMENTO_DDOS_PROTECTION=true

# Monitoring
export MOMENTO_ANOMALY_DETECTION=true

# Zero-Trust
export MOMENTO_ZERO_TRUST_STRICT=false

# Security Headers
export MOMENTO_HSTS_ENABLED=true
export MOMENTO_HSTS_PRELOAD=true
```

### TLS Configuration

For production deployment, configure TLS 1.3:

**Uvicorn:**
```bash
uvicorn momento.api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --ssl-keyfile /path/to/private.key \
    --ssl-certfile /path/to/certificate.crt \
    --ssl-ca-certs /path/to/ca_bundle.crt
```

**Nginx:**
See `TLSConfiguration.get_nginx_config()` for recommended configuration.

**Apache:**
See `TLSConfiguration.get_apache_config()` for recommended configuration.

### Database Schema

The following tables are used for security:

```sql
-- Users table (existing)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL,
    tier TEXT NOT NULL,
    display_name TEXT,
    created_at TEXT NOT NULL,
    last_login TEXT,
    active INTEGER NOT NULL DEFAULT 1
);

-- Audit log table (existing)
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

-- Additional tables to add for MFA:
CREATE TABLE user_mfa (
    user_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'disabled',
    secret TEXT,
    backup_codes TEXT,  -- JSON array
    backup_codes_used TEXT,  -- JSON array
    verified_at TEXT,
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT,
    last_used_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Compliance Checklist

### NIST SP 800-53

- [x] AC-3: Access Enforcement (RBAC + ABAC)
- [x] AC-6: Least Privilege (Role-based permissions)
- [x] AU-2: Audit Events (Comprehensive logging)
- [x] AU-3: Audit Record Content (Structured events)
- [x] AU-12: Audit Generation (Real-time logging)
- [x] SC-8: Transmission Confidentiality (TLS 1.3)
- [x] SC-12: Cryptographic Key Management (Key rotation)
- [x] SC-13: Cryptographic Protection (AES-256-GCM)
- [x] IA-2: Identification and Authentication (JWT + MFA)
- [x] IA-5: Authenticator Management (Password policy)

### ISO 27001

- [x] A.9.1: Access control policy
- [x] A.9.2: User access management
- [x] A.9.3: User responsibilities
- [x] A.9.4: System access control
- [x] A.10: Cryptography
- [x] A.12.3: Backup
- [x] A.14.2: System acquisition
- [x] A.16.1: Management of information security incidents

### SOC 2

- [x] CC6.1: Logical and physical access controls
- [x] CC6.6: System monitoring
- [x] CC6.7: System configuration
- [x] CC7.2: System operation monitoring
- [x] CC7.3: Change management

### PCI DSS

- [x] Requirement 2: Protect system components
- [x] Requirement 3: Protect stored data (Encryption)
- [x] Requirement 4: Encrypt transmission (TLS)
- [x] Requirement 7: Restrict access (RBAC)
- [x] Requirement 8: Identify and authenticate (MFA)
- [x] Requirement 10: Track and monitor (Audit logging)

## Best Practices

### 1. Key Management

- Use a proper KMS (AWS KMS, Azure Key Vault, GCP KMS) in production
- Rotate encryption keys every 90 days
- Never store keys in code or configuration files
- Use environment variables or secret management systems

### 2. Password Policy

- Minimum 12 characters
- Require uppercase, lowercase, numbers, and special characters
- Force password rotation every 90 days
- Implement password history checking

### 3. Session Management

- Use short-lived access tokens (1 hour)
- Implement refresh token rotation
- Invalidate sessions on password change
- Track concurrent sessions

### 4. Monitoring

- Set up alerts for high-severity events
- Review security logs daily
- Implement log aggregation (ELK, Splunk)
- Regular security audits

### 5. Testing

- Regular penetration testing
- Security code reviews
- Dependency vulnerability scanning
- Automated security testing in CI/CD

## Troubleshooting

### MFA Issues

**Problem:** User cannot login after MFA enabled
**Solution:** Use backup codes or disable MFA via admin interface

**Problem:** QR code not generating
**Solution:** Check that qrcode and pillow packages are installed

### Rate Limiting

**Problem:** Legitimate users being rate-limited
**Solution:** Increase limits in security_config.py or whitelist IP addresses

### Encryption

**Problem:** Decryption fails
**Solution:** Ensure context matches encryption context exactly

### Zero-Trust

**Problem:** All requests being blocked
**Solution:** Check public_paths configuration and ensure authentication is working

## Support

For security issues or questions:
1. Review this documentation
2. Check security logs in the audit_log table
3. Review security event monitoring output
4. Contact security team for critical issues

## References

- NIST SP 800-53: Security and Privacy Controls
- NIST SP 800-63B: Digital Identity Guidelines
- NIST SP 800-94: Guide to Intrusion Detection
- ISO 27001: Information Security Management
- SOC 2: Service Organization Control 2
- PCI DSS: Payment Card Industry Data Security Standard
- OWASP Top 10: Web Application Security Risks
- RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 6238: TOTP: Time-Based One-Time Password
