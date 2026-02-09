"""
nixo Feature Sync Module

Auto-discovers features from the nixo-custops codebase and syncs them to the database.
Scans for AVAILABLE_FEATURES constant and feature flag enforcement locations.
"""

import ast
import os
import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# The 23 features from nixo-custops AVAILABLE_FEATURES (exact match)
NIXO_FEATURES = {
    # Account Management (4 features)
    "accounts": {"category": "Account Management", "description": "Accounts management page"},
    "customer_dashboard": {"category": "Account Management", "description": "Customer dashboard view"},
    "schemas": {"category": "Account Management", "description": "Schemas configuration page"},
    "account_analysis": {"category": "Account Management", "description": "Account analysis and insights"},

    # AI Studio (3 features)
    "intaker_agent": {"category": "AI Studio", "description": "AI Intaker Agent for automated support intake"},
    "tickets": {"category": "AI Studio", "description": "Tickets/Issues management"},
    "testbed": {"category": "AI Studio", "description": "AI Testbed for testing"},

    # Communications (3 features)
    "related_tickets": {"category": "Communications", "description": "Related tickets view"},
    "blasts": {"category": "Communications", "description": "Broadcast/Blasts messaging"},
    "digests": {"category": "Communications", "description": "Digests and summaries"},

    # Integrations (10 features)
    "slack_settings": {"category": "Integrations", "description": "Slack integration settings"},
    "hubspot_integration": {"category": "Integrations", "description": "HubSpot CRM integration and notifications"},
    "linear_integration": {"category": "Integrations", "description": "Linear issue tracking integration"},
    "fireflies": {"category": "Integrations", "description": "Fireflies meeting integration"},
    "fathom": {"category": "Integrations", "description": "Fathom meeting integration"},
    "circleback": {"category": "Integrations", "description": "Circleback meeting integration"},
    "github_repos": {"category": "Integrations", "description": "GitHub indexed repositories"},
    "intercom": {"category": "Integrations", "description": "Intercom integration"},
    "github_oauth": {"category": "Integrations", "description": "GitHub OAuth integration"},
    "github_app": {"category": "Integrations", "description": "GitHub App integration"},

    # Advanced (3 features)
    "custom_branding": {"category": "Advanced", "description": "Custom branding and white-labeling"},
    "advanced_analytics": {"category": "Advanced", "description": "Advanced analytics and reporting"},
    "api_access": {"category": "Advanced", "description": "API access for integrations"},
}

# Default tier assignments
TIER_FEATURES = {
    "starter": [
        "accounts", "customer_dashboard", "schemas", "tickets",
        "slack_settings", "onboarding"
    ],
    "professional": [
        # Includes all starter features plus:
        "account_analysis", "related_tickets", "blasts", "digests",
        "hubspot_integration", "linear_integration", "intercom",
        "github_repos", "release_notes", "meetings"
    ],
    "enterprise": [
        # Includes all professional features plus:
        "intaker_agent", "testbed", "fireflies", "fathom", "circleback",
        "github_oauth", "github_app", "custom_branding",
        "advanced_analytics", "api_access"
    ]
}


class FeatureFlagScanner:
    """Scans codebase for feature flag usage and enforcement locations."""

    def __init__(self, codebase_path: str = None):
        self.codebase_path = codebase_path or os.environ.get(
            "NIXO_CODEBASE_PATH",
            "/home/dhyan/nixo-custops"
        )
        self.feature_usages: Dict[str, List[Dict]] = {}
        self.enforced_features: Set[str] = set()

    def scan_file(self, file_path: str) -> Dict[str, List[Dict]]:
        """
        Scan a Python file for feature flag usage.

        Looks for patterns like:
        - feature_flag_service.has_feature(client_id, 'feature_name')
        - @require_feature('feature_name')
        - if has_feature('feature_name'):
        """
        usages = {}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return usages

        # Pattern 1: has_feature/isEnabled calls
        patterns = [
            r"has_feature\s*\([^,]+,\s*['\"](\w+)['\"]",
            r"isEnabled\s*\([^,]+,\s*['\"](\w+)['\"]",
            r"check_feature\s*\([^,]+,\s*['\"](\w+)['\"]",
            r"@require_feature\s*\(['\"](\w+)['\"]",
            r"feature_flag_service\.has_feature\s*\([^,]+,\s*['\"](\w+)['\"]",
        ]

        rel_path = os.path.relpath(file_path, self.codebase_path)

        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for feature_name in matches:
                    if feature_name not in usages:
                        usages[feature_name] = []
                    usages[feature_name].append({
                        "file": rel_path,
                        "line": line_num,
                        "context": line.strip()[:100]
                    })
                    self.enforced_features.add(feature_name)

        return usages

    def scan_directory(self, directory: str = None) -> Dict[str, List[Dict]]:
        """Scan entire directory for feature flag usage."""
        directory = directory or self.codebase_path

        if not os.path.exists(directory):
            logger.warning(f"Directory not found: {directory}")
            return {}

        for root, dirs, files in os.walk(directory):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', 'node_modules', 'venv', '.venv',
                'dist', 'build', '.pytest_cache', '.mypy_cache'
            }]

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    file_usages = self.scan_file(file_path)

                    for feature, locations in file_usages.items():
                        if feature not in self.feature_usages:
                            self.feature_usages[feature] = []
                        self.feature_usages[feature].extend(locations)

        return self.feature_usages

    def get_enforced_features(self) -> Set[str]:
        """Get set of features that are enforced in code."""
        return self.enforced_features


