"""
Feature Flagging API - Production Vercel Deployment
Includes: Feature flags, AST analysis, Ruleset management, Supabase integration
Enhanced: API authentication, Targeting rules, Scheduling, Audit logging
Nixo: Feature management system with flexible rulesets and inheritance
"""
import os, sys, logging, json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, request, render_template, g
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

# Import nixo blueprint
try:
    from nixo_routes import nixo_bp, init_nixo_services
    app.register_blueprint(nixo_bp)
    logger.info("✓ Nixo blueprint registered")
except Exception as e:
    logger.warning(f"⚠️ Nixo blueprint: {e}")

# Process after-request callbacks
@app.after_request
def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', []):
        callback(response)
    return response

# Initialize clients
ff_client = None
supabase_client = None
ast_analyzer = None
api_key_manager = None
audit_logger = None

# Load SupabaseClient first (needed by other components)
try:
    from supabase_client import SupabaseClient
    supabase_client = SupabaseClient()
    logger.info("✓ SupabaseClient initialized")
except Exception as e:
    logger.warning(f"⚠️ SupabaseClient: {e}")

# Initialize nixo services with Supabase client
try:
    init_nixo_services(supabase_client)
    logger.info("✓ Nixo services initialized")
except Exception as e:
    logger.warning(f"⚠️ Nixo services: {e}")

# Load API Key Manager
try:
    from auth import get_api_key_manager, require_api_key
    api_key_manager = get_api_key_manager(supabase_client)
    logger.info("✓ APIKeyManager initialized")
except Exception as e:
    logger.warning(f"⚠️ APIKeyManager: {e}")
    # Create dummy decorator if auth module fails
    def require_api_key(permission="read"):
        def decorator(f):
            return f
        return decorator

# Load Audit Logger
try:
    from audit import get_audit_logger, AuditAction, EntityType
    audit_logger = get_audit_logger(supabase_client)
    logger.info("✓ AuditLogger initialized")
except Exception as e:
    logger.warning(f"⚠️ AuditLogger: {e}")

# Load FeatureFlagClient (with enhanced features)
try:
    from feature_flag_client import FeatureFlagClient
    ff_client = FeatureFlagClient(
        config_path='rulesets.yaml',
        clients_path='clients.yaml',
        bootstrap_path='bootstrap_defaults.json',
        supabase_client=supabase_client,
        enable_targeting=True,
        enable_scheduling=True,
        enable_audit=True
    )
    logger.info("✓ FeatureFlagClient initialized (enhanced)")
except Exception as e:
    logger.warning(f"⚠️ FeatureFlagClient: {e}")

# Load AST Analyzer
try:
    from enhanced_ast_analyzer import analyze_codebase_with_helpers, get_functions_for_feature
    ast_analyzer = {'analyze': analyze_codebase_with_helpers, 'get_functions': get_functions_for_feature}
    logger.info("✓ AST Analyzer loaded")
except Exception as e:
    logger.warning(f"⚠️ AST Analyzer: {e}")

# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Template error: {e}")
        return jsonify({
            "message": "Feature Flagging API",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "clients": "/api/clients",
                "rulesets": "/api/rulesets",
                "analyze": "/api/analyze"
            }
        })

# ============================================================================
# API INFO & HEALTH
# ============================================================================

@app.route('/api')
def api_info():
    """API information"""
    return jsonify({
        "message": "Feature Flagging API",
        "version": "2.0",
        "status": "production",
        "features": {
            "feature_flags": ff_client is not None,
            "ast_analysis": ast_analyzer is not None,
            "supabase": supabase_client is not None
        },
        "endpoints": {
            "clients": "/api/clients",
            "rulesets": "/api/rulesets",
            "analyze": "/api/analyze",
            "projects": "/api/projects",
            "kill_switch": "/api/kill-switch"
        }
    })

@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "feature_flags": ff_client is not None,
        "ast_analysis": ast_analyzer is not None,
        "supabase": supabase_client is not None
    })

# ============================================================================
# CLIENT MANAGEMENT
# ============================================================================

