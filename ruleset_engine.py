"""
Rule Set Engine for Feature Flagging System

Maps clients to rulesets, which define available features.
Supports baseline fallback when features fail.
Enhanced with targeting rules and scheduling support.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum


class Ruleset:
    """
    Represents a ruleset defining available features for clients.
    Each ruleset is a feature set that clients can be assigned to.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize a ruleset.

        Args:
            name: Unique identifier for the ruleset (e.g., "enterprise_tier", "free_tier")
            config: Configuration dictionary containing:
                - description: Human-readable description
                - features: List or dict of available features
                - baseline_ruleset: Name of ruleset to fall back to on failure
                - rollout_percentage: Optional percentage for gradual rollout
                - user_targeting: Optional user whitelists/blacklists
        """
        self.name = name
        self.config = config
        self.description = config.get("description", "")
        self.baseline_ruleset = config.get("baseline_ruleset", None)

        # Parse features - can be list or dict
        features_config = config.get("features", {})
        if isinstance(features_config, list):
            # Simple list of feature names - all enabled by default
            self.features = {f: {"enabled": True} for f in features_config}
        else:
            # Dict with per-feature configuration
            self.features = features_config

    def has_feature(self, feature_name: str) -> bool:
        """
        Check if this ruleset includes a specific feature.

        Args:
            feature_name: Name of the feature to check

        Returns:
            True if feature is available in this ruleset
        """
        if feature_name not in self.features:
            return False

        feature_config = self.features[feature_name]
        if isinstance(feature_config, dict):
            return feature_config.get("enabled", True)
        return True

    def get_all_features(self) -> Set[str]:
        """Get all features available in this ruleset."""
        return {f for f, config in self.features.items()
                if (isinstance(config, dict) and config.get("enabled", True)) or config}


class ClientManager:
    """
    Manages client-to-ruleset assignments.
    """

    def __init__(self):
        """Initialize the client manager"""
        self.clients: Dict[str, Dict[str, Any]] = {}

    def register_client(
        self,
        client_id: str,
        ruleset_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a client and assign them to a ruleset.

        Args:
            client_id: Unique identifier for the client
            ruleset_name: Name of the ruleset to assign
            metadata: Optional metadata (name, tier, etc.)
        """
        self.clients[client_id] = {
            "ruleset": ruleset_name,
            "metadata": metadata or {},
            "active": True
        }

    def get_client_ruleset(self, client_id: str) -> Optional[str]:
        """
        Get the ruleset name assigned to a client.

        Args:
            client_id: Client identifier

        Returns:
            Ruleset name or None if client not found
        """
        client = self.clients.get(client_id)
        if client and client.get("active", True):
            return client.get("ruleset")
        return None

    def update_client_ruleset(self, client_id: str, new_ruleset: str) -> bool:
        """
        Update a client's assigned ruleset.

        Args:
            client_id: Client identifier
            new_ruleset: New ruleset name to assign

        Returns:
            True if successful, False if client not found
        """
        if client_id in self.clients:
            self.clients[client_id]["ruleset"] = new_ruleset
            return True
        return False

    def deactivate_client(self, client_id: str) -> bool:
        """
        Deactivate a client (they'll fall back to baseline).

        Args:
            client_id: Client identifier

        Returns:
            True if successful, False if client not found
        """
        if client_id in self.clients:
            self.clients[client_id]["active"] = False
            return True
        return False

    def get_all_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered clients."""
        return self.clients.copy()


class RulesetEngine:
    """
    Core engine managing rulesets and evaluating feature access.
    Enhanced with targeting rules and scheduling support.
    """

    def __init__(self, baseline_ruleset_name: str = "baseline"):
        """
        Initialize the ruleset engine.

        Args:
            baseline_ruleset_name: Name of the baseline/fallback ruleset
        """
        self.rulesets: Dict[str, Ruleset] = {}
        self.client_manager = ClientManager()
        self.baseline_ruleset_name = baseline_ruleset_name
        self._use_baseline = False  # Global kill switch

        # Optional enhanced engines (lazy loaded)
        self._targeting_engine = None
        self._schedule_engine = None
        self._audit_logger = None

    def set_targeting_engine(self, engine):
        """Set the targeting rules engine."""
        self._targeting_engine = engine

    def set_schedule_engine(self, engine):
        """Set the scheduling engine."""
        self._schedule_engine = engine

    def set_audit_logger(self, logger):
        """Set the audit logger."""
        self._audit_logger = logger

    def load_ruleset(self, name: str, config: Dict[str, Any]) -> None:
        """
        Load a ruleset configuration.

        Args:
            name: Name of the ruleset
            config: Configuration dictionary for the ruleset
        """
        self.rulesets[name] = Ruleset(name, config)

    def load_multiple_rulesets(self, rulesets_config: Dict[str, Dict[str, Any]]) -> None:
        """
        Load multiple rulesets at once.

        Args:
            rulesets_config: Dictionary mapping ruleset names to their configurations
        """
        for name, config in rulesets_config.items():
            self.load_ruleset(name, config)

    def register_client(
        self,
        client_id: str,
        ruleset_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a client and assign them to a ruleset.

        Args:
            client_id: Unique client identifier
            ruleset_name: Ruleset to assign
            metadata: Optional client metadata
        """
        self.client_manager.register_client(client_id, ruleset_name, metadata)

    def is_feature_enabled(
        self,
        client_id: str,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature is enabled for a specific client.

        Evaluation order:
        1. Global kill switch (forces baseline)
        2. Schedule overrides (time-based)
        3. Targeting rules (user attribute-based)
        4. Client's assigned ruleset
        5. Per-feature rollout percentage
        6. Baseline fallback on failure

        Args:
            client_id: Client identifier
            feature_name: Feature to check
            user_context: Optional user context for percentage rollouts and targeting

        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            # Check global kill switch
            if self._use_baseline:
                return self._check_baseline_feature(feature_name)

            # Get client's assigned ruleset
            ruleset_name = self.client_manager.get_client_ruleset(client_id)

            if not ruleset_name or ruleset_name not in self.rulesets:
                # Client not found or invalid ruleset - use baseline
                return self._check_baseline_feature(feature_name)

            ruleset = self.rulesets[ruleset_name]

            # Check schedule overrides first
            if self._schedule_engine:
                schedule_result, _ = self._schedule_engine.evaluate(
                    feature_name, client_id, ruleset_name
                )
                if schedule_result is not None:
                    return schedule_result

            # Check targeting rules
            if self._targeting_engine and user_context:
                # Add client context for targeting
                enhanced_context = {
                    **user_context,
                    "client_id": client_id,
                    "ruleset": ruleset_name
                }
                action, variant = self._targeting_engine.evaluate(
                    feature_name, enhanced_context, ruleset_name
                )
                if action == "enable":
                    return True
                elif action == "disable":
                    return False
                # action == "variant" or None continues to normal evaluation

            # Check if feature exists in ruleset
            if not ruleset.has_feature(feature_name):
                # Feature not in ruleset - check baseline
                return self._check_baseline_feature(feature_name)

            # Check per-feature rollout percentage
            feature_config = ruleset.features.get(feature_name, {})
            if isinstance(feature_config, dict):
                percentage = feature_config.get("percentage", 100)

                if percentage < 100 and user_context:
                    # Use consistent hashing for percentage rollout
                    if not self._passes_percentage_check(
                        client_id, feature_name, percentage, user_context
                    ):
                        return self._check_baseline_feature(feature_name)

            return True

        except Exception as e:
            # On any error, fall back to baseline
            print(f"Error evaluating feature '{feature_name}' for client '{client_id}': {e}")
            return self._check_baseline_feature(feature_name)

    def is_feature_enabled_detailed(
        self,
        client_id: str,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if feature is enabled with detailed evaluation info.

        Returns:
            Dict with 'enabled', 'reason', 'source', and other debug info
        """
        result = {
            "enabled": False,
            "reason": "unknown",
            "source": "baseline",
            "feature_name": feature_name,
            "client_id": client_id,
            "ruleset": None,
            "schedule": None,
            "targeting_rule": None
        }

        try:
            if self._use_baseline:
                result["enabled"] = self._check_baseline_feature(feature_name)
                result["reason"] = "kill_switch_active"
                result["source"] = "kill_switch"
                return result

            ruleset_name = self.client_manager.get_client_ruleset(client_id)
            result["ruleset"] = ruleset_name

            if not ruleset_name or ruleset_name not in self.rulesets:
                result["enabled"] = self._check_baseline_feature(feature_name)
                result["reason"] = "client_not_found" if not ruleset_name else "invalid_ruleset"
                result["source"] = "baseline"
                return result

            # Check schedule
            if self._schedule_engine:
                schedule_result, schedule = self._schedule_engine.evaluate(
                    feature_name, client_id, ruleset_name
                )
                if schedule_result is not None:
                    result["enabled"] = schedule_result
                    result["reason"] = "schedule_override"
                    result["source"] = "schedule"
                    result["schedule"] = {"id": schedule.id, "type": schedule.schedule_type}
                    return result

            # Check targeting
            if self._targeting_engine and user_context:
                enhanced_context = {**user_context, "client_id": client_id, "ruleset": ruleset_name}
                action, variant = self._targeting_engine.evaluate(feature_name, enhanced_context, ruleset_name)
                if action in ("enable", "disable"):
                    result["enabled"] = action == "enable"
                    result["reason"] = f"targeting_rule_{action}"
                    result["source"] = "targeting"
                    return result

            # Normal ruleset evaluation
            ruleset = self.rulesets[ruleset_name]
            if not ruleset.has_feature(feature_name):
                result["enabled"] = self._check_baseline_feature(feature_name)
                result["reason"] = "feature_not_in_ruleset"
                result["source"] = "baseline"
                return result

            feature_config = ruleset.features.get(feature_name, {})
            if isinstance(feature_config, dict):
                percentage = feature_config.get("percentage", 100)
                if percentage < 100 and user_context:
                    if not self._passes_percentage_check(client_id, feature_name, percentage, user_context):
                        result["enabled"] = self._check_baseline_feature(feature_name)
                        result["reason"] = f"percentage_rollout_{percentage}%"
                        result["source"] = "percentage"
                        return result

            result["enabled"] = True
            result["reason"] = "ruleset_enabled"
            result["source"] = "ruleset"
            return result

        except Exception as e:
            result["enabled"] = self._check_baseline_feature(feature_name)
            result["reason"] = f"error: {str(e)}"
            result["source"] = "error_fallback"
            return result

    def _check_baseline_feature(self, feature_name: str) -> bool:
        """Check if feature exists in baseline ruleset."""
        if self.baseline_ruleset_name not in self.rulesets:
            return False

        baseline = self.rulesets[self.baseline_ruleset_name]
        return baseline.has_feature(feature_name)

    def _passes_percentage_check(
        self,
        client_id: str,
        feature_name: str,
        percentage: int,
        user_context: Dict[str, Any]
    ) -> bool:
        """
        Check if user passes percentage rollout using consistent hashing.
        """
        user_id = user_context.get("user_id")
        if not user_id:
            return False

        # Create deterministic hash for client + user + feature
        hash_input = f"{client_id}:{user_id}:{feature_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        user_percentage = (hash_value % 100) + 1

        return user_percentage <= percentage

    def activate_kill_switch(self) -> None:
        """
        Activate global kill switch - all clients fall back to baseline.
        """
        self._use_baseline = True

    def deactivate_kill_switch(self) -> None:
        """
        Deactivate global kill switch - resume normal operation.
        """
        self._use_baseline = False

    def get_client_features(self, client_id: str) -> Set[str]:
        """
        Get all features available to a client.

        Args:
            client_id: Client identifier

        Returns:
            Set of feature names
        """
        if self._use_baseline:
            if self.baseline_ruleset_name in self.rulesets:
                return self.rulesets[self.baseline_ruleset_name].get_all_features()
            return set()

        ruleset_name = self.client_manager.get_client_ruleset(client_id)
        if ruleset_name and ruleset_name in self.rulesets:
            return self.rulesets[ruleset_name].get_all_features()

        # Fall back to baseline
        if self.baseline_ruleset_name in self.rulesets:
            return self.rulesets[self.baseline_ruleset_name].get_all_features()
        return set()

    def get_all_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered clients."""
        return self.client_manager.get_all_clients()

    def get_all_rulesets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all rulesets with their configurations.

        Returns:
            Dictionary mapping ruleset names to their info
        """
        return {
            name: {
                "description": ruleset.description,
                "features": list(ruleset.get_all_features()),
                "baseline_ruleset": ruleset.baseline_ruleset
            }
            for name, ruleset in self.rulesets.items()
        }