class NixoFeatureSync:
    """
    Syncs nixo features to the database.
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self.scanner = FeatureFlagScanner()
        self._last_sync: Optional[datetime] = None

    def get_all_features(self) -> List[Dict]:
        """
        Get all known nixo features with their metadata.

        Returns:
            List of feature dictionaries with name, description, category, etc.
        """
        features = []

        # Scan codebase for enforcement locations
        enforcement_locations = self.scanner.scan_directory()
        enforced_features = self.scanner.get_enforced_features()

        for name, metadata in NIXO_FEATURES.items():
            feature = {
                "name": name,
                "description": metadata["description"],
                "category": metadata["category"],
                "is_enforced": name in enforced_features,
                "enforcement_locations": enforcement_locations.get(name, []),
                "metadata": {
                    "default_tiers": self._get_feature_tiers(name)
                }
            }
            features.append(feature)

        return features

    def _get_feature_tiers(self, feature_name: str) -> List[str]:
        """Get which tiers include this feature by default."""
        tiers = []

        if feature_name in TIER_FEATURES["starter"]:
            tiers.append("starter")
        if feature_name in TIER_FEATURES["professional"]:
            tiers.append("professional")
        if feature_name in TIER_FEATURES["enterprise"]:
            tiers.append("enterprise")

        # If not explicitly listed, it's enterprise-only
        if not tiers and feature_name in NIXO_FEATURES:
            tiers.append("enterprise")

        return tiers

    def get_features_by_category(self) -> Dict[str, List[Dict]]:
        """
        Get features grouped by category.

        Returns:
            Dict mapping category names to list of features
        """
        features = self.get_all_features()
        by_category = {}

        for feature in features:
            category = feature["category"]
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(feature)

        return by_category

    def get_categories(self) -> List[Dict]:
        """
        Get list of all feature categories with counts.
        """
        by_category = self.get_features_by_category()

        return [
            {
                "name": category,
                "count": len(features),
                "enforced_count": sum(1 for f in features if f["is_enforced"])
            }
            for category, features in sorted(by_category.items())
        ]

    def sync_to_database(self) -> Dict:
        """
        Sync all features to the database.

        Returns:
            Dict with sync results
        """
        if not self.supabase:
            return {"success": False, "error": "Supabase client not configured"}

        features = self.get_all_features()
        synced = 0
        errors = []

        for feature in features:
            try:
                result = self.supabase.client.table("feature_registry").upsert({
                    "name": feature["name"],
                    "description": feature["description"],
                    "category": feature["category"],
                    "is_enforced": feature["is_enforced"],
                    "enforcement_locations": feature["enforcement_locations"],
                    "metadata": feature["metadata"],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).execute()

                if result.data:
                    synced += 1
            except Exception as e:
                errors.append(f"{feature['name']}: {str(e)}")
                logger.error(f"Failed to sync feature {feature['name']}: {e}")

        self._last_sync = datetime.now(timezone.utc)

        return {
            "success": len(errors) == 0,
            "synced": synced,
            "total": len(features),
            "errors": errors,
            "synced_at": self._last_sync.isoformat()
        }

    def get_last_sync(self) -> Optional[datetime]:
        """Get timestamp of last sync."""
        return self._last_sync


def get_default_ruleset_features(ruleset_name: str) -> List[str]:
    """
    Get the default features for a ruleset template.

    Args:
        ruleset_name: One of 'starter', 'professional', 'enterprise'

    Returns:
        List of feature names
    """
    if ruleset_name == "starter":
        return TIER_FEATURES["starter"]
    elif ruleset_name == "professional":
        return TIER_FEATURES["starter"] + TIER_FEATURES["professional"]
    elif ruleset_name == "enterprise":
        return (TIER_FEATURES["starter"] + TIER_FEATURES["professional"] +
                TIER_FEATURES["enterprise"])
    else:
        return []


# Module-level instance for convenience
_sync_instance: Optional[NixoFeatureSync] = None


def get_feature_sync(supabase_client=None) -> NixoFeatureSync:
    """Get or create the feature sync instance."""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = NixoFeatureSync(supabase_client)
    elif supabase_client is not None:
        # Update supabase client if provided (in case it was initialized later)
        _sync_instance.supabase = supabase_client
    return _sync_instance
