"""
nixo Ruleset Service

Provides ruleset resolution with inheritance chain support, client overrides,
and feature flag evaluation for the nixo feature management system.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timezone
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class NixoRulesetService:
    """
    Service for managing rulesets and resolving features with inheritance.

    Resolution Priority (highest to lowest):
    1. Client-specific override (if not expired)
    2. Client's assigned ruleset
    3. Ruleset inheritance chain
    4. Default: feature disabled
    """

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._ruleset_cache: Dict[str, Dict] = {}
        self._feature_cache: Dict[str, Dict] = {}
        self._cache_ttl = 60  # seconds

    # =========================================================================
    # Feature Registry Operations
    # =========================================================================

    def get_all_features(self) -> List[Dict]:
        """Get all features from the registry."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("feature_registry") \
                .select("*") \
                .order("category", desc=False) \
                .order("name", desc=False) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get features: {e}")
            return []

    def get_features_by_category(self) -> Dict[str, List[Dict]]:
        """Get features grouped by category."""
        features = self.get_all_features()
        by_category = {}

        for feature in features:
            category = feature.get("category", "Other")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(feature)

        return by_category

    def get_feature(self, feature_name: str) -> Optional[Dict]:
        """Get a single feature by name."""
        if not self.supabase:
            return None

        try:
            result = self.supabase.client.table("feature_registry") \
                .select("*") \
                .eq("name", feature_name) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get feature {feature_name}: {e}")
            return None

    # =========================================================================
    # Ruleset Operations
    # =========================================================================

    def get_all_rulesets(self) -> List[Dict]:
        """Get all rulesets with summary info."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("ruleset_summary") \
                .select("*") \
                .execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Could not get ruleset_summary view, falling back: {e}")
            # Fallback to direct query
            try:
                result = self.supabase.client.table("rulesets") \
                    .select("*") \
                    .execute()
                return result.data or []
            except Exception as e2:
                logger.error(f"Failed to get rulesets: {e2}")
                return []

    def get_ruleset(self, ruleset_id: str) -> Optional[Dict]:
        """Get a single ruleset by ID."""
        if not self.supabase:
            return None

        try:
            result = self.supabase.client.table("rulesets") \
                .select("*") \
                .eq("id", ruleset_id) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get ruleset {ruleset_id}: {e}")
            return None

    def get_ruleset_by_name(self, name: str) -> Optional[Dict]:
        """Get a ruleset by its name."""
        if not self.supabase:
            return None

        try:
            result = self.supabase.client.table("rulesets") \
                .select("*") \
                .eq("name", name) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get ruleset by name {name}: {e}")
            return None

    def create_ruleset(
        self,
        name: str,
        display_name: str,
        description: str = "",
        color: str = "#6366f1",
        icon: str = "package",
        inherits_from: Optional[str] = None,
        is_template: bool = False,
        created_by: str = "system"
    ) -> Optional[Dict]:
        """Create a new ruleset."""
        if not self.supabase:
            return None

        try:
            data = {
                "name": name,
                "display_name": display_name,
                "description": description,
                "color": color,
                "icon": icon,
                "inherits_from": inherits_from,
                "is_template": is_template,
                "created_by": created_by
            }

            result = self.supabase.client.table("rulesets") \
                .insert(data) \
                .execute()

            if result.data:
                self._log_audit("create_ruleset", "ruleset", result.data[0]["id"], {
                    "after": data
                }, created_by)

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to create ruleset: {e}")
            return None

    def update_ruleset(
        self,
        ruleset_id: str,
        updates: Dict[str, Any],
        updated_by: str = "system"
    ) -> bool:
        """Update an existing ruleset."""
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current = self.get_ruleset(ruleset_id)

            # Don't update timestamps - they're handled by trigger
            safe_updates = {k: v for k, v in updates.items()
                          if k not in ["id", "created_at"]}

            result = self.supabase.client.table("rulesets") \
                .update(safe_updates) \
                .eq("id", ruleset_id) \
                .execute()

            if result.data:
                self._log_audit("update_ruleset", "ruleset", ruleset_id, {
                    "before": current,
                    "after": updates
                }, updated_by)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update ruleset: {e}")
            return False

    def delete_ruleset(self, ruleset_id: str, deleted_by: str = "system") -> bool:
        """Delete a ruleset."""
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current = self.get_ruleset(ruleset_id)

            result = self.supabase.client.table("rulesets") \
                .delete() \
                .eq("id", ruleset_id) \
                .execute()

            self._log_audit("delete_ruleset", "ruleset", ruleset_id, {
                "before": current
            }, deleted_by)

            return True
        except Exception as e:
            logger.error(f"Failed to delete ruleset: {e}")
            return False

    def clone_ruleset(
        self,
        source_id: str,
        new_name: str,
        new_display_name: str,
        created_by: str = "system"
    ) -> Optional[Dict]:
        """Clone a ruleset with all its features."""
        if not self.supabase:
            return None

        try:
            # Get source ruleset
            source = self.get_ruleset(source_id)
            if not source:
                return None

            # Create new ruleset
            new_ruleset = self.create_ruleset(
                name=new_name,
                display_name=new_display_name,
                description=f"Cloned from {source['display_name']}",
                color=source.get("color", "#6366f1"),
                icon=source.get("icon", "package"),
                inherits_from=source.get("inherits_from"),
                is_template=False,
                created_by=created_by
            )

            if not new_ruleset:
                return None

            # Copy features
            features = self.get_ruleset_direct_features(source_id)
            for feature in features:
                self.set_ruleset_feature(
                    new_ruleset["id"],
                    feature["feature_name"],
                    feature["enabled"],
                    feature.get("config", {})
                )

            return new_ruleset
        except Exception as e:
            logger.error(f"Failed to clone ruleset: {e}")
            return None

    def get_template_rulesets(self) -> List[Dict]:
        """Get all template rulesets."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("rulesets") \
                .select("*") \
                .eq("is_template", True) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get templates: {e}")
            return []

    # =========================================================================
    # Ruleset Features Operations
    # =========================================================================

    def get_ruleset_direct_features(self, ruleset_id: str) -> List[Dict]:
        """Get features directly assigned to a ruleset (no inheritance)."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("ruleset_features") \
                .select("*, feature_registry(*)") \
                .eq("ruleset_id", ruleset_id) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get ruleset features: {e}")
            return []

    def get_ruleset_resolved_features(self, ruleset_id: str) -> List[Dict]:
        """
        Get all features for a ruleset including inherited ones.
        Uses the database function for proper resolution.
        """
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.rpc(
                "get_ruleset_features",
                {"p_ruleset_id": ruleset_id}
            ).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"RPC failed, using fallback: {e}")
            # Fallback to Python-based resolution
            return self._resolve_features_python(ruleset_id)

    def _resolve_features_python(self, ruleset_id: str) -> List[Dict]:
        """
        Python fallback for feature resolution with inheritance.
        """
        resolved = {}
        chain = self._get_inheritance_chain(ruleset_id)

        # Process from oldest ancestor to current (reverse order)
        for depth, rs_id, rs_name in reversed(chain):
            features = self.get_ruleset_direct_features(rs_id)
            for f in features:
                feature_name = f["feature_name"]
                resolved[feature_name] = {
                    "feature_name": feature_name,
                    "enabled": f["enabled"],
                    "source_ruleset_id": rs_id,
                    "source_ruleset_name": rs_name,
                    "is_inherited": depth > 0
                }

        return list(resolved.values())

    def _get_inheritance_chain(self, ruleset_id: str) -> List[Tuple[int, str, str]]:
        """
        Get the inheritance chain for a ruleset.
        Returns list of (depth, ruleset_id, ruleset_name) tuples.
        """
        chain = []
        visited = set()
        current_id = ruleset_id
        depth = 0

        while current_id and current_id not in visited:
            visited.add(current_id)
            ruleset = self.get_ruleset(current_id)
            if ruleset:
                chain.append((depth, current_id, ruleset["name"]))
                current_id = ruleset.get("inherits_from")
                depth += 1
            else:
                break

        return chain

    def set_ruleset_feature(
        self,
        ruleset_id: str,
        feature_name: str,
        enabled: bool = True,
        config: Dict = None
    ) -> bool:
        """Set a feature for a ruleset."""
        if not self.supabase:
            return False

        try:
            data = {
                "ruleset_id": ruleset_id,
                "feature_name": feature_name,
                "enabled": enabled,
                "config": config or {}
            }

            result = self.supabase.client.table("ruleset_features") \
                .upsert(data) \
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to set ruleset feature: {e}")
            return False

    def remove_ruleset_feature(self, ruleset_id: str, feature_name: str) -> bool:
        """Remove a feature from a ruleset."""
        if not self.supabase:
            return False

        try:
            self.supabase.client.table("ruleset_features") \
                .delete() \
                .eq("ruleset_id", ruleset_id) \
                .eq("feature_name", feature_name) \
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to remove ruleset feature: {e}")
            return False

    def bulk_update_ruleset_features(
        self,
        ruleset_id: str,
        features: List[Dict],
        updated_by: str = "system"
    ) -> bool:
        """
        Bulk update features for a ruleset.

        Args:
            ruleset_id: The ruleset ID
            features: List of {feature_name: str, enabled: bool, config: dict}
            updated_by: Who is making the change
        """
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current_features = self.get_ruleset_direct_features(ruleset_id)

            # Clear existing and insert new
            self.supabase.client.table("ruleset_features") \
                .delete() \
                .eq("ruleset_id", ruleset_id) \
                .execute()

            if features:
                data = [
                    {
                        "ruleset_id": ruleset_id,
                        "feature_name": f["feature_name"],
                        "enabled": f.get("enabled", True),
                        "config": f.get("config", {})
                    }
                    for f in features
                ]

                self.supabase.client.table("ruleset_features") \
                    .insert(data) \
                    .execute()

            self._log_audit("bulk_update_features", "ruleset", ruleset_id, {
                "before": [f["feature_name"] for f in current_features],
                "after": [f["feature_name"] for f in features]
            }, updated_by)

            return True
        except Exception as e:
            logger.error(f"Failed to bulk update features: {e}")
            return False

    # =========================================================================
    # Client Operations
    # =========================================================================

    def get_all_clients(self) -> List[Dict]:
        """Get all clients with their ruleset info."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("client_summary") \
                .select("*") \
                .execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"Could not get client_summary view, falling back: {e}")
            try:
                result = self.supabase.client.table("client_rulesets") \
                    .select("*, rulesets(*)") \
                    .execute()
                return result.data or []
            except Exception as e2:
                logger.error(f"Failed to get clients: {e2}")
                return []

    def get_client(self, client_id: str) -> Optional[Dict]:
        """Get a single client with ruleset info."""
        if not self.supabase:
            return None

        try:
            result = self.supabase.client.table("client_rulesets") \
                .select("*, rulesets(*)") \
                .eq("client_id", client_id) \
                .single() \
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get client {client_id}: {e}")
            return None

    def assign_client_ruleset(
        self,
        client_id: str,
        ruleset_id: str,
        assigned_by: str = "system",
        notes: str = ""
    ) -> bool:
        """Assign a ruleset to a client."""
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current = self.get_client(client_id)

            data = {
                "client_id": client_id,
                "ruleset_id": ruleset_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "assigned_by": assigned_by,
                "notes": notes
            }

            result = self.supabase.client.table("client_rulesets") \
                .upsert(data) \
                .execute()

            if result.data:
                self._log_audit("assign_ruleset", "client", client_id, {
                    "before": {"ruleset_id": current.get("ruleset_id") if current else None},
                    "after": {"ruleset_id": ruleset_id}
                }, assigned_by)

            return bool(result.data)
        except Exception as e:
            logger.error(f"Failed to assign ruleset: {e}")
            return False

    def get_client_resolved_features(self, client_id: str) -> List[Dict]:
        """
        Get all resolved features for a client including overrides.
        Uses the database function for proper resolution.
        """
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.rpc(
                "get_client_features",
                {"p_client_id": client_id}
            ).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"RPC failed, using fallback: {e}")
            return self._resolve_client_features_python(client_id)

    def _resolve_client_features_python(self, client_id: str) -> List[Dict]:
        """
        Python fallback for client feature resolution.
        """
        resolved = {}

        # Get client's ruleset
        client = self.get_client(client_id)
        if client and client.get("ruleset_id"):
            # Get ruleset features
            ruleset_features = self.get_ruleset_resolved_features(client["ruleset_id"])
            for f in ruleset_features:
                resolved[f["feature_name"]] = {
                    "feature_name": f["feature_name"],
                    "enabled": f["enabled"],
                    "source": "inherited" if f.get("is_inherited") else "ruleset",
                    "source_detail": f.get("source_ruleset_name"),
                    "expires_at": None
                }

        # Apply overrides (highest priority)
        overrides = self.get_client_overrides(client_id)
        now = datetime.now(timezone.utc)

        for override in overrides:
            expires_at = override.get("expires_at")
            if expires_at:
                # Check if expired
                try:
                    exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if exp_dt <= now:
                        continue  # Skip expired override
                except:
                    pass

            resolved[override["feature_name"]] = {
                "feature_name": override["feature_name"],
                "enabled": override["enabled"],
                "source": "override",
                "source_detail": override.get("reason", ""),
                "expires_at": expires_at
            }

        return list(resolved.values())

    def has_feature(self, client_id: str, feature_name: str) -> bool:
        """
        Check if a client has a specific feature enabled.
        This is the main entry point for feature flag checks.
        """
        features = self.get_client_resolved_features(client_id)

        for f in features:
            if f["feature_name"] == feature_name:
                return f["enabled"]

        return False  # Default: feature disabled

    # =========================================================================
    # Override Operations
    # =========================================================================

    def get_client_overrides(self, client_id: str) -> List[Dict]:
        """Get all overrides for a client."""
        if not self.supabase:
            return []

        try:
            result = self.supabase.client.table("client_overrides") \
                .select("*") \
                .eq("client_id", client_id) \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get overrides: {e}")
            return []

    def add_client_override(
        self,
        client_id: str,
        feature_name: str,
        enabled: bool,
        reason: str = "",
        expires_at: Optional[str] = None,
        created_by: str = "system"
    ) -> Optional[Dict]:
        """Add or update a client override."""
        if not self.supabase:
            return None

        try:
            data = {
                "client_id": client_id,
                "feature_name": feature_name,
                "enabled": enabled,
                "reason": reason,
                "expires_at": expires_at,
                "created_by": created_by
            }

            result = self.supabase.client.table("client_overrides") \
                .upsert(data, on_conflict="client_id,feature_name") \
                .execute()

            if result.data:
                self._log_audit("add_override", "override",
                              f"{client_id}:{feature_name}", {
                    "after": data
                }, created_by)

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to add override: {e}")
            return None

    def remove_client_override(
        self,
        client_id: str,
        feature_name: str,
        removed_by: str = "system"
    ) -> bool:
        """Remove a client override."""
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current = self.supabase.client.table("client_overrides") \
                .select("*") \
                .eq("client_id", client_id) \
                .eq("feature_name", feature_name) \
                .execute()

            self.supabase.client.table("client_overrides") \
                .delete() \
                .eq("client_id", client_id) \
                .eq("feature_name", feature_name) \
                .execute()

            if current.data:
                self._log_audit("remove_override", "override",
                              f"{client_id}:{feature_name}", {
                    "before": current.data[0]
                }, removed_by)

            return True
        except Exception as e:
            logger.error(f"Failed to remove override: {e}")
            return False

    def update_client_override(
        self,
        client_id: str,
        feature_name: str,
        updates: Dict[str, Any],
        updated_by: str = "system"
    ) -> bool:
        """Update an existing client override."""
        if not self.supabase:
            return False

        try:
            # Get current state for audit
            current = self.supabase.client.table("client_overrides") \
                .select("*") \
                .eq("client_id", client_id) \
                .eq("feature_name", feature_name) \
                .single() \
                .execute()

            safe_updates = {k: v for k, v in updates.items()
                          if k not in ["id", "client_id", "feature_name", "created_at"]}

            result = self.supabase.client.table("client_overrides") \
                .update(safe_updates) \
                .eq("client_id", client_id) \
                .eq("feature_name", feature_name) \
                .execute()

            if result.data:
                self._log_audit("update_override", "override",
                              f"{client_id}:{feature_name}", {
                    "before": current.data,
                    "after": safe_updates
                }, updated_by)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update override: {e}")
            return False

    # =========================================================================
    # Audit Logging
    # =========================================================================

    def _log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        changes: Dict,
        actor: str
    ):
        """Log an audit entry."""
        if not self.supabase:
            return

        try:
            self.supabase.client.table("feature_audit_log").insert({
                "action": action,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "changes": changes,
                "actor": actor
            }).execute()
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")

    def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query audit logs."""
        if not self.supabase:
            return []

        try:
            query = self.supabase.client.table("feature_audit_log") \
                .select("*") \
                .order("created_at", desc=True) \
                .limit(limit)

            if entity_type:
                query = query.eq("entity_type", entity_type)
            if entity_id:
                query = query.eq("entity_id", entity_id)

            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get audit logs: {e}")
            return []


# Module-level singleton
_service_instance: Optional[NixoRulesetService] = None


def get_nixo_service(supabase_client=None) -> NixoRulesetService:
    """Get or create the nixo service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = NixoRulesetService(supabase_client)
    elif supabase_client is not None:
        # Update supabase client if provided (in case it was initialized later)
        _service_instance.supabase = supabase_client
    return _service_instance
