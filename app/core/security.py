"""
Security middleware and rate limiting for EmberFrame V2
"""

import time
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, List
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis
import logging

from app.core.config import get_settings
from app.utils.helpers import get_client_ip

logger = logging.getLogger(__name__)
settings = get_settings()


class SecurityHeaders:
    """Security headers configuration"""

    @staticmethod
    def get_headers() -> Dict[str, str]:
        return {
            # Prevent clickjacking
            "X-Frame-Options": "SAMEORIGIN",

            # XSS protection
            "X-XSS-Protection": "1; mode=block",

            # MIME type sniffing protection
            "X-Content-Type-Options": "nosniff",

            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Content Security Policy
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' https://cdnjs.cloudflare.com; "
                "connect-src 'self' ws: wss:; "
                "media-src 'self' blob:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            ),

            # HSTS (only in production with HTTPS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" if not settings.DEBUG else "",

            # Permissions policy
            "Permissions-Policy": (
                "camera=(), "
                "microphone=(), "
                "geolocation=(), "
                "interest-cohort=()"
            )
        }


class RateLimiter:
    """Redis-based rate limiter"""

    def __init__(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory rate limiting: {e}")
            self.redis_client = None
            self.memory_store: Dict[str, Dict] = {}

    def _get_key(self, identifier: str, window: str) -> str:
        """Generate rate limit key"""
        return f"rate_limit:{window}:{identifier}"

    def _cleanup_memory_store(self):
        """Clean up expired entries from memory store"""
        current_time = time.time()
        expired_keys = []

        for key, data in self.memory_store.items():
            if current_time > data.get('reset_time', 0):
                expired_keys.append(key)

        for key in expired_keys:
            del self.memory_store[key]

    def check_rate_limit(self, identifier: str, limit: int, window: int) -> Dict[str, any]:
        """
        Check if request is within rate limit

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            Dict with rate limit status and metadata
        """
        current_time = time.time()
        reset_time = current_time + window
        key = self._get_key(identifier, f"{window}s")

        if self.redis_client:
            try:
                # Use Redis for distributed rate limiting
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, window)
                results = pipe.execute()

                current_requests = results[0]

                return {
                    'allowed': current_requests <= limit,
                    'limit': limit,
                    'remaining': max(0, limit - current_requests),
                    'reset_time': reset_time,
                    'retry_after': window if current_requests > limit else 0
                }

            except Exception as e:
                logger.error(f"Redis rate limiting error: {e}")
                # Fallback to memory-based limiting

        # Memory-based rate limiting (fallback)
        self._cleanup_memory_store()

        if key not in self.memory_store:
            self.memory_store[key] = {
                'count': 0,
                'reset_time': reset_time
            }

        data = self.memory_store[key]

        # Reset if window expired
        if current_time > data['reset_time']:
            data['count'] = 0
            data['reset_time'] = reset_time

        data['count'] += 1

        return {
            'allowed': data['count'] <= limit,
            'limit': limit,
            'remaining': max(0, limit - data['count']),
            'reset_time': data['reset_time'],
            'retry_after': window if data['count'] > limit else 0
        }


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware"""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.security_headers = SecurityHeaders.get_headers()

        # Rate limit configurations for different endpoints
        self.rate_limits = {
            # Authentication endpoints (stricter limits)
            '/api/auth/login': {'limit': 5, 'window': 300},      # 5 per 5 minutes
            '/api/auth/register': {'limit': 3, 'window': 3600},  # 3 per hour
            '/api/auth/logout': {'limit': 10, 'window': 60},     # 10 per minute

            # API endpoints (general limits)
            '/api/': {'limit': 100, 'window': 60},               # 100 per minute
            '/api/files/upload': {'limit': 10, 'window': 60},    # 10 uploads per minute
            '/api/files/search': {'limit': 20, 'window': 60},    # 20 searches per minute

            # WebSocket connections
            '/ws/': {'limit': 5, 'window': 60},                  # 5 connections per minute

            # Default for all other endpoints
            'default': {'limit': 200, 'window': 60}              # 200 per minute
        }

        # Blocked IPs and suspicious patterns
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns = [
            'admin', 'test', 'api', 'dev', 'staging', 'backup',
            'sql', 'injection', 'script', 'eval', 'exec'
        ]

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = get_client_ip(request)

        # Security checks
        try:
            # 1. Check blocked IPs
            if await self._check_blocked_ip(client_ip):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied"}
                )

            # 2. Check for suspicious requests
            if await self._check_suspicious_request(request):
                await self._log_suspicious_activity(request, client_ip)
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request"}
                )

            # 3. Apply rate limiting
            rate_limit_result = await self._apply_rate_limiting(request, client_ip)
            if not rate_limit_result['allowed']:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": rate_limit_result['retry_after']
                    },
                    headers={
                        "Retry-After": str(rate_limit_result['retry_after']),
                        "X-RateLimit-Limit": str(rate_limit_result['limit']),
                        "X-RateLimit-Remaining": str(rate_limit_result['remaining']),
                        "X-RateLimit-Reset": str(int(rate_limit_result['reset_time']))
                    }
                )

            # Process request
            response = await call_next(request)

            # Add security headers
            for header_name, header_value in self.security_headers.items():
                if header_value:  # Only add non-empty headers
                    response.headers[header_name] = header_value

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result['limit'])
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result['remaining'])
            response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result['reset_time']))

            # Add processing time header
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            # Log request
            await self._log_request(request, response, client_ip, process_time)

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            # Return generic error to avoid information disclosure
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )

    async def _check_blocked_ip(self, client_ip: str) -> bool:
        """Check if IP is blocked"""
        return client_ip in self.blocked_ips

    async def _check_suspicious_request(self, request: Request) -> bool:
        """Check for suspicious request patterns"""
        # Check URL for suspicious patterns
        url_path = str(request.url.path).lower()
        for pattern in self.suspicious_patterns:
            if pattern in url_path and not url_path.startswith('/api/'):
                return True

        # Check for SQL injection patterns in query parameters
        for param_value in request.query_params.values():
            if any(sql_keyword in param_value.lower() for sql_keyword in
                   ['union', 'select', 'insert', 'delete', 'drop', 'exec', 'script']):
                return True

        # Check User-Agent for bot patterns
        user_agent = request.headers.get('user-agent', '').lower()
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
        if any(pattern in user_agent for pattern in bot_patterns) and not '/api/' in str(request.url.path):
            return True

        # Check for unusually large headers
        for header_name, header_value in request.headers.items():
            if len(header_value) > 8192:  # 8KB limit per header
                return True

        return False

    async def _apply_rate_limiting(self, request: Request, client_ip: str) -> Dict[str, any]:
        """Apply rate limiting based on endpoint and client"""
        url_path = str(request.url.path)

        # Find matching rate limit configuration
        rate_config = None
        for pattern, config in self.rate_limits.items():
            if pattern != 'default' and url_path.startswith(pattern):
                rate_config = config
                break

        if not rate_config:
            rate_config = self.rate_limits['default']

        # Use client IP as identifier (could be enhanced with user ID for authenticated requests)
        identifier = client_ip

        # Check if user is authenticated and use user ID instead
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # For authenticated requests, use a combination of user token hash and IP
            token_hash = hashlib.sha256(auth_header.encode()).hexdigest()[:16]
            identifier = f"user:{token_hash}:{client_ip}"

        return self.rate_limiter.check_rate_limit(
            identifier=identifier,
            limit=rate_config['limit'],
            window=rate_config['window']
        )

    async def _log_suspicious_activity(self, request: Request, client_ip: str):
        """Log suspicious activity"""
        logger.warning(
            f"Suspicious activity detected: "
            f"IP={client_ip}, "
            f"Path={request.url.path}, "
            f"Method={request.method}, "
            f"User-Agent={request.headers.get('user-agent', 'Unknown')}"
        )

    async def _log_request(self, request: Request, response: Response, client_ip: str, process_time: float):
        """Log request for monitoring"""
        # Only log errors and slow requests to reduce noise
        if response.status_code >= 400 or process_time > 1.0:
            logger.info(
                f"Request: "
                f"IP={client_ip}, "
                f"Method={request.method}, "
                f"Path={request.url.path}, "
                f"Status={response.status_code}, "
                f"Time={process_time:.3f}s"
            )

    def block_ip(self, ip_address: str):
        """Block an IP address"""
        try:
            # Validate IP address
            ipaddress.ip_address(ip_address)
            self.blocked_ips.add(ip_address)
            logger.info(f"Blocked IP address: {ip_address}")
        except ValueError:
            logger.error(f"Invalid IP address format: {ip_address}")

    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        logger.info(f"Unblocked IP address: {ip_address}")


class AuthenticationSecurity:
    """Enhanced authentication security features"""

    def __init__(self):
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.locked_accounts: Dict[str, datetime] = {}
        self.max_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        self.attempt_window = timedelta(minutes=5)

    def record_failed_attempt(self, identifier: str) -> bool:
        """
        Record a failed login attempt

        Args:
            identifier: IP address or username

        Returns:
            True if account should be locked
        """
        current_time = datetime.utcnow()

        # Initialize attempts list if not exists
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []

        # Clean old attempts outside the window
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if current_time - attempt < self.attempt_window
        ]

        # Add current attempt
        self.failed_attempts[identifier].append(current_time)

        # Check if should lock
        if len(self.failed_attempts[identifier]) >= self.max_attempts:
            self.locked_accounts[identifier] = current_time + self.lockout_duration
            return True

        return False

    def is_locked(self, identifier: str) -> bool:
        """Check if account/IP is locked"""
        if identifier not in self.locked_accounts:
            return False

        # Check if lockout period has expired
        if datetime.utcnow() > self.locked_accounts[identifier]:
            del self.locked_accounts[identifier]
            # Also clear failed attempts
            self.failed_attempts.pop(identifier, None)
            return False

        return True

    def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts for successful login"""
        self.failed_attempts.pop(identifier, None)
        self.locked_accounts.pop(identifier, None)


