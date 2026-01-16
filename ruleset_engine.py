"""
Rule Set Engine for Feature Flagging System

Handles ruleset evaluation, percentage rollouts, A/B testing, and kill switch functionality.
"""

import hashlib
from typing import Dict, List, Any, Optional
from enum import Enum


class RulesetType(Enum):
    """Types of rulesets available"""
    PERCENTAGE = "percentage"
    USER_TARGETING = "user_targeting"
    AB_TEST = "ab_test"
    KILL_SWITCH = "kill_switch"


class Ruleset:
    """
    Represents a feature flag ruleset with evaluation logic.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize a ruleset.

        Args:
            name: Unique identifier for the ruleset
            config: Configuration dictionary containing ruleset parameters
        """
        self.name = name
        self.config = config
        self.ruleset_type = RulesetType(config.get("type", "percentage"))
        self.baseline = config.get("baseline", {})
        self.kill_switch_active = config.get("kill_switch_active", False)

    def evaluate(self, feature_name: str, user_context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Evaluate if a feature should be enabled based on the ruleset.

        Args:
            feature_name: Name of the feature to evaluate
            user_context: Dictionary containing user information (user_id, attributes, etc.)

        Returns:
            True if feature should be enabled, False otherwise
        """
        # Check kill switch first
        if self.kill_switch_active:
            return self._get_baseline_value(feature_name)

        # Get feature configuration from ruleset
        features = self.config.get("features", {})
        feature_config = features.get(feature_name)

        if not feature_config:
            return self._get_baseline_value(feature_name)

        # If feature is explicitly disabled
        if not feature_config.get("enabled", True):
            return False

        # Evaluate based on ruleset type
        if self.ruleset_type == RulesetType.PERCENTAGE:
            return self._evaluate_percentage(feature_name, feature_config, user_context)
        elif self.ruleset_type == RulesetType.USER_TARGETING:
            return self._evaluate_user_targeting(feature_config, user_context)
        elif self.ruleset_type == RulesetType.AB_TEST:
            return self._evaluate_ab_test(feature_config, user_context)

        return self._get_baseline_value(feature_name)

    def _get_baseline_value(self, feature_name: str) -> bool:
        """Get the baseline value for a feature (used during kill switch or fallback)"""
        return self.baseline.get(feature_name, False)

    def _evaluate_percentage(
        self,
        feature_name: str,
        feature_config: Dict[str, Any],
        user_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Evaluate percentage-based rollout.
        Uses consistent hashing to ensure same user always gets same result.
        """
        percentage = feature_config.get("percentage", 0)

        if percentage <= 0:
            return False
        if percentage >= 100:
            return True

        # Need user_id for consistent hashing
        if not user_context or "user_id" not in user_context:
            # If no user context, use random-like behavior based on feature name
            return False

        user_id = str(user_context["user_id"])

        # Create deterministic hash for user + feature combination
        hash_input = f"{user_id}:{feature_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        user_percentage = (hash_value % 100) + 1

        return user_percentage <= percentage

    def _evaluate_user_targeting(
        self,
        feature_config: Dict[str, Any],
        user_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Evaluate user-targeting rules (whitelist, blacklist, attributes).
        """
        if not user_context:
            return False

        user_id = user_context.get("user_id")

        # Check whitelist
        whitelist = feature_config.get("whitelist", [])
        if whitelist and user_id in whitelist:
            return True

        # Check blacklist
        blacklist = feature_config.get("blacklist", [])
        if blacklist and user_id in blacklist:
            return False

        # Check attribute targeting
        target_attributes = feature_config.get("target_attributes", {})
        if target_attributes:
            return self._check_attributes(target_attributes, user_context)

        # Default to percentage rollout if available
        if "percentage" in feature_config:
            return self._evaluate_percentage(
                feature_config.get("name", "unknown"),
                feature_config,
                user_context
            )

        return False

    def _evaluate_ab_test(
        self,
        feature_config: Dict[str, Any],
        user_context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Evaluate A/B test assignment.
        Assigns users to groups consistently and checks if assigned to treatment group.
        """
        if not user_context or "user_id" not in user_context:
            return False

        user_id = str(user_context["user_id"])
        groups = feature_config.get("groups", ["control", "treatment"])
        treatment_groups = feature_config.get("treatment_groups", ["treatment"])

        # Assign user to group consistently
        hash_input = f"{user_id}:{self.name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        assigned_group = groups[hash_value % len(groups)]

        return assigned_group in treatment_groups

    def _check_attributes(
        self,
        target_attributes: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> bool:
        """
        Check if user attributes match targeting criteria.
        """
        for key, value in target_attributes.items():
            user_value = user_context.get(key)

            # Handle list matching (user value must be in list)
            if isinstance(value, list):
                if user_value not in value:
                    return False
            # Handle exact matching
            elif user_value != value:
                return False

        return True


class RulesetEngine:
    """
    Manages multiple rulesets and evaluates features across them.
    """

    def __init__(self):
        """Initialize the ruleset engine"""
        self.rulesets: Dict[str, Ruleset] = {}
        self.active_ruleset_name: Optional[str] = None

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

    def set_active_ruleset(self, name: str) -> None:
        """
        Set the active ruleset to use for evaluation.

        Args:
            name: Name of the ruleset to activate

        Raises:
            ValueError: If ruleset with given name doesn't exist
        """
        if name not in self.rulesets:
            raise ValueError(f"Ruleset '{name}' not found")
        self.active_ruleset_name = name

    def evaluate_feature(
        self,
        feature_name: str,
        user_context: Optional[Dict[str, Any]] = None,
        ruleset_name: Optional[str] = None
    ) -> bool:
        """
        Evaluate if a feature should be enabled.

        Args:
            feature_name: Name of the feature to evaluate
            user_context: User context for evaluation
            ruleset_name: Optional specific ruleset to use (defaults to active ruleset)

        Returns:
            True if feature should be enabled, False otherwise
        """
        ruleset_to_use = ruleset_name or self.active_ruleset_name

        if not ruleset_to_use or ruleset_to_use not in self.rulesets:
            # No ruleset available, return False as safe default
            return False

        ruleset = self.rulesets[ruleset_to_use]
        return ruleset.evaluate(feature_name, user_context)

    def activate_kill_switch(self, ruleset_name: Optional[str] = None) -> None:
        """
        Activate kill switch for a ruleset (reverts all features to baseline).

        Args:
            ruleset_name: Name of ruleset to activate kill switch for (defaults to active)
        """
        ruleset_to_update = ruleset_name or self.active_ruleset_name

        if ruleset_to_update and ruleset_to_update in self.rulesets:
            self.rulesets[ruleset_to_update].kill_switch_active = True

    def deactivate_kill_switch(self, ruleset_name: Optional[str] = None) -> None:
        """
        Deactivate kill switch for a ruleset.

        Args:
            ruleset_name: Name of ruleset to deactivate kill switch for (defaults to active)
        """
        ruleset_to_update = ruleset_name or self.active_ruleset_name

        if ruleset_to_update and ruleset_to_update in self.rulesets:
            self.rulesets[ruleset_to_update].kill_switch_active = False

    def get_ruleset_baseline(self, ruleset_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Get the baseline configuration for a ruleset.

        Args:
            ruleset_name: Name of ruleset (defaults to active)

        Returns:
            Dictionary mapping feature names to their baseline values
        """
        ruleset_to_check = ruleset_name or self.active_ruleset_name

        if ruleset_to_check and ruleset_to_check in self.rulesets:
            return self.rulesets[ruleset_to_check].baseline

        return {}
