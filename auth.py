"""
API Authentication Module

Provides API key authentication and rate limiting for the feature flagging system.
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Dict, Any, Optional, Tuple, List
from flask import request, jsonify, g
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(self):
        self.buckets: Dict[str, List[float]] = {}
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()

    def _cleanup(self):
        """Remove expired entries."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        hour_ago = now - 3600
        for key in list(self.buckets.keys()):
            self.buckets[key] = [t for t in self.buckets[key] if t > hour_ago]
            if not self.buckets[key]:
                del self.buckets[key]
        self.last_cleanup = now

    def is_allowed(self, key: str, limit: int) -> Tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        self._cleanup()
        now = time.time()
        hour_ago = now - 3600

        if key not in self.buckets:
            self.buckets[key] = []

        # Filter to last hour
        self.buckets[key] = [t for t in self.buckets[key] if t > hour_ago]

        current_count = len(self.buckets[key])
        remaining = max(0, limit - current_count - 1)

        if current_count >= limit:
            # Find when oldest request expires
            reset_time = int(min(self.buckets[key]) + 3600 - now)
            return False, 0, reset_time

        self.buckets[key].append(now)
        return True, remaining, 3600


class APIKeyManager:
    """Manages API key creation, validation, and storage."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.rate_limiter = RateLimiter()
        # In-memory cache for API keys (with TTL)
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl = 300  # 5 minutes

    @staticmethod
    def generate_key() -> Tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (full_key, prefix, hash)
        """
        # Generate 32 random bytes = 64 hex characters
        raw_key = secrets.token_hex(32)
        prefix = f"ff_{raw_key[:8]}"  # ff_ prefix + first 8 chars
        full_key = f"{prefix}_{raw_key[8:]}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        return full_key, prefix, key_hash

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage/lookup."""
        return hashlib.sha256(key.encode()).hexdigest()

    def create_key(
        self,
        name: str,
        client_id: Optional[str] = None,
        permissions: List[str] = None,
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None,
        description: str = "",
        created_by: str = "system"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Create a new API key.

        Returns:
            Tuple of (full_key, key_record)
        """
        full_key, prefix, key_hash = self.generate_key()

        permissions = permissions or ["read"]
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        key_record = {
            "key_hash": key_hash,
            "key_prefix": prefix,
            "name": name,
            "description": description,
            "client_id": client_id,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "is_active": True,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_by": created_by,
            "metadata": {}
        }

        if self.supabase:
            try:
                result = self.supabase.client.table("api_keys").insert(key_record).execute()
                key_record = result.data[0] if result.data else key_record
            except Exception as e:
                logger.warning(f"Could not save API key to Supabase: {e}")

        return full_key, key_record

    def validate_key(self, key: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validate an API key.

        Returns:
            Tuple of (is_valid, key_data, error_message)
        """
        if not key:
            return False, None, "API key required"

        key_hash = self.hash_key(key)

        # Check cache first
        if key_hash in self._cache:
            key_data, cached_at = self._cache[key_hash]
            if time.time() - cached_at < self._cache_ttl:
                return self._validate_key_data(key_data)

        # Query database
        key_data = None
        if self.supabase:
            try:
                result = self.supabase.client.table("api_keys").select("*").eq("key_hash", key_hash).execute()
                if result.data:
                    key_data = result.data[0]
                    self._cache[key_hash] = (key_data, time.time())
            except Exception as e:
                logger.error(f"Error validating API key: {e}")
                return False, None, "Database error"

        if not key_data:
            return False, None, "Invalid API key"

        return self._validate_key_data(key_data)

    def _validate_key_data(self, key_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Validate key data after retrieval."""
        if not key_data.get("is_active", False):
            return False, None, "API key is inactive"

        expires_at = key_data.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.now(timezone.utc):
                return False, None, "API key has expired"

        return True, key_data, ""

    def check_rate_limit(self, key_data: Dict[str, Any]) -> Tuple[bool, int, int]:
        """
        Check rate limit for an API key.

        Returns:
            Tuple of (allowed, remaining, reset_seconds)
        """
        key_hash = key_data.get("key_hash", "")
        limit = key_data.get("rate_limit", 1000)

        if limit == -1:  # Unlimited
            return True, -1, 0

        return self.rate_limiter.is_allowed(key_hash, limit)

    def has_permission(self, key_data: Dict[str, Any], required: str) -> bool:
        """Check if API key has required permission."""
        permissions = key_data.get("permissions", [])

        # Admin has all permissions
        if "admin" in permissions:
            return True

        # Write includes read
        if required == "read" and "write" in permissions:
            return True

        return required in permissions

    def update_last_used(self, key_hash: str):
        """Update last_used_at timestamp."""
        if self.supabase:
            try:
                self.supabase.client.table("api_keys").update({
                    "last_used_at": datetime.now(timezone.utc).isoformat()
                }).eq("key_hash", key_hash).execute()
            except Exception as e:
                logger.debug(f"Could not update last_used: {e}")

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if self.supabase:
            try:
                self.supabase.client.table("api_keys").update({
                    "is_active": False
                }).eq("id", key_id).execute()

                # Clear from cache
                for key_hash, (data, _) in list(self._cache.items()):
                    if data.get("id") == key_id:
                        del self._cache[key_hash]

                return True
            except Exception as e:
                logger.error(f"Error revoking API key: {e}")
        return False

    def list_keys(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List API keys (without hashes)."""
        if not self.supabase:
            return []

        try:
            query = self.supabase.client.table("api_keys").select(
                "id, key_prefix, name, description, client_id, permissions, "
                "rate_limit, is_active, expires_at, last_used_at, created_at, created_by"
            )

            if client_id:
                query = query.eq("client_id", client_id)

            result = query.order("created_at", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error listing API keys: {e}")
            return []


# Global API key manager instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(supabase_client=None) -> APIKeyManager:
    """Get or create the global API key manager."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager(supabase_client)
    return _api_key_manager


def require_api_key(permission: str = "read"):
    """
    Decorator to require API key authentication.

    Usage:
        @app.route('/api/something')
        @require_api_key('read')
        def get_something():
            # g.api_key_data contains the validated key info
            return jsonify({"data": "..."})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get API key from header
            auth_header = request.headers.get("Authorization", "")
            api_key = None

            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            elif auth_header.startswith("ApiKey "):
                api_key = auth_header[7:]
            else:
                # Also check X-API-Key header
                api_key = request.headers.get("X-API-Key")

            # Allow bypass in development (if explicitly enabled)
            if not api_key and request.headers.get("X-Dev-Bypass") == "true":
                g.api_key_data = {"permissions": ["admin"], "client_id": None}
                return f(*args, **kwargs)

            manager = get_api_key_manager()

            # Validate key
            is_valid, key_data, error = manager.validate_key(api_key)
            if not is_valid:
                return jsonify({
                    "success": False,
                    "error": error,
                    "code": "UNAUTHORIZED"
                }), 401

            # Check permission
            if not manager.has_permission(key_data, permission):
                return jsonify({
                    "success": False,
                    "error": f"Insufficient permissions. Required: {permission}",
                    "code": "FORBIDDEN"
                }), 403

            # Check rate limit
            allowed, remaining, reset = manager.check_rate_limit(key_data)

            # Add rate limit headers to response
            @after_this_request
            def add_rate_limit_headers(response):
                response.headers["X-RateLimit-Limit"] = str(key_data.get("rate_limit", 1000))
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(reset)
                return response

            if not allowed:
                return jsonify({
                    "success": False,
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMITED",
                    "retry_after": reset
                }), 429

            # Store key data in flask.g for use in route
            g.api_key_data = key_data

            # Update last used (async-ish, don't wait)
            try:
                manager.update_last_used(key_data.get("key_hash", ""))
            except:
                pass

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def after_this_request(f):
    """Register a function to be called after the current request."""
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(f)
    return f
