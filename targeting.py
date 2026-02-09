"""
Targeting Rules Engine

Enables feature targeting based on user attributes, segments, and conditions.
Supports operators: equals, not_equals, contains, not_contains, in, not_in,
greater_than, less_than, regex, percentage, semver
"""

import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class Operators:
    """Available targeting operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    REGEX = "regex"
    PERCENTAGE = "percentage"
    SEMVER_GT = "semver_gt"
    SEMVER_GTE = "semver_gte"
    SEMVER_LT = "semver_lt"
    SEMVER_LTE = "semver_lte"
    SEMVER_EQ = "semver_eq"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    BEFORE = "before"  # Date comparison
    AFTER = "after"    # Date comparison


def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string to tuple."""
    try:
        parts = version.lstrip("v").split("-")[0].split(".")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0
        )
    except (ValueError, AttributeError):
        return (0, 0, 0)


def evaluate_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition against user context.

    Args:
        condition: Dict with 'attribute', 'operator', and 'value'/'values'
        context: User context dictionary

    Returns:
        True if condition matches
    """
    attribute = condition.get("attribute", "")
    operator = condition.get("operator", Operators.EQUALS)
    expected_value = condition.get("value")
    expected_values = condition.get("values", [])

    # Handle nested attributes with dot notation (e.g., "user.country")
    actual_value = context
    for key in attribute.split("."):
        if isinstance(actual_value, dict):
            actual_value = actual_value.get(key)
        else:
            actual_value = None
            break

    try:
        # Existence checks
        if operator == Operators.EXISTS:
            return actual_value is not None

        if operator == Operators.NOT_EXISTS:
            return actual_value is None

        # Can't evaluate if attribute doesn't exist (except for existence checks)
        if actual_value is None:
            return False

        # String operations
        if operator == Operators.EQUALS:
            return str(actual_value).lower() == str(expected_value).lower()

        if operator == Operators.NOT_EQUALS:
            return str(actual_value).lower() != str(expected_value).lower()

        if operator == Operators.CONTAINS:
            return str(expected_value).lower() in str(actual_value).lower()

        if operator == Operators.NOT_CONTAINS:
            return str(expected_value).lower() not in str(actual_value).lower()

        if operator == Operators.STARTS_WITH:
            return str(actual_value).lower().startswith(str(expected_value).lower())

        if operator == Operators.ENDS_WITH:
            return str(actual_value).lower().endswith(str(expected_value).lower())

        # List operations
        if operator == Operators.IN:
            values_lower = [str(v).lower() for v in expected_values]
            return str(actual_value).lower() in values_lower

        if operator == Operators.NOT_IN:
            values_lower = [str(v).lower() for v in expected_values]
            return str(actual_value).lower() not in values_lower

        # Numeric comparisons
        if operator == Operators.GREATER_THAN:
            return float(actual_value) > float(expected_value)

        if operator == Operators.GREATER_THAN_OR_EQUAL:
            return float(actual_value) >= float(expected_value)

        if operator == Operators.LESS_THAN:
            return float(actual_value) < float(expected_value)

        if operator == Operators.LESS_THAN_OR_EQUAL:
            return float(actual_value) <= float(expected_value)

        # Regex
        if operator == Operators.REGEX:
            pattern = re.compile(expected_value, re.IGNORECASE)
            return bool(pattern.search(str(actual_value)))

        # Percentage (consistent hashing)
        if operator == Operators.PERCENTAGE:
            # Use user_id or fallback to stringified context for hashing
            hash_key = context.get("user_id", str(actual_value))
            feature = context.get("_feature_name", "default")
            hash_input = f"{hash_key}:{feature}".encode()
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            user_bucket = (hash_value % 100) + 1
            return user_bucket <= int(expected_value)

        # Semantic version comparisons
        if operator.startswith("semver_"):
            actual_semver = parse_semver(str(actual_value))
            expected_semver = parse_semver(str(expected_value))

            if operator == Operators.SEMVER_GT:
                return actual_semver > expected_semver
            if operator == Operators.SEMVER_GTE:
                return actual_semver >= expected_semver
            if operator == Operators.SEMVER_LT:
                return actual_semver < expected_semver
            if operator == Operators.SEMVER_LTE:
                return actual_semver <= expected_semver
            if operator == Operators.SEMVER_EQ:
                return actual_semver == expected_semver

        # Date comparisons
        if operator in (Operators.BEFORE, Operators.AFTER):
            if isinstance(actual_value, str):
                actual_date = datetime.fromisoformat(actual_value.replace("Z", "+00:00"))
            elif isinstance(actual_value, datetime):
                actual_date = actual_value
            else:
                return False

            expected_date = datetime.fromisoformat(expected_value.replace("Z", "+00:00"))

            if operator == Operators.BEFORE:
                return actual_date < expected_date
            if operator == Operators.AFTER:
                return actual_date > expected_date

        logger.warning(f"Unknown operator: {operator}")
        return False

    except Exception as e:
        logger.debug(f"Error evaluating condition: {e}")
        return False


def evaluate_conditions(
    conditions: List[Dict[str, Any]],
    context: Dict[str, Any],
    logic: str = "AND"
) -> bool:
    """
    Evaluate multiple conditions with AND/OR logic.

    Args:
        conditions: List of condition dicts
        context: User context
        logic: "AND" or "OR"

    Returns:
        True if conditions match according to logic
    """
    if not conditions:
        return True

    results = [evaluate_condition(c, context) for c in conditions]

    if logic.upper() == "OR":
        return any(results)
    return all(results)  # AND is default


class TargetingRule:
    """Represents a single targeting rule."""

    def __init__(self, config: Dict[str, Any]):
        self.id = config.get("id")
        self.name = config.get("name", "")
        self.description = config.get("description", "")
        self.feature_name = config.get("feature_name", "")
        self.ruleset_name = config.get("ruleset_name")  # None = all rulesets
        self.priority = config.get("priority", 0)
        self.conditions = config.get("conditions", [])
        self.logic = config.get("logic", "AND")  # AND/OR for conditions
        self.action = config.get("action", "enable")  # enable, disable, variant
        self.variant_value = config.get("variant_value")
        self.is_active = config.get("is_active", True)

    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if this rule matches the given context."""
        if not self.is_active:
            return False

        # Add feature name to context for percentage hashing
        context_with_feature = {**context, "_feature_name": self.feature_name}
        return evaluate_conditions(self.conditions, context_with_feature, self.logic)

    def get_result(self) -> Tuple[str, Any]:
        """Get the action and value for this rule."""
        return self.action, self.variant_value


