"""
Feature Flag Client

Provides API for checking feature access for clients based on their assigned ruleset.
"""

import json
import os
import yaml
from typing import Dict, Any, Optional, Set

from ruleset_engine import RulesetEngine


class FeatureFlagClient:
    """
    Main client for feature flag evaluation based on client-ruleset assignments.
    """

    def __init__(
        self,
        config_path: str = "rulesets.yaml",
        clients_path: str = "clients.yaml",
        bootstrap_path: str = "bootstrap_defaults.json",
        baseline_ruleset: str = "baseline"
    ):
        """
        Initialize the Feature Flag Client.

        Args:
            config_path: Path to rulesets configuration
            clients_path: Path to clients configuration
            bootstrap_path: Path to bootstrap defaults
            baseline_ruleset: Name of the baseline ruleset
        """
        self.config_path = config_path
        self.clients_path = clients_path
        self.bootstrap_path = bootstrap_path

        # Initialize engine
        self.engine = RulesetEngine(baseline_ruleset_name=baseline_ruleset)

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