@app.route('/api/clients')
def get_clients():
    """Get all clients with features"""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503
    try:
        clients = ff_client.get_all_clients()
        result = {}
        for client_id, client_data in clients.items():
            features = list(ff_client.get_client_features(client_id))
            result[client_id] = {
                **client_data,
                'features': features,
                'feature_count': len(features)
            }
        return jsonify({"success": True, "clients": result})
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clients/<client_id>')
def get_client_details(client_id):
    """Get specific client details"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        clients = ff_client.get_all_clients()
        if client_id not in clients:
            return jsonify({"success": False, "error": "Client not found"}), 404
        
        client_data = clients[client_id]
        features = list(ff_client.get_client_features(client_id))
        
        return jsonify({
            "success": True,
            "client": {
                "id": client_id,
                **client_data,
                "features": features,
                "feature_count": len(features)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# RULESET MANAGEMENT
# ============================================================================

@app.route('/api/rulesets')
def get_rulesets():
    """Get all rulesets"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        rulesets = ff_client.get_all_rulesets()
        return jsonify({"success": True, "rulesets": rulesets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/rulesets', methods=['POST'])
def create_ruleset():
    """Create new ruleset from analyzed codebase features"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        ruleset_name = data.get('name')
        description = data.get('description', '')
        features = data.get('features', [])
        baseline = data.get('baseline_ruleset')
        
        if not ruleset_name or not features:
            return jsonify({"success": False, "error": "Name and features required"}), 400
        
        # Read current rulesets
        import yaml
        with open('rulesets.yaml', 'r') as f:
            rulesets_data = yaml.safe_load(f) or {}
        
        # Add new ruleset
        rulesets_data['rulesets'] = rulesets_data.get('rulesets', {})
        rulesets_data['rulesets'][ruleset_name] = {
            'description': description,
            'baseline_ruleset': baseline,
            'features': features
        }
        
        # Save back
        with open('rulesets.yaml', 'w') as f:
            yaml.dump(rulesets_data, f, default_flow_style=False, sort_keys=False)
        
        # Reload the client
        ff_client._load_configuration()
        
        return jsonify({
            "success": True,
            "message": f"Ruleset '{ruleset_name}' created with {len(features)} features",
            "ruleset": rulesets_data['rulesets'][ruleset_name]
        })
    except Exception as e:
        logger.error(f"Error creating ruleset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# AST ANALYSIS & CODEBASE INTEGRATION
# ============================================================================

@app.route('/api/analyze', methods=['POST'])
def analyze_codebase():
    """Analyze codebase and extract features for ruleset creation"""
    if not ast_analyzer:
        return jsonify({"success": False, "error": "AST analyzer not available"}), 503
    
    try:
        data = request.get_json()
        codebase_path = data.get('path')
        project_name = data.get('project_name', 'Analyzed Project')
        
        if not codebase_path:
            return jsonify({"success": False, "error": "Codebase path required"}), 400
        
        # Analyze the codebase
        logger.info(f"Analyzing codebase at: {codebase_path}")
        graph_data = ast_analyzer['analyze'](codebase_path)
        
        # Extract features from function names
        features = set()
        functions = []
        
        if 'nodes' in graph_data:
            for node in graph_data['nodes']:
                func_name = node.get('id', '')
                if func_name and not func_name.startswith('_'):
                    # Convert function names to feature names
                    feature_name = func_name.replace('_', ' ').title().replace(' ', '_').lower()
                    features.add(feature_name)
                    functions.append({
                        'name': func_name,
                        'feature': feature_name,
                        'file': node.get('file', 'unknown')
                    })
        
        features_list = sorted(list(features))
        
        # Store in Supabase if available
        project_id = None
        if supabase_client:
            try:
                project = supabase_client.create_project(
                    name=project_name,
                    description=f"Analyzed from {codebase_path}",
                    repository_url=codebase_path,
                    metadata={'features': features_list, 'function_count': len(functions)}
                )
                project_id = project.get('id')
            except Exception as e:
                logger.warning(f"Could not save to Supabase: {e}")
        
        return jsonify({
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "features_found": len(features_list),
            "features": features_list,
            "functions": functions[:50],  # Limit for response size
            "total_functions": len(functions),
            "graph": {
                "nodes": len(graph_data.get('nodes', [])),
                "edges": len(graph_data.get('edges', []))
            },
            "suggested_ruleset_name": f"{project_name.lower().replace(' ', '_')}_features"
        })
    except Exception as e:
        logger.error(f"Error analyzing codebase: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/analyze/preview', methods=['POST'])
def preview_analysis():
    """Quick preview of what features would be extracted"""
    data = request.get_json()
    sample_functions = data.get('functions', [])
    
    features = []
    for func in sample_functions:
        if not func.startswith('_'):
            feature = func.replace('_', ' ').title().replace(' ', '_').lower()
            features.append({"function": func, "feature": feature})
    
    return jsonify({"success": True, "preview": features})

# ============================================================================
# FEATURE CHECKING
# ============================================================================

@app.route('/api/client/<client_id>/feature/<feature_name>')
def check_feature(client_id, feature_name):
    """Check if feature is enabled for client"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        user_id = request.args.get('user_id')
        context = {"user_id": user_id} if user_id else None
        enabled = ff_client.isEnabled(client_id, feature_name, context)
        return jsonify({
            "success": True,
            "client_id": client_id,
            "feature_name": feature_name,
            "enabled": enabled
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# KILL SWITCH
# ============================================================================

@app.route('/api/kill-switch', methods=['GET', 'POST'])
def kill_switch():
    """Manage global kill switch"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        if request.method == 'POST':
            activate = request.get_json().get('activate', False)
            if activate:
                ff_client.activate_kill_switch()
            else:
                ff_client.deactivate_kill_switch()
            return jsonify({"success": True, "active": activate})
        else:
            active = ff_client.engine._use_baseline
            return jsonify({"success": True, "active": active})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# PROJECT MANAGEMENT (Supabase)
# ============================================================================

@app.route('/api/projects')
def list_projects():
    """List all projects"""
    if not supabase_client:
        return jsonify({"success": True, "projects": [], "note": "Supabase not configured"}), 200
    try:
        projects = supabase_client.list_projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create new project"""
    if not supabase_client:
        return jsonify({"success": False, "error": "Supabase not configured"}), 503
    try:
        data = request.get_json()
        project = supabase_client.create_project(
            name=data.get('name'),
            description=data.get('description', ''),
            repository_url=data.get('repository_url', ''),
            metadata=data.get('metadata', {})
        )
        return jsonify({"success": True, "project": project})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@app.route('/api/keys', methods=['GET'])
def list_api_keys():
    """List all API keys (requires admin)"""
    if not api_key_manager:
        return jsonify({"success": False, "error": "API key management not available"}), 503
    try:
        client_id = request.args.get('client_id')
        keys = api_key_manager.list_keys(client_id)
        return jsonify({"success": True, "keys": keys})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/keys', methods=['POST'])
def create_api_key():
    """Create a new API key"""
    if not api_key_manager:
        return jsonify({"success": False, "error": "API key management not available"}), 503
    try:
        data = request.get_json()
        name = data.get('name')
        if not name:
            return jsonify({"success": False, "error": "Name required"}), 400

        full_key, key_record = api_key_manager.create_key(
            name=name,
            client_id=data.get('client_id'),
            permissions=data.get('permissions', ['read']),
            rate_limit=data.get('rate_limit', 1000),
            expires_in_days=data.get('expires_in_days'),
            description=data.get('description', ''),
            created_by=data.get('created_by', 'api')
        )

        if audit_logger:
            audit_logger.log_api_key_created(key_record)

        return jsonify({
            "success": True,
            "key": full_key,  # Only returned once!
            "key_info": {
                "prefix": key_record.get('key_prefix'),
                "name": key_record.get('name'),
                "permissions": key_record.get('permissions'),
                "rate_limit": key_record.get('rate_limit')
            },
            "warning": "Save this key now - it won't be shown again!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/keys/<key_id>', methods=['DELETE'])
def revoke_api_key(key_id):
    """Revoke an API key"""
    if not api_key_manager:
        return jsonify({"success": False, "error": "API key management not available"}), 503
    try:
        success = api_key_manager.revoke_key(key_id)
        if success and audit_logger:
            audit_logger.log_api_key_revoked(key_id, "")
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# TARGETING RULES
# ============================================================================

@app.route('/api/targeting-rules', methods=['GET'])
def list_targeting_rules():
    """List all targeting rules"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        feature_name = request.args.get('feature_name')
        rules = ff_client.list_targeting_rules(feature_name)
        return jsonify({"success": True, "rules": rules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/targeting-rules', methods=['POST'])
def create_targeting_rule():
    """Create a new targeting rule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        required = ['name', 'feature_name', 'conditions']
        for field in required:
            if field not in data:
                return jsonify({"success": False, "error": f"{field} required"}), 400

        rule = ff_client.add_targeting_rule(data)
        if rule:
            return jsonify({"success": True, "rule": rule})
        return jsonify({"success": False, "error": "Failed to create rule"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/targeting-rules/<rule_id>', methods=['PUT'])
def update_targeting_rule(rule_id):
    """Update a targeting rule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        success = ff_client.update_targeting_rule(rule_id, data)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/targeting-rules/<rule_id>', methods=['DELETE'])
def delete_targeting_rule(rule_id):
    """Delete a targeting rule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        success = ff_client.delete_targeting_rule(rule_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# SCHEDULING
# ============================================================================

@app.route('/api/schedules', methods=['GET'])
def list_schedules():
    """List all feature schedules"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        feature_name = request.args.get('feature_name')
        schedules = ff_client.list_schedules(feature_name)
        return jsonify({"success": True, "schedules": schedules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    """Create a new feature schedule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        required = ['feature_name', 'schedule_type']
        for field in required:
            if field not in data:
                return jsonify({"success": False, "error": f"{field} required"}), 400

        schedule = ff_client.add_schedule(data)
        if schedule:
            return jsonify({"success": True, "schedule": schedule})
        return jsonify({"success": False, "error": "Failed to create schedule"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Update a schedule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        success = ff_client.update_schedule(schedule_id, data)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Delete a schedule"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        success = ff_client.delete_schedule(schedule_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/schedules/upcoming', methods=['GET'])
def get_upcoming_schedules():
    """Get schedules starting within next N hours"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        hours = int(request.args.get('hours', 24))
        schedules = ff_client.get_upcoming_schedules(hours)
        return jsonify({"success": True, "schedules": schedules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# AUDIT LOGS
# ============================================================================

@app.route('/api/audit-logs', methods=['GET'])
def query_audit_logs():
    """Query audit logs with filters"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id')
        limit = int(request.args.get('limit', 100))

        logs = ff_client.get_audit_logs(entity_type, entity_id, limit)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/audit-logs/recent', methods=['GET'])
def get_recent_activity():
    """Get recent activity"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        hours = int(request.args.get('hours', 24))
        logs = ff_client.get_recent_activity(hours)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/audit-logs/feature/<feature_name>', methods=['GET'])
def get_feature_history(feature_name):
    """Get audit history for a feature"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        limit = int(request.args.get('limit', 50))
        logs = ff_client.get_feature_history(feature_name, limit)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# ENHANCED FEATURE CHECKING
# ============================================================================

@app.route('/api/client/<client_id>/feature/<feature_name>/detailed')
def check_feature_detailed(client_id, feature_name):
    """Check if feature is enabled with detailed evaluation info"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        # Build user context from query params
        user_context = {}
        for key, value in request.args.items():
            if key not in ['_']:  # Skip cache buster
                user_context[key] = value

        result = ff_client.isEnabledDetailed(client_id, feature_name, user_context or None)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# CLIENT MANAGEMENT ENHANCED
# ============================================================================

@app.route('/api/clients/<client_id>/ruleset', methods=['PUT'])
def update_client_ruleset(client_id):
    """Update a client's ruleset"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        new_ruleset = data.get('ruleset')
        if not new_ruleset:
            return jsonify({"success": False, "error": "Ruleset required"}), 400

        # Get old ruleset for audit
        clients = ff_client.get_all_clients()
        old_ruleset = clients.get(client_id, {}).get('ruleset')

        success = ff_client.update_client_ruleset(client_id, new_ruleset)

        if success and audit_logger:
            audit_logger.log_client_change(
                client_id,
                "ruleset_change",
                before={"ruleset": old_ruleset},
                after={"ruleset": new_ruleset}
            )

        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/clients', methods=['POST'])
def create_client():
    """Create a new client"""
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        ruleset = data.get('ruleset', 'baseline')
        metadata = data.get('metadata', {})

        if not client_id:
            return jsonify({"success": False, "error": "client_id required"}), 400

        ff_client.register_client(client_id, ruleset, metadata)

        # Save to YAML
        import yaml
        with open('clients.yaml', 'r') as f:
            clients_data = yaml.safe_load(f) or {}

        clients_data[client_id] = {
            'ruleset': ruleset,
            'metadata': metadata
        }

        with open('clients.yaml', 'w') as f:
            yaml.dump(clients_data, f, default_flow_style=False, sort_keys=False)

        if audit_logger:
            audit_logger.log_client_change(
                client_id,
                "create",
                after={"ruleset": ruleset, "metadata": metadata}
            )

        return jsonify({
            "success": True,
            "client": {"client_id": client_id, "ruleset": ruleset, "metadata": metadata}
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# SYSTEM STATUS
# ============================================================================

@app.route('/api/status')
def system_status():
    """Get comprehensive system status"""
    try:
        status = {
            "healthy": True,
            "version": "2.1.0",
            "features": {
                "feature_flags": ff_client is not None,
                "supabase": supabase_client is not None,
                "ast_analysis": ast_analyzer is not None,
                "api_authentication": api_key_manager is not None,
                "audit_logging": audit_logger is not None,
                "targeting_rules": ff_client._targeting_engine is not None if ff_client else False,
                "scheduling": ff_client._schedule_engine is not None if ff_client else False
            },
            "stats": {}
        }

        if ff_client:
            clients = ff_client.get_all_clients()
            rulesets = ff_client.get_all_rulesets()
            status["stats"]["clients"] = len(clients)
            status["stats"]["rulesets"] = len(rulesets)
            status["stats"]["kill_switch_active"] = ff_client.engine._use_baseline

        return jsonify(status)
    except Exception as e:
        return jsonify({"healthy": False, "error": str(e)}), 500

# Export for Vercel
logger.info("✓ Feature Flagging API ready (v2.1.0 - Enhanced)")
application = app
