"""
Audit Logging Module

Tracks all changes to feature flags, clients, rulesets, and other entities.
Provides queryable audit trail for compliance and debugging.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from flask import request, g
import logging

logger = logging.getLogger(__name__)


class AuditAction:
    """Standard audit actions."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ENABLE = "enable"
    DISABLE = "disable"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    LOGIN = "login"
    LOGOUT = "logout"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"
    KILL_SWITCH_ON = "kill_switch_on"
    KILL_SWITCH_OFF = "kill_switch_off"
    RULESET_CHANGE = "ruleset_change"
    SCHEDULE_CREATE = "schedule_create"
    SCHEDULE_UPDATE = "schedule_update"
    TARGETING_RULE_CREATE = "targeting_rule_create"
    TARGETING_RULE_UPDATE = "targeting_rule_update"


class EntityType:
    """Entity types for audit logging."""
    FEATURE = "feature"
    CLIENT = "client"
    RULESET = "ruleset"
    API_KEY = "api_key"
    SCHEDULE = "schedule"
    TARGETING_RULE = "targeting_rule"
    SEGMENT = "segment"
    OVERRIDE = "override"
    SYSTEM = "system"


class ActorType:
    """Actor types for audit logging."""
    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"


class AuditLogger:
    """
    Audit logger for tracking changes.

    Logs all modifications to entities with before/after values,
    actor information, and metadata.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_size = 10  # Flush after this many entries
        self._fallback_logs: List[Dict[str, Any]] = []  # In-memory fallback

    def _get_request_info(self) -> Dict[str, Any]:
        """Extract request information for audit log."""
        info = {
            "ip_address": None,
            "user_agent": None
        }

        try:
            if request:
                info["ip_address"] = request.remote_addr
                info["user_agent"] = request.headers.get("User-Agent", "")[:500]
        except RuntimeError:
            # Outside request context
            pass

        return info

    def _get_actor_info(self) -> Dict[str, Any]:
        """Extract actor information from request context."""
        actor = {
            "actor_type": ActorType.SYSTEM,
            "actor_id": "system",
            "actor_name": "System"
        }

        try:
            # Check for API key in flask.g
            if hasattr(g, 'api_key_data') and g.api_key_data:
                key_data = g.api_key_data
                actor["actor_type"] = ActorType.API_KEY
                actor["actor_id"] = key_data.get("id", key_data.get("key_prefix", "unknown"))
                actor["actor_name"] = key_data.get("name", "API Key")

            # Check for user session (if implemented)
            elif hasattr(g, 'user') and g.user:
                actor["actor_type"] = ActorType.USER
                actor["actor_id"] = g.user.get("id", "unknown")
                actor["actor_name"] = g.user.get("name", g.user.get("email", "User"))
        except RuntimeError:
            # Outside request context
            pass

        return actor

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        actor_override: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event.

        Args:
            action: Action performed (see AuditAction)
            entity_type: Type of entity (see EntityType)
            entity_id: Unique identifier of the entity
            entity_name: Human-readable name
            before: State before change
            after: State after change
            metadata: Additional context
            actor_override: Override auto-detected actor info
        """
        request_info = self._get_request_info()
        actor_info = actor_override if actor_override else self._get_actor_info()

        changes = None
        if before is not None or after is not None:
            changes = {
                "before": self._sanitize_for_json(before),
                "after": self._sanitize_for_json(after)
            }

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "entity_name": entity_name,
            "actor_type": actor_info.get("actor_type"),
            "actor_id": actor_info.get("actor_id"),
            "actor_name": actor_info.get("actor_name"),
            "changes": changes,
            "metadata": self._sanitize_for_json(metadata or {}),
            "ip_address": request_info.get("ip_address"),
            "user_agent": request_info.get("user_agent")
        }

        self._buffer.append(log_entry)

        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            self.flush()

    def _sanitize_for_json(self, data: Any) -> Any:
        """Sanitize data for JSON storage."""
        if data is None:
            return None

        if isinstance(data, (str, int, float, bool)):
            return data

        if isinstance(data, datetime):
            return data.isoformat()

        if isinstance(data, dict):
            return {k: self._sanitize_for_json(v) for k, v in data.items()}

        if isinstance(data, (list, tuple)):
            return [self._sanitize_for_json(v) for v in data]

        return str(data)

    def flush(self):
        """Flush buffered logs to database."""
        if not self._buffer:
            return

        entries = self._buffer.copy()
        self._buffer = []

        if self.supabase:
            try:
                self.supabase.client.table("audit_logs").insert(entries).execute()
            except Exception as e:
                logger.error(f"Error flushing audit logs: {e}")
                # Store in fallback
                self._fallback_logs.extend(entries)
                # Retry fallback logs if we have too many
                if len(self._fallback_logs) > 100:
                    self._retry_fallback_logs()
        else:
            # No Supabase - store in memory
            self._fallback_logs.extend(entries)

    def _retry_fallback_logs(self):
        """Retry sending fallback logs to database."""
        if not self.supabase or not self._fallback_logs:
            return

        try:
            self.supabase.client.table("audit_logs").insert(self._fallback_logs).execute()
            self._fallback_logs = []
        except Exception as e:
            logger.error(f"Error retrying fallback logs: {e}")
            # Keep only most recent 100 entries to prevent memory issues
            self._fallback_logs = self._fallback_logs[-100:]

    def query(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            action: Filter by action
            actor_id: Filter by actor
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of audit log entries
        """
        if not self.supabase:
            # Return from fallback logs
            results = self._fallback_logs.copy()

            if entity_type:
                results = [r for r in results if r.get("entity_type") == entity_type]
            if entity_id:
                results = [r for r in results if r.get("entity_id") == entity_id]
            if action:
                results = [r for r in results if r.get("action") == action]
            if actor_id:
                results = [r for r in results if r.get("actor_id") == actor_id]

            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return results[offset:offset + limit]

        try:
            query = self.supabase.client.table("audit_logs").select("*")

            if entity_type:
                query = query.eq("entity_type", entity_type)
            if entity_id:
                query = query.eq("entity_id", entity_id)
            if action:
                query = query.eq("action", action)
            if actor_id:
                query = query.eq("actor_id", actor_id)
            if start_time:
                query = query.gte("timestamp", start_time.isoformat())
            if end_time:
                query = query.lte("timestamp", end_time.isoformat())

            result = query.order("timestamp", desc=True).range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error querying audit logs: {e}")
            return []

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get complete history for a specific entity."""
        return self.query(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit
        )

    def get_recent_activity(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent activity across all entities."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return self.query(start_time=start_time, limit=limit)

    def get_actor_activity(
        self,
        actor_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all activity by a specific actor."""
        return self.query(actor_id=actor_id, limit=limit)

    # Convenience methods for common operations

    def log_feature_change(
        self,
        feature_name: str,
        action: str,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None
    ):
        """Log a feature flag change."""
        self.log(
            action=action,
            entity_type=EntityType.FEATURE,
            entity_id=feature_name,
            entity_name=feature_name,
            before=before,
            after=after
        )

    def log_client_change(
        self,
        client_id: str,
        action: str,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None
    ):
        """Log a client change."""
        self.log(
            action=action,
            entity_type=EntityType.CLIENT,
            entity_id=client_id,
            entity_name=client_id,
            before=before,
            after=after
        )

    def log_ruleset_change(
        self,
        ruleset_name: str,
        action: str,
        before: Optional[Dict] = None,
        after: Optional[Dict] = None
    ):
        """Log a ruleset change."""
        self.log(
            action=action,
            entity_type=EntityType.RULESET,
            entity_id=ruleset_name,
            entity_name=ruleset_name,
            before=before,
            after=after
        )

    def log_kill_switch(self, activated: bool):
        """Log kill switch toggle."""
        self.log(
            action=AuditAction.KILL_SWITCH_ON if activated else AuditAction.KILL_SWITCH_OFF,
            entity_type=EntityType.SYSTEM,
            entity_id="kill_switch",
            entity_name="Global Kill Switch",
            after={"activated": activated}
        )

    def log_api_key_created(self, key_data: Dict[str, Any]):
        """Log API key creation."""
        # Don't log the actual key hash
        safe_data = {k: v for k, v in key_data.items() if k not in ["key_hash"]}
        self.log(
            action=AuditAction.API_KEY_CREATE,
            entity_type=EntityType.API_KEY,
            entity_id=key_data.get("id", key_data.get("key_prefix")),
            entity_name=key_data.get("name"),
            after=safe_data
        )

    def log_api_key_revoked(self, key_id: str, key_name: str):
        """Log API key revocation."""
        self.log(
            action=AuditAction.API_KEY_REVOKE,
            entity_type=EntityType.API_KEY,
            entity_id=key_id,
            entity_name=key_name
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(supabase_client=None) -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(supabase_client)
    return _audit_logger


def audit_log(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    **kwargs
):
    """Convenience function to log an audit event."""
    logger = get_audit_logger()
    logger.log(action, entity_type, entity_id, **kwargs)
