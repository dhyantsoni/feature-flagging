"""
Feature Flag Client

Provides API for checking feature access for clients based on their assigned ruleset.
Enhanced with targeting rules, scheduling, and audit logging support.
"""

import json
import os
import yaml
from typing import Dict, Any, Optional, Set

from ruleset_engine import RulesetEngine

# Optional imports for enhanced features
try:
    from targeting import get_targeting_engine
except ImportError:
    get_targeting_engine = None

try:
    from scheduling import get_schedule_engine
except ImportError:
    get_schedule_engine = None

try:
    from audit import get_audit_logger, AuditAction, EntityType
except ImportError:
    get_audit_logger = None
    AuditAction = None
    EntityType = None


class FeatureFlagClient:
    """
    Main client for feature flag evaluation based on client-ruleset assignments.
    """

    def __init__(
        self,
        config_path: str = "rulesets.yaml",
        clients_path: str = "clients.yaml",
        bootstrap_path: str = "bootstrap_defaults.json",
        baseline_ruleset: str = "baseline",
        supabase_client=None,
        enable_targeting: bool = True,
        enable_scheduling: bool = True,
        enable_audit: bool = True
    ):
        """
        Initialize the Feature Flag Client.

        Args:
            config_path: Path to rulesets configuration
            clients_path: Path to clients configuration
            bootstrap_path: Path to bootstrap defaults
            baseline_ruleset: Name of the baseline ruleset
            supabase_client: Optional Supabase client for database features
            enable_targeting: Enable targeting rules engine
            enable_scheduling: Enable scheduling engine
            enable_audit: Enable audit logging
        """
        self.config_path = config_path
        self.clients_path = clients_path
        self.bootstrap_path = bootstrap_path
        self.supabase = supabase_client

        # Initialize engine
        self.engine = RulesetEngine(baseline_ruleset_name=baseline_ruleset)

        # Initialize enhanced features
        self._targeting_engine = None
        self._schedule_engine = None
        self._audit_logger = None

        if enable_targeting and get_targeting_engine:
            self._targeting_engine = get_targeting_engine(supabase_client)
            self.engine.set_targeting_engine(self._targeting_engine)

        if enable_scheduling and get_schedule_engine:
            self._schedule_engine = get_schedule_engine(supabase_client)
            self.engine.set_schedule_engine(self._schedule_engine)

        if enable_audit and get_audit_logger:
            self._audit_logger = get_audit_logger(supabase_client)
            self.engine.set_audit_logger(self._audit_logger)

        # Load configuration
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load rulesets and clients from configuration files."""
        config_loaded = False

        # Try loading rulesets from YAML
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    rulesets = yaml.safe_load(f)
                    if rulesets:
                        self.engine.load_multiple_rulesets(rulesets)
                        config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load rulesets from YAML: {e}")

        # Fall back to bootstrap if needed
        if not config_loaded and os.path.exists(self.bootstrap_path):
            try:
                with open(self.bootstrap_path, 'r') as f:
                    rulesets = json.load(f)
                    self.engine.load_multiple_rulesets(rulesets)
                    config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load bootstrap defaults: {e}")

        if not config_loaded:
            raise RuntimeError("Failed to load ruleset configuration")

        # Load clients
        if os.path.exists(self.clients_path):
            try:
                with open(self.clients_path, 'r') as f:
                    clients_config = yaml.safe_load(f)
                    if clients_config:
                        for client_id, client_data in clients_config.items():
                            self.engine.register_client(
                                client_id,
                                client_data.get("ruleset"),
                                client_data.get("metadata", {})
                            )
            except Exception as e:
                print(f"Warning: Failed to load clients: {e}")

    def isEnabled(
        self,
        client_id: str,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature is enabled for a client.

        Args:
            client_id: Client identifier
            feature_name: Feature to check
            user_context: Optional user context for percentage rollouts

        Returns:
            True if feature is enabled, False otherwise

        Example:
            client = FeatureFlagClient()
            if client.isEnabled("acme_corp", "advanced_analytics"):
                # Show advanced analytics
                pass
            else:
                # Show baseline analytics
                pass
        """
        return self.engine.is_feature_enabled(client_id, feature_name, user_context)

    def get_client_features(self, client_id: str) -> Set[str]:
        """
        Get all features available to a client.

        Args:
            client_id: Client identifier

        Returns:
            Set of feature names
        """
        return self.engine.get_client_features(client_id)

    def register_client(
        self,
        client_id: str,
        ruleset_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a new client.

        Args:
            client_id: Unique client identifier
            ruleset_name: Ruleset to assign
            metadata: Optional metadata (name, tier, etc.)
        """
        self.engine.register_client(client_id, ruleset_name, metadata)

    def update_client_ruleset(self, client_id: str, new_ruleset: str) -> bool:
        """
        Update a client's assigned ruleset.

        Args:
            client_id: Client identifier
            new_ruleset: New ruleset name

        Returns:
            True if successful
        """
        return self.engine.client_manager.update_client_ruleset(client_id, new_ruleset)

    def activate_kill_switch(self) -> None:
        """Activate global kill switch - all clients use baseline."""
        self.engine.activate_kill_switch()

    def deactivate_kill_switch(self) -> None:
        """Deactivate kill switch - resume normal operation."""
        self.engine.deactivate_kill_switch()

    def get_all_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered clients."""
        return self.engine.get_all_clients()

    def get_all_rulesets(self) -> Dict[str, Dict[str, Any]]:
        """Get all rulesets."""
        return self.engine.get_all_rulesets()

    def reload_configuration(self) -> None:
        """Reload configuration from files."""
        self._load_configuration()

    # Enhanced evaluation methods

    def isEnabledDetailed(
        self,
        client_id: str,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if a feature is enabled with detailed evaluation info.

        Args:
            client_id: Client identifier
            feature_name: Feature to check
            user_context: Optional user context

        Returns:
            Dict with 'enabled', 'reason', 'source', and debug info
        """
        return self.engine.is_feature_enabled_detailed(client_id, feature_name, user_context)

    # Targeting methods

    def add_targeting_rule(self, rule_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new targeting rule."""
        if self._targeting_engine:
            result = self._targeting_engine.add_rule(rule_config)
            if result and self._audit_logger:
                self._audit_logger.log(
                    AuditAction.TARGETING_RULE_CREATE,
                    EntityType.TARGETING_RULE,
                    result.get("id"),
                    rule_config.get("name"),
                    after=rule_config
                )
            return result
        return None

    def update_targeting_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing targeting rule."""
        if self._targeting_engine:
            success = self._targeting_engine.update_rule(rule_id, updates)
            if success and self._audit_logger:
                self._audit_logger.log(
                    AuditAction.TARGETING_RULE_UPDATE,
                    EntityType.TARGETING_RULE,
                    rule_id,
                    after=updates
                )
            return success
        return False

    def delete_targeting_rule(self, rule_id: str) -> bool:
        """Delete a targeting rule."""
        if self._targeting_engine:
            return self._targeting_engine.delete_rule(rule_id)
        return False

    def list_targeting_rules(self, feature_name: Optional[str] = None) -> list:
        """List targeting rules."""
        if self._targeting_engine:
            return self._targeting_engine.list_rules(feature_name)
        return []

    # Scheduling methods

    def add_schedule(self, schedule_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new feature schedule."""
        if self._schedule_engine:
            result = self._schedule_engine.add_schedule(schedule_config)
            if result and self._audit_logger:
                self._audit_logger.log(
                    AuditAction.SCHEDULE_CREATE,
                    EntityType.SCHEDULE,
                    result.get("id"),
                    schedule_config.get("feature_name"),
                    after=schedule_config
                )
            return result
        return None

    def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing schedule."""
        if self._schedule_engine:
            success = self._schedule_engine.update_schedule(schedule_id, updates)
            if success and self._audit_logger:
                self._audit_logger.log(
                    AuditAction.SCHEDULE_UPDATE,
                    EntityType.SCHEDULE,
                    schedule_id,
                    after=updates
                )
            return success
        return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if self._schedule_engine:
            return self._schedule_engine.delete_schedule(schedule_id)
        return False

    def list_schedules(self, feature_name: Optional[str] = None) -> list:
        """List schedules."""
        if self._schedule_engine:
            return self._schedule_engine.list_schedules(feature_name)
        return []

    def get_upcoming_schedules(self, hours: int = 24) -> list:
        """Get schedules starting within the next N hours."""
        if self._schedule_engine:
            return self._schedule_engine.get_upcoming_schedules(hours)
        return []

    # Audit methods

    def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Query audit logs."""
        if self._audit_logger:
            return self._audit_logger.query(
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit
            )
        return []

    def get_feature_history(self, feature_name: str, limit: int = 50) -> list:
        """Get audit history for a specific feature."""
        if self._audit_logger:
            return self._audit_logger.get_entity_history(
                EntityType.FEATURE if EntityType else "feature",
                feature_name,
                limit
            )
        return []

    def get_recent_activity(self, hours: int = 24) -> list:
        """Get recent activity."""
        if self._audit_logger:
            return self._audit_logger.get_recent_activity(hours)
        return []

    def flush_audit_logs(self):
        """Flush any buffered audit logs."""
        if self._audit_logger:
            self._audit_logger.flush()


# Global singleton instance
_default_client: Optional[FeatureFlagClient] = None


def get_client(**kwargs) -> FeatureFlagClient:
    """
    Get or create the default feature flag client singleton.

    Args:
        **kwargs: Arguments to pass to FeatureFlagClient constructor

    Returns:
        The default FeatureFlagClient instance
    """
    global _default_client
    if _default_client is None:
        _default_client = FeatureFlagClient(**kwargs)
    return _default_client


def isEnabled(
    client_id: str,
    feature_name: str,
    user_context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Convenience function using default client.

    Args:
        client_id: Client identifier
        feature_name: Feature to check
        user_context: Optional user context

    Returns:
        True if feature is enabled
    """
    client = get_client()
    return client.isEnabled(client_id, feature_name, user_context)
