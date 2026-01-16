"""
Feature Flag Client

Provides the main API for checking feature flags with caching, dynamic polling,
and Supabase integration support.
"""

import json
import os
import time
import yaml
import threading
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from ruleset_engine import RulesetEngine


class FeatureFlagClient:
    """
    Main client for feature flag evaluation with multi-level caching and polling.
    """

    def __init__(
        self,
        ruleset_name: str = "production",
        config_path: str = "rulesets.yaml",
        bootstrap_path: str = "bootstrap_defaults.json",
        cache_file_path: Optional[str] = ".feature_flags_cache.json",
        polling_interval: int = 60,
        enable_polling: bool = False,
        supabase_client: Optional[Any] = None
    ):
        """
        Initialize the Feature Flag Client.

        Args:
            ruleset_name: Name of the ruleset to use
            config_path: Path to the rulesets YAML configuration file
            bootstrap_path: Path to bootstrap defaults JSON file
            cache_file_path: Path to local file cache (None to disable)
            polling_interval: Seconds between polls for remote updates
            enable_polling: Whether to enable dynamic polling
            supabase_client: Optional Supabase client for remote flag management
        """
        self.ruleset_name = ruleset_name
        self.config_path = config_path
        self.bootstrap_path = bootstrap_path
        self.cache_file_path = cache_file_path
        self.polling_interval = polling_interval
        self.enable_polling = enable_polling
        self.supabase_client = supabase_client

        # Initialize ruleset engine
        self.engine = RulesetEngine()

        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        # Polling thread
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()

        # Load initial configuration
        self._load_configuration()

        # Start polling if enabled
        if self.enable_polling:
            self.start_polling()

    def _load_configuration(self) -> None:
        """
        Load configuration from various sources in priority order:
        1. Supabase (if configured)
        2. Local YAML file
        3. Local file cache
        4. Bootstrap defaults
        """
        config_loaded = False

        # Try loading from Supabase first
        if self.supabase_client:
            try:
                config = self._load_from_supabase()
                if config:
                    self.engine.load_multiple_rulesets(config)
                    self.engine.set_active_ruleset(self.ruleset_name)
                    self._save_to_cache(config)
                    config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load from Supabase: {e}")

        # Try loading from local YAML file
        if not config_loaded and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self.engine.load_multiple_rulesets(config)
                    self.engine.set_active_ruleset(self.ruleset_name)
                    self._save_to_cache(config)
                    config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load from YAML: {e}")

        # Try loading from file cache
        if not config_loaded and self.cache_file_path and os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, 'r') as f:
                    config = json.load(f)
                    self.engine.load_multiple_rulesets(config)
                    self.engine.set_active_ruleset(self.ruleset_name)
                    config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load from cache: {e}")

        # Fall back to bootstrap defaults
        if not config_loaded and os.path.exists(self.bootstrap_path):
            try:
                with open(self.bootstrap_path, 'r') as f:
                    config = json.load(f)
                    self.engine.load_multiple_rulesets(config)
                    self.engine.set_active_ruleset(self.ruleset_name)
                    config_loaded = True
            except Exception as e:
                print(f"Warning: Failed to load bootstrap defaults: {e}")

        if not config_loaded:
            raise RuntimeError("Failed to load feature flag configuration from any source")

    def _load_from_supabase(self) -> Optional[Dict[str, Any]]:
        """
        Load feature flag configuration from Supabase.

        Returns:
            Configuration dictionary or None if failed
        """
        if not self.supabase_client:
            return None

        try:
            # Query feature flags table
            response = self.supabase_client.table('feature_flags').select('*').execute()

            # Transform response into ruleset format
            # This is a placeholder - adjust based on your Supabase schema
            config = {}
            for row in response.data:
                ruleset_name = row.get('ruleset_name')
                if ruleset_name not in config:
                    config[ruleset_name] = {
                        'type': row.get('ruleset_type', 'percentage'),
                        'kill_switch_active': row.get('kill_switch_active', False),
                        'baseline': row.get('baseline', {}),
                        'features': {}
                    }

                feature_name = row.get('feature_name')
                config[ruleset_name]['features'][feature_name] = {
                    'enabled': row.get('enabled', True),
                    'percentage': row.get('percentage', 0),
                    'whitelist': row.get('whitelist', []),
                    'blacklist': row.get('blacklist', []),
                    'target_attributes': row.get('target_attributes', {}),
                    'groups': row.get('groups', []),
                    'treatment_groups': row.get('treatment_groups', [])
                }

            return config

        except Exception as e:
            print(f"Error loading from Supabase: {e}")
            return None

    def _save_to_cache(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to in-memory and file cache.

        Args:
            config: Configuration dictionary to cache
        """
        # Update in-memory cache
        with self._cache_lock:
            self._cache = config

        # Save to file cache if enabled
        if self.cache_file_path:
            try:
                with open(self.cache_file_path, 'w') as f:
                    json.dump(config, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to save to file cache: {e}")

    def _poll_updates(self) -> None:
        """
        Background polling loop to check for configuration updates.
        """
        while not self._stop_polling.is_set():
            try:
                # Try loading latest configuration
                if self.supabase_client:
                    config = self._load_from_supabase()
                    if config:
                        self.engine.load_multiple_rulesets(config)
                        self.engine.set_active_ruleset(self.ruleset_name)
                        self._save_to_cache(config)
                elif os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as f:
                        config = yaml.safe_load(f)
                        self.engine.load_multiple_rulesets(config)
                        self.engine.set_active_ruleset(self.ruleset_name)
                        self._save_to_cache(config)

            except Exception as e:
                print(f"Error during polling: {e}")

            # Wait for next poll interval or stop signal
            self._stop_polling.wait(self.polling_interval)

    def start_polling(self) -> None:
        """Start the background polling thread."""
        if self._polling_thread and self._polling_thread.is_alive():
            return

        self._stop_polling.clear()
        self._polling_thread = threading.Thread(target=self._poll_updates, daemon=True)
        self._polling_thread.start()

    def stop_polling(self) -> None:
        """Stop the background polling thread."""
        if self._polling_thread:
            self._stop_polling.set()
            self._polling_thread.join(timeout=5)

    def isEnabled(
        self,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature is enabled for the given user context.

        This is the main API method for feature flag evaluation.

        Args:
            feature_name: Name of the feature to check
            user_context: Dictionary containing user information:
                - user_id: User identifier (required for percentage/AB tests)
                - Any additional attributes for targeting

        Returns:
            True if feature is enabled, False otherwise

        Example:
            client = FeatureFlagClient()
            if client.isEnabled("feature1_recommendations", {"user_id": 123}):
                # Use new recommendation engine
                pass
        """
        try:
            return self.engine.evaluate_feature(feature_name, user_context)
        except Exception as e:
            print(f"Error evaluating feature '{feature_name}': {e}")
            # Safe default: return baseline or False
            baseline = self.engine.get_ruleset_baseline()
            return baseline.get(feature_name, False)

    def activate_kill_switch(self) -> None:
        """
        Activate the kill switch for the active ruleset.
        All features will revert to their baseline values.
        """
        self.engine.activate_kill_switch()

    def deactivate_kill_switch(self) -> None:
        """
        Deactivate the kill switch for the active ruleset.
        Features will resume normal evaluation.
        """
        self.engine.deactivate_kill_switch()

    def switch_ruleset(self, ruleset_name: str) -> None:
        """
        Switch to a different ruleset.

        Args:
            ruleset_name: Name of the ruleset to switch to

        Raises:
            ValueError: If ruleset doesn't exist
        """
        self.engine.set_active_ruleset(ruleset_name)
        self.ruleset_name = ruleset_name

    def get_baseline(self) -> Dict[str, bool]:
        """
        Get the baseline configuration for the active ruleset.

        Returns:
            Dictionary mapping feature names to their baseline values
        """
        return self.engine.get_ruleset_baseline()

    def reload_configuration(self) -> None:
        """
        Manually reload configuration from all sources.
        """
        self._load_configuration()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.stop_polling()


# Singleton instance for easy access
_default_client: Optional[FeatureFlagClient] = None


def get_client(**kwargs) -> FeatureFlagClient:
    """
    Get or create the default feature flag client singleton.

    Args:
        **kwargs: Arguments to pass to FeatureFlagClient constructor (only used on first call)

    Returns:
        The default FeatureFlagClient instance
    """
    global _default_client
    if _default_client is None:
        _default_client = FeatureFlagClient(**kwargs)
    return _default_client


def isEnabled(feature_name: str, user_context: Optional[Dict[str, Any]] = None) -> bool:
    """
    Convenience function to check if a feature is enabled using the default client.

    Args:
        feature_name: Name of the feature to check
        user_context: User context dictionary

    Returns:
        True if feature is enabled, False otherwise
    """
    client = get_client()
    return client.isEnabled(feature_name, user_context)
