"""
Feature Flagging API - Production Vercel Deployment
Includes: Feature flags, AST analysis, Ruleset management, Supabase integration
"""
import os, sys, logging, json
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

# Initialize clients
ff_client = None
supabase_client = None
ast_analyzer = None

# Load FeatureFlagClient
try:
    from feature_flag_client import FeatureFlagClient
    ff_client = FeatureFlagClient(
        config_path='rulesets.yaml',
        clients_path='clients.yaml', 
        bootstrap_path='bootstrap_defaults.json'
    )
    logger.info("✓ FeatureFlagClient initialized")
except Exception as e:
    logger.warning(f"⚠️ FeatureFlagClient: {e}")

# Load AST Analyzer
try:
    from enhanced_ast_analyzer import analyze_codebase_with_helpers, get_functions_for_feature
    ast_analyzer = {'analyze': analyze_codebase_with_helpers, 'get_functions': get_functions_for_feature}
    logger.info("✓ AST Analyzer loaded")
except Exception as e:
    logger.warning(f"⚠️ AST Analyzer: {e}")

# Load SupabaseClient
try:
    from supabase_client import SupabaseClient
    supabase_client = SupabaseClient()
    logger.info("✓ SupabaseClient initialized")
except Exception as e:
    logger.warning(f"⚠️ SupabaseClient: {e}")

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

# Export for Vercel
logger.info("✓ Feature Flagging API ready")
application = app
