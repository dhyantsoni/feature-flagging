"""
nixo API Routes

Flask blueprint providing API endpoints for the nixo feature management system.
Includes endpoints for features, rulesets, clients, and overrides.
"""

import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

# Create blueprint
nixo_bp = Blueprint('nixo', __name__, url_prefix='/api/nixo')

# Service instances (initialized when blueprint is registered)
_feature_sync = None
_ruleset_service = None


def init_nixo_services(supabase_client):
    """Initialize nixo services with Supabase client."""
    global _feature_sync, _ruleset_service

    from nixo_sync import get_feature_sync
    from nixo_service import get_nixo_service

    _feature_sync = get_feature_sync(supabase_client)
    _ruleset_service = get_nixo_service(supabase_client)


# =============================================================================
# Feature Discovery Endpoints
# =============================================================================

@nixo_bp.route('/features', methods=['GET'])
def get_features():
    """
    Get all features from the registry.

    Query params:
        - category: Filter by category name
        - enforced: Filter by enforcement status (true/false)
    """
    try:
        if _ruleset_service:
            features = _ruleset_service.get_all_features()
        elif _feature_sync:
            features = _feature_sync.get_all_features()
        else:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        # Apply filters
        category = request.args.get('category')
        enforced = request.args.get('enforced')

        if category:
            features = [f for f in features if f.get('category') == category]
        if enforced is not None:
            is_enforced = enforced.lower() == 'true'
            features = [f for f in features if f.get('is_enforced') == is_enforced]

        return jsonify({
            "success": True,
            "features": features,
            "total": len(features)
        })
    except Exception as e:
        logger.error(f"Error getting features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/features/sync', methods=['POST'])
def sync_features():
    """
    Re-scan codebase for features and sync to database.
    """
    try:
        if not _feature_sync:
            return jsonify({"success": False, "error": "Feature sync not initialized"}), 503

        result = _feature_sync.sync_to_database()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/features/categories', methods=['GET'])
def get_categories():
    """Get all feature categories with counts."""
    try:
        if _feature_sync:
            categories = _feature_sync.get_categories()
        elif _ruleset_service:
            by_category = _ruleset_service.get_features_by_category()
            categories = [
                {
                    "name": cat,
                    "count": len(features),
                    "enforced_count": sum(1 for f in features if f.get("is_enforced"))
                }
                for cat, features in sorted(by_category.items())
            ]
        else:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        return jsonify({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Ruleset Management Endpoints
# =============================================================================

@nixo_bp.route('/rulesets', methods=['GET'])
def get_rulesets():
    """Get all rulesets with summary info."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        rulesets = _ruleset_service.get_all_rulesets()

        return jsonify({
            "success": True,
            "rulesets": rulesets,
            "total": len(rulesets)
        })
    except Exception as e:
        logger.error(f"Error getting rulesets: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets', methods=['POST'])
def create_ruleset():
    """
    Create a new ruleset.

    Body:
        - name: Unique ruleset identifier
        - display_name: Human-readable name
        - description: Optional description
        - color: Hex color for UI (default: #6366f1)
        - icon: Icon name for UI (default: package)
        - inherits_from: Optional parent ruleset ID
        - is_template: Whether this is a template
        - features: Optional list of {feature_name, enabled} to assign
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()

        # Validate required fields
        if not data.get('name') or not data.get('display_name'):
            return jsonify({"success": False, "error": "name and display_name required"}), 400

        # Create ruleset
        ruleset = _ruleset_service.create_ruleset(
            name=data['name'],
            display_name=data['display_name'],
            description=data.get('description', ''),
            color=data.get('color', '#6366f1'),
            icon=data.get('icon', 'package'),
            inherits_from=data.get('inherits_from'),
            is_template=data.get('is_template', False),
            created_by=data.get('created_by', 'api')
        )

        if not ruleset:
            return jsonify({"success": False, "error": "Failed to create ruleset"}), 500

        # Add features if provided
        features = data.get('features', [])
        if features:
            for f in features:
                _ruleset_service.set_ruleset_feature(
                    ruleset['id'],
                    f['feature_name'],
                    f.get('enabled', True),
                    f.get('config', {})
                )

        return jsonify({
            "success": True,
            "ruleset": ruleset
        })
    except Exception as e:
        logger.error(f"Error creating ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>', methods=['GET'])
def get_ruleset(ruleset_id):
    """Get a single ruleset by ID."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        ruleset = _ruleset_service.get_ruleset(ruleset_id)
        if not ruleset:
            return jsonify({"success": False, "error": "Ruleset not found"}), 404

        return jsonify({
            "success": True,
            "ruleset": ruleset
        })
    except Exception as e:
        logger.error(f"Error getting ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>', methods=['PUT'])
def update_ruleset(ruleset_id):
    """
    Update a ruleset.

    Body: Fields to update (display_name, description, color, icon, inherits_from)
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()
        updated_by = data.pop('updated_by', 'api')

        success = _ruleset_service.update_ruleset(ruleset_id, data, updated_by)
        if not success:
            return jsonify({"success": False, "error": "Failed to update ruleset"}), 500

        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error updating ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>', methods=['DELETE'])
def delete_ruleset(ruleset_id):
    """Delete a ruleset."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        deleted_by = request.args.get('deleted_by', 'api')
        success = _ruleset_service.delete_ruleset(ruleset_id, deleted_by)

        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error deleting ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>/clone', methods=['POST'])
def clone_ruleset(ruleset_id):
    """
    Clone a ruleset.

    Body:
        - name: New ruleset name
        - display_name: New display name
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()

        if not data.get('name') or not data.get('display_name'):
            return jsonify({"success": False, "error": "name and display_name required"}), 400

        new_ruleset = _ruleset_service.clone_ruleset(
            source_id=ruleset_id,
            new_name=data['name'],
            new_display_name=data['display_name'],
            created_by=data.get('created_by', 'api')
        )

        if not new_ruleset:
            return jsonify({"success": False, "error": "Failed to clone ruleset"}), 500

        return jsonify({
            "success": True,
            "ruleset": new_ruleset
        })
    except Exception as e:
        logger.error(f"Error cloning ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>/features', methods=['GET'])
def get_ruleset_features(ruleset_id):
    """Get resolved features for a ruleset (including inherited)."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        include_inherited = request.args.get('include_inherited', 'true').lower() == 'true'

        if include_inherited:
            features = _ruleset_service.get_ruleset_resolved_features(ruleset_id)
        else:
            features = _ruleset_service.get_ruleset_direct_features(ruleset_id)

        return jsonify({
            "success": True,
            "features": features,
            "total": len(features)
        })
    except Exception as e:
        logger.error(f"Error getting ruleset features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/<ruleset_id>/features', methods=['PUT'])
def update_ruleset_features(ruleset_id):
    """
    Bulk update features for a ruleset.

    Body:
        - features: List of {feature_name, enabled, config}
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()
        features = data.get('features', [])
        updated_by = data.get('updated_by', 'api')

        success = _ruleset_service.bulk_update_ruleset_features(
            ruleset_id, features, updated_by
        )

        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error updating ruleset features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/rulesets/templates', methods=['GET'])
def get_template_rulesets():
    """Get all template rulesets for quick start."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        templates = _ruleset_service.get_template_rulesets()

        return jsonify({
            "success": True,
            "templates": templates
        })
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Client Management Endpoints
# =============================================================================

@nixo_bp.route('/clients', methods=['GET'])
def get_clients():
    """Get all clients with their ruleset info."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        clients = _ruleset_service.get_all_clients()

        # Optional: filter by ruleset
        ruleset_id = request.args.get('ruleset_id')
        if ruleset_id:
            clients = [c for c in clients if c.get('ruleset_id') == ruleset_id]

        return jsonify({
            "success": True,
            "clients": clients,
            "total": len(clients)
        })
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>', methods=['GET'])
def get_client(client_id):
    """Get a single client with full details."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        client = _ruleset_service.get_client(client_id)
        if not client:
            return jsonify({"success": False, "error": "Client not found"}), 404

        # Include resolved features
        features = _ruleset_service.get_client_resolved_features(client_id)
        overrides = _ruleset_service.get_client_overrides(client_id)

        return jsonify({
            "success": True,
            "client": client,
            "features": features,
            "overrides": overrides,
            "feature_count": len([f for f in features if f.get('enabled')])
        })
    except Exception as e:
        logger.error(f"Error getting client: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/ruleset', methods=['PUT'])
def assign_client_ruleset(client_id):
    """
    Assign a ruleset to a client.

    Body:
        - ruleset_id: The ruleset ID to assign
        - notes: Optional notes about the assignment
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()
        ruleset_id = data.get('ruleset_id')

        if not ruleset_id:
            return jsonify({"success": False, "error": "ruleset_id required"}), 400

        success = _ruleset_service.assign_client_ruleset(
            client_id=client_id,
            ruleset_id=ruleset_id,
            assigned_by=data.get('assigned_by', 'api'),
            notes=data.get('notes', '')
        )

        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error assigning ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/features', methods=['GET'])
def get_client_features(client_id):
    """Get final resolved features for a client."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        features = _ruleset_service.get_client_resolved_features(client_id)

        return jsonify({
            "success": True,
            "client_id": client_id,
            "features": features,
            "enabled_count": len([f for f in features if f.get('enabled')]),
            "total": len(features)
        })
    except Exception as e:
        logger.error(f"Error getting client features: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/check/<feature_name>', methods=['GET'])
def check_client_feature(client_id, feature_name):
    """
    Check if a specific feature is enabled for a client.
    This is the main feature flag check endpoint.
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        enabled = _ruleset_service.has_feature(client_id, feature_name)

        return jsonify({
            "success": True,
            "client_id": client_id,
            "feature_name": feature_name,
            "enabled": enabled
        })
    except Exception as e:
        logger.error(f"Error checking feature: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Override Management Endpoints
# =============================================================================

@nixo_bp.route('/clients/<client_id>/overrides', methods=['GET'])
def get_client_overrides(client_id):
    """Get all overrides for a client."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        overrides = _ruleset_service.get_client_overrides(client_id)

        return jsonify({
            "success": True,
            "overrides": overrides,
            "total": len(overrides)
        })
    except Exception as e:
        logger.error(f"Error getting overrides: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/overrides', methods=['POST'])
def add_client_override(client_id):
    """
    Add a feature override for a client.

    Body:
        - feature_name: The feature to override
        - enabled: True/False
        - reason: Optional reason for the override
        - expires_at: Optional ISO8601 expiration datetime
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()

        if not data.get('feature_name'):
            return jsonify({"success": False, "error": "feature_name required"}), 400

        if 'enabled' not in data:
            return jsonify({"success": False, "error": "enabled required"}), 400

        override = _ruleset_service.add_client_override(
            client_id=client_id,
            feature_name=data['feature_name'],
            enabled=data['enabled'],
            reason=data.get('reason', ''),
            expires_at=data.get('expires_at'),
            created_by=data.get('created_by', 'api')
        )

        if not override:
            return jsonify({"success": False, "error": "Failed to add override"}), 500

        return jsonify({
            "success": True,
            "override": override
        })
    except Exception as e:
        logger.error(f"Error adding override: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/overrides/<feature_name>', methods=['PUT'])
def update_client_override(client_id, feature_name):
    """
    Update an existing override.

    Body: Fields to update (enabled, reason, expires_at)
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        data = request.get_json()
        updated_by = data.pop('updated_by', 'api')

        success = _ruleset_service.update_client_override(
            client_id, feature_name, data, updated_by
        )

        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error updating override: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@nixo_bp.route('/clients/<client_id>/overrides/<feature_name>', methods=['DELETE'])
def remove_client_override(client_id, feature_name):
    """Remove an override."""
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        removed_by = request.args.get('removed_by', 'api')
        success = _ruleset_service.remove_client_override(
            client_id, feature_name, removed_by
        )

        return jsonify({"success": success})
    except Exception as e:
        logger.error(f"Error removing override: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Audit Log Endpoints
# =============================================================================

@nixo_bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    """
    Query audit logs.

    Query params:
        - entity_type: Filter by entity type
        - entity_id: Filter by entity ID
        - limit: Max number of results (default: 100)
    """
    try:
        if not _ruleset_service:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        limit = int(request.args.get('limit', 100))

        logs = _ruleset_service.get_audit_logs(entity_type, entity_id, limit)

        return jsonify({
            "success": True,
            "logs": logs,
            "total": len(logs)
        })
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =============================================================================
# Utility Endpoints
# =============================================================================

@nixo_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for nixo services."""
    return jsonify({
        "success": True,
        "feature_sync": _feature_sync is not None,
        "ruleset_service": _ruleset_service is not None
    })