class TargetingEngine:
    """
    Engine for evaluating targeting rules.

    Rules are evaluated in priority order (highest first).
    First matching rule wins.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.rules: Dict[str, List[TargetingRule]] = {}  # feature_name -> rules
        self._cache_loaded = False
        self._segments: Dict[str, Dict[str, Any]] = {}

    def load_rules_from_config(self, rules_config: List[Dict[str, Any]]):
        """Load targeting rules from configuration."""
        self.rules = {}

        for rule_config in rules_config:
            rule = TargetingRule(rule_config)
            feature = rule.feature_name

            if feature not in self.rules:
                self.rules[feature] = []

            self.rules[feature].append(rule)

        # Sort each feature's rules by priority (descending)
        for feature in self.rules:
            self.rules[feature].sort(key=lambda r: r.priority, reverse=True)

    def load_rules_from_db(self):
        """Load targeting rules from Supabase."""
        if not self.supabase:
            return

        try:
            result = self.supabase.client.table("targeting_rules").select("*").eq(
                "is_active", True
            ).order("priority", desc=True).execute()

            if result.data:
                self.load_rules_from_config(result.data)
            self._cache_loaded = True
        except Exception as e:
            logger.error(f"Error loading targeting rules: {e}")

    def load_segments(self):
        """Load user segments from database."""
        if not self.supabase:
            return

        try:
            result = self.supabase.client.table("user_segments").select("*").eq(
                "is_active", True
            ).execute()

            self._segments = {s["name"]: s for s in (result.data or [])}
        except Exception as e:
            logger.error(f"Error loading segments: {e}")

    def check_segment_membership(self, segment_name: str, context: Dict[str, Any]) -> bool:
        """Check if user context matches a segment."""
        segment = self._segments.get(segment_name)
        if not segment:
            return False

        rules = segment.get("rules", [])
        return evaluate_conditions(rules, context)

    def evaluate(
        self,
        feature_name: str,
        context: Dict[str, Any],
        ruleset_name: Optional[str] = None
    ) -> Tuple[Optional[str], Any]:
        """
        Evaluate targeting rules for a feature.

        Args:
            feature_name: Feature to evaluate
            context: User context (user_id, country, device, custom attrs, etc.)
            ruleset_name: Current ruleset (for ruleset-specific rules)

        Returns:
            Tuple of (action, variant_value) or (None, None) if no rules match
        """
        if not self._cache_loaded:
            self.load_rules_from_db()

        rules = self.rules.get(feature_name, [])

        # Expand segment conditions in context
        expanded_context = {**context}
        if "segments" not in expanded_context:
            expanded_context["segments"] = []

        # Check all segments and add matching ones to context
        for segment_name in self._segments:
            if self.check_segment_membership(segment_name, context):
                expanded_context["segments"].append(segment_name)

        for rule in rules:
            # Check if rule applies to this ruleset
            if rule.ruleset_name and rule.ruleset_name != ruleset_name:
                continue

            if rule.matches(expanded_context):
                return rule.get_result()

        return None, None

    def add_rule(self, rule_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a new targeting rule."""
        if self.supabase:
            try:
                result = self.supabase.client.table("targeting_rules").insert(rule_config).execute()
                if result.data:
                    # Reload rules
                    self.load_rules_from_db()
                    return result.data[0]
            except Exception as e:
                logger.error(f"Error adding targeting rule: {e}")
        return None

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing targeting rule."""
        if self.supabase:
            try:
                self.supabase.client.table("targeting_rules").update(updates).eq(
                    "id", rule_id
                ).execute()
                self.load_rules_from_db()
                return True
            except Exception as e:
                logger.error(f"Error updating targeting rule: {e}")
        return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a targeting rule."""
        if self.supabase:
            try:
                self.supabase.client.table("targeting_rules").delete().eq(
                    "id", rule_id
                ).execute()
                self.load_rules_from_db()
                return True
            except Exception as e:
                logger.error(f"Error deleting targeting rule: {e}")
        return False

    def list_rules(self, feature_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List targeting rules."""
        if not self.supabase:
            return []

        try:
            query = self.supabase.client.table("targeting_rules").select("*")

            if feature_name:
                query = query.eq("feature_name", feature_name)

            result = query.order("priority", desc=True).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error listing targeting rules: {e}")
            return []


# Global targeting engine instance
_targeting_engine: Optional[TargetingEngine] = None


def get_targeting_engine(supabase_client=None) -> TargetingEngine:
    """Get or create the global targeting engine."""
    global _targeting_engine
    if _targeting_engine is None:
        _targeting_engine = TargetingEngine(supabase_client)
    return _targeting_engine
