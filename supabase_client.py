"""
Supabase client for feature flagging system.
Handles all database operations for function graphs, features, and analysis.
"""

import os
import logging
from typing import Dict, List, Optional, Set
from supabase import create_client, Client
import json

# Configure logging
logger = logging.getLogger(__name__)


class SupabaseClient:
    """Client for interacting with Supabase database"""

    def __init__(self):
        """Initialize Supabase client with environment variables"""
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")

        try:
            self.client: Client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    # Project Management
    def create_project(self, name: str, description: str = "", repository_url: str = "", metadata: dict = None) -> dict:
        """Create a new project"""
        try:
            data = {
                "name": name,
                "description": description,
                "repository_url": repository_url,
                "metadata": metadata or {}
            }
            result = self.client.table("projects").insert(data).execute()
            if result.data:
                logger.info(f"Project '{name}' created successfully")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise

    def get_project(self, project_id: str) -> Optional[dict]:
        """Get project by ID"""
        try:
            result = self.client.table("projects").select("*").eq("id", project_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            raise

    def list_projects(self) -> List[dict]:
        """List all projects"""
        try:
            result = self.client.table("projects").select("*").order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise

    # Function Graph Management
    def save_function_graph(self, project_id: str, file_path: str, graph_data: dict,
                           total_functions: int, total_calls: int, metadata: dict = None) -> dict:
        """Save a complete function graph analysis"""
        try:
            data = {
                "project_id": project_id,
                "file_path": file_path,
                "graph_data": graph_data,
                "total_functions": total_functions,
                "total_calls": total_calls,
                "metadata": metadata or {}
            }
            result = self.client.table("function_graphs").insert(data).execute()
            if result.data:
                logger.info(f"Function graph for {file_path} saved")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save function graph: {e}")
            raise

    def get_function_graph(self, project_id: str, file_path: str = None) -> Optional[dict]:
        """Get function graph for a project and optional file"""
        try:
            query = self.client.table("function_graphs").select("*").eq("project_id", project_id)
            if file_path:
                query = query.eq("file_path", file_path)
            query = query.order("analysis_timestamp", desc=True).limit(1)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get function graph: {e}")
            raise

    # Function Management
    def save_function(self, project_id: str, function_name: str, file_path: str,
                     is_feature_flagged: bool = False, is_helper: bool = False,
                     is_shared_helper: bool = False, line_number: int = None,
                     complexity_score: int = 0, metadata: dict = None) -> dict:
        """Save or update a function"""
        try:
            data = {
                "project_id": project_id,
                "function_name": function_name,
                "file_path": file_path,
                "is_feature_flagged": is_feature_flagged,
                "is_helper": is_helper,
                "is_shared_helper": is_shared_helper,
                "line_number": line_number,
                "complexity_score": complexity_score,
                "metadata": metadata or {}
            }
            result = self.client.table("functions").upsert(data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save function {function_name}: {e}")
            raise

    def get_function(self, project_id: str, function_name: str) -> Optional[dict]:
        """Get function by name"""
        try:
            result = self.client.table("functions").select("*").eq("project_id", project_id).eq("function_name", function_name).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get function {function_name}: {e}")
            raise

    def list_functions(self, project_id: str, is_feature_flagged: bool = None,
                      is_helper: bool = None, is_shared_helper: bool = None) -> List[dict]:
        """List functions with optional filters"""
        try:
            query = self.client.table("functions").select("*").eq("project_id", project_id)
            if is_feature_flagged is not None:
                query = query.eq("is_feature_flagged", is_feature_flagged)
            if is_helper is not None:
                query = query.eq("is_helper", is_helper)
            if is_shared_helper is not None:
                query = query.eq("is_shared_helper", is_shared_helper)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list functions: {e}")
            raise

    # Feature Management
    def create_feature(self, project_id: str, feature_name: str, description: str = "",
                      is_enabled: bool = False, metadata: dict = None) -> dict:
        """Create a new feature"""
        try:
            data = {
                "project_id": project_id,
                "feature_name": feature_name,
                "description": description,
                "is_enabled": is_enabled,
                "metadata": metadata or {}
            }
            result = self.client.table("features").upsert(data).execute()
            if result.data:
                logger.info(f"Feature '{feature_name}' created")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create feature {feature_name}: {e}")
            raise

    def get_feature(self, project_id: str, feature_name: str) -> Optional[dict]:
        """Get feature by name"""
        try:
            result = self.client.table("features").select("*").eq("project_id", project_id).eq("feature_name", feature_name).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get feature {feature_name}: {e}")
            raise

    def list_features(self, project_id: str) -> List[dict]:
        """List all features for a project"""
        try:
            result = self.client.table("features").select("*").eq("project_id", project_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list features: {e}")
            raise

    def toggle_feature(self, feature_id: str, is_enabled: bool) -> dict:
        """Toggle feature on/off"""
        try:
            result = self.client.table("features").update({"is_enabled": is_enabled}).eq("id", feature_id).execute()
            if result.data:
                logger.info(f"Feature {feature_id} toggled to {is_enabled}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to toggle feature: {e}")
            raise

    # Function Mapping Management
    def create_function_mapping(self, feature_id: str, function_id: str,
                               is_entry_point: bool = False,
                               dependency_type: str = "direct") -> dict:
        """Map a function to a feature"""
        try:
            data = {
                "feature_id": feature_id,
                "function_id": function_id,
                "is_entry_point": is_entry_point,
                "dependency_type": dependency_type
            }
            result = self.client.table("function_mappings").upsert(data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create function mapping: {e}")
            raise

    def get_feature_functions(self, feature_id: str) -> List[dict]:
        """Get all functions mapped to a feature"""
        try:
            result = self.client.table("function_mappings").select(
                "*, functions(*)"
            ).eq("feature_id", feature_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get feature functions: {e}")
            raise

    def get_function_features(self, function_id: str) -> List[dict]:
        """Get all features that use a function"""
        try:
            result = self.client.table("function_mappings").select(
                "*, features(*)"
            ).eq("function_id", function_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get function features: {e}")
            raise

    # Dependency Management
    def save_dependency(self, project_id: str, caller_function_id: str,
                       callee_function_id: str, call_count: int = 1) -> dict:
        """Save a function dependency (call relationship)"""
        try:
            data = {
                "project_id": project_id,
                "caller_function_id": caller_function_id,
                "callee_function_id": callee_function_id,
                "call_count": call_count
            }
            result = self.client.table("dependencies").upsert(data).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save dependency: {e}")
            raise

    def get_function_dependencies(self, function_id: str, direction: str = "downstream") -> List[dict]:
        """Get function dependencies (upstream callers or downstream callees)"""
        try:
            if direction == "upstream":
                result = self.client.table("dependencies").select(
                    "*, caller:functions!caller_function_id(*)"
                ).eq("callee_function_id", function_id).execute()
            else:
                result = self.client.table("dependencies").select(
                    "*, callee:functions!callee_function_id(*)"
                ).eq("caller_function_id", function_id).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get function dependencies: {e}")
            raise

    # Impact Analysis
    def save_impact_analysis(self, feature_id: str, analysis_data: dict,
                            total_affected: int, unreachable: int, need_fallback: int) -> dict:
        """Save impact analysis results"""
        try:
            data = {
                "feature_id": feature_id,
                "analysis_data": analysis_data,
                "total_affected_functions": total_affected,
                "functions_unreachable": unreachable,
                "functions_need_fallback": need_fallback
            }
            result = self.client.table("impact_analysis").insert(data).execute()
            if result.data:
                logger.info(f"Impact analysis saved for feature {feature_id}")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save impact analysis: {e}")
            raise

    def get_impact_analysis(self, feature_id: str) -> Optional[dict]:
        """Get latest impact analysis for a feature"""
        try:
            result = self.client.table("impact_analysis").select("*").eq(
                "feature_id", feature_id
            ).order("analyzed_at", desc=True).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get impact analysis: {e}")
            raise

    # Client Management
    def save_client(self, client_id: str, ruleset_name: str,
                   project_id: str = None, metadata: dict = None) -> dict:
        """Save or update a client"""
        try:
            data = {
                "client_id": client_id,
                "ruleset_name": ruleset_name,
                "project_id": project_id,
                "metadata": metadata or {}
            }
            result = self.client.table("clients").upsert(data).execute()
            if result.data:
                logger.info(f"Client '{client_id}' saved")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save client: {e}")
            raise

    def get_client(self, client_id: str) -> Optional[dict]:
        """Get client by ID"""
        try:
            result = self.client.table("clients").select("*").eq("client_id", client_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get client: {e}")
            raise

    def list_clients(self, project_id: str = None) -> List[dict]:
        """List all clients, optionally filtered by project"""
        try:
            query = self.client.table("clients").select("*")
            if project_id:
                query = query.eq("project_id", project_id)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list clients: {e}")
            raise

    # Ruleset Management
    def save_ruleset(self, project_id: str, ruleset_name: str, description: str,
                    rules: dict, is_active: bool = True) -> dict:
        """Save or update a ruleset"""
        try:
            data = {
                "project_id": project_id,
                "ruleset_name": ruleset_name,
                "description": description,
                "rules": rules,
                "is_active": is_active
            }
            result = self.client.table("rulesets").upsert(data).execute()
            if result.data:
                logger.info(f"Ruleset '{ruleset_name}' saved")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to save ruleset: {e}")
            raise

    def get_ruleset(self, project_id: str, ruleset_name: str) -> Optional[dict]:
        """Get ruleset by name"""
        try:
            result = self.client.table("rulesets").select("*").eq(
                "project_id", project_id
            ).eq("ruleset_name", ruleset_name).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get ruleset: {e}")
            raise

    def list_rulesets(self, project_id: str, is_active: bool = None) -> List[dict]:
        """List all rulesets for a project"""
        try:
            query = self.client.table("rulesets").select("*").eq("project_id", project_id)
            if is_active is not None:
                query = query.eq("is_active", is_active)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list rulesets: {e}")
            raise

    # New Standalone Ruleset Management (not project-specific)
    def create_ruleset(self, name: str, description: str = "", features: list = None,
                      baseline_ruleset: str = None, rollout_percentage: int = 100,
                      metadata: dict = None) -> dict:
        """Create a new standalone ruleset"""
        try:
            data = {
                "name": name,
                "description": description,
                "features": features or [],
                "baseline_ruleset": baseline_ruleset,
                "rollout_percentage": rollout_percentage,
                "metadata": metadata or {}
            }
            result = self.client.table("rulesets").insert(data).execute()
            if result.data:
                logger.info(f"Ruleset '{name}' created")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create ruleset: {e}")
            raise

    def get_ruleset_by_id(self, ruleset_id: str) -> Optional[dict]:
        """Get ruleset by ID"""
        try:
            result = self.client.table("rulesets").select("*").eq("id", ruleset_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get ruleset by ID: {e}")
            raise

    def list_all_rulesets(self) -> List[dict]:
        """List all rulesets"""
        try:
            result = self.client.table("rulesets").select("*").order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to list all rulesets: {e}")
            raise

    def update_ruleset(self, ruleset_id: str, updates: dict) -> Optional[dict]:
        """Update an existing ruleset"""
        try:
            result = self.client.table("rulesets").update(updates).eq("id", ruleset_id).execute()
            if result.data:
                logger.info(f"Ruleset {ruleset_id} updated")
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to update ruleset: {e}")
            raise

    def delete_ruleset(self, ruleset_id: str) -> bool:
        """Delete a ruleset"""
        try:
            self.client.table("rulesets").delete().eq("id", ruleset_id).execute()
            logger.info(f"Ruleset {ruleset_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete ruleset: {e}")
            return False