class CSRFProtection:
    """CSRF protection for state-changing operations"""

    def __init__(self):
        self.token_store: Dict[str, datetime] = {}
        self.token_lifetime = timedelta(hours=1)

    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        import secrets
        token = secrets.token_urlsafe(32)
        key = f"{session_id}:{token}"
        self.token_store[key] = datetime.utcnow() + self.token_lifetime
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate CSRF token"""
        key = f"{session_id}:{token}"

        if key not in self.token_store:
            return False

        # Check expiration
        if datetime.utcnow() > self.token_store[key]:
            del self.token_store[key]
            return False

        return True

    def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self.token_store.items()
            if current_time > expiry
        ]

        for key in expired_keys:
            del self.token_store[key]


# Global instances
rate_limiter = RateLimiter()
auth_security = AuthenticationSecurity()
csrf_protection = CSRFProtection()


def get_security_middleware():
    """Get configured security middleware"""
    return SecurityMiddleware(app=None, rate_limiter=rate_limiter)


# Security utility functions
def validate_password_strength(password: str) -> Dict[str, any]:
    """Validate password strength"""
    issues = []
    score = 0

    # Length check
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    else:
        score += 1

    # Character variety checks
    if not any(c.islower() for c in password):
        issues.append("Password must contain lowercase letters")
    else:
        score += 1

    if not any(c.isupper() for c in password):
        issues.append("Password must contain uppercase letters")
    else:
        score += 1

    if not any(c.isdigit() for c in password):
        issues.append("Password must contain numbers")
    else:
        score += 1

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain special characters")
    else:
        score += 1

    # Common password check
    common_passwords = [
        "password", "123456", "password123", "admin", "letmein",
        "welcome", "monkey", "1234567890", "qwerty", "abc123"
    ]

    if password.lower() in common_passwords:
        issues.append("Password is too common")
        score = max(0, score - 2)

    strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
    strength = strength_levels[min(score, 4)]

    return {
        "valid": len(issues) == 0,
        "score": score,
        "strength": strength,
        "issues": issues
    }


def sanitize_input(input_string: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not input_string:
        return ""

    # Truncate to max length
    sanitized = input_string[:max_length]

    # Remove null bytes
    sanitized = sanitized.replace('\x00', '')

    # Remove control characters except newlines and tabs
    sanitized = ''.join(char for char in sanitized
                       if ord(char) >= 32 or char in ['\n', '\t'])

    return sanitized.strip()


def check_file_safety(filename: str, content_type: str = None) -> Dict[str, any]:
    """Check if uploaded file is safe"""
    import os

    issues = []
    safe = True

    # Check filename
    if not filename:
        issues.append("Filename is required")
        safe = False

    # Check for path traversal
    if '..' in filename or '/' in filename or '\\' in filename:
        issues.append("Invalid filename - path traversal detected")
        safe = False

    # Check file extension
    dangerous_extensions = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.php', '.asp', '.aspx', '.jsp', '.sh', '.ps1'
    ]

    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in dangerous_extensions:
        issues.append(f"File type {file_ext} is not allowed")
        safe = False

    # Check content type if provided
    if content_type:
        dangerous_types = [
            'application/x-executable',
            'application/x-msdownload',
            'application/x-msdos-program'
        ]

        if content_type in dangerous_types:
            issues.append(f"Content type {content_type} is not allowed")
            safe = False

    return {
        "safe": safe,
        "issues": issues,
        "sanitized_filename": sanitize_input(filename, 255)
    }