"""
Feature Flagging API - Vercel Deployment Handler
Properly configured for @vercel/python serverless runtime
"""
import os
import sys
import logging
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import from root
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

logger.info(f"ROOT_DIR set to: {ROOT_DIR}")
logger.info(f"Templates exist: {(ROOT_DIR / 'templates').exists()}")
logger.info(f"Static exists: {(ROOT_DIR / 'static').exists()}")

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS

# Create Flask app with correct paths
app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / 'templates'),
    static_folder=str(ROOT_DIR / 'static'),
    static_url_path='/static'
)
CORS(app)
logger.info("Flask app created successfully")

# Initialize clients with error handling
ff_client = None
supabase_client = None
IMPORTS_SUCCESSFUL = False

try:
    from feature_flag_client import FeatureFlagClient
    from supabase_client import SupabaseClient
    from enhanced_ast_analyzer import analyze_codebase_with_helpers, get_functions_for_feature

    IMPORTS_SUCCESSFUL = True
    logger.info("✓ All imports successful")

    try:
        ff_client = FeatureFlagClient()
        logger.info("✓ FeatureFlagClient initialized")
    except Exception as e:
        logger.warning(f"⚠️ FeatureFlagClient initialization failed: {e}")

    try:
        supabase_client = SupabaseClient()
        logger.info("✓ SupabaseClient initialized")
    except Exception as e:
        logger.warning(f"⚠️ SupabaseClient initialization failed: {e}")

except Exception as e:
    logger.error(f"❌ Import error: {e}")
    IMPORTS_SUCCESSFUL = False

@app.route('/')
def index():
    """Serve the dashboard frontend"""
    try:
        return render_template('dashboard.html')
    except:
        return render_template('index.html')

@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        "message": "Feature Flagging API",
        "version": "1.0",
        "status": "deployed",
        "modules_loaded": IMPORTS_SUCCESSFUL,
        "clients_initialized": {
            "feature_flags": ff_client is not None,
            "supabase": supabase_client is not None
        },
        "endpoints": {
            "health": "/health",
            "clients": "/api/clients",
            "rulesets": "/api/rulesets",
            "projects": "/api/projects"
        }
    })

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory(str(ROOT_DIR / 'static'), path)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "supabase": supabase_client is not None,
        "feature_flags": ff_client is not None,
        "endpoints": {
            "clients": "/api/clients",
            "rulesets": "/api/rulesets",
            "projects": "/api/projects",
            "analyze": "/api/analyze",
            "functions": "/api/functions"
        }
    })

# ============================================================================
# Client Management Endpoints
# ============================================================================

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all registered clients."""
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
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/rulesets', methods=['GET'])
def get_rulesets():
    """Get all available rulesets."""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503

    try:
        rulesets = ff_client.get_all_rulesets()
        return jsonify({"success": True, "rulesets": rulesets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/client/<client_id>', methods=['GET'])
def get_client_details(client_id):
    """Get detailed information about a specific client."""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503

    try:
        clients = ff_client.get_all_clients()
        if client_id not in clients:
            return jsonify({"success": False, "error": "Client not found"}), 404

        client_data = clients[client_id]
        features = list(ff_client.get_client_features(client_id))
        ruleset_name = client_data.get('ruleset')

        rulesets = ff_client.get_all_rulesets()
        ruleset_info = rulesets.get(ruleset_name, {})

        return jsonify({
            "success": True,
            "client": {
                "client_id": client_id,
                **client_data,
                "features": features,
                "feature_count": len(features),
                "ruleset_description": ruleset_info.get('description', '')
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/client/<client_id>/feature/<feature_name>', methods=['GET'])
def check_feature(client_id, feature_name):
    """Check if a specific feature is enabled for a client."""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503

    try:
        user_id = request.args.get('user_id')
        user_context = {"user_id": user_id} if user_id else None

        enabled = ff_client.isEnabled(client_id, feature_name, user_context)

        return jsonify({
            "success": True,
            "client_id": client_id,
            "feature_name": feature_name,
            "enabled": enabled
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kill-switch', methods=['POST'])
def toggle_kill_switch():
    """Toggle the global kill switch."""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503

    try:
        data = request.get_json()
        activate = data.get('activate', False)

        if activate:
            ff_client.activate_kill_switch()
            message = "Kill switch activated - all clients using baseline"
        else:
            ff_client.deactivate_kill_switch()
            message = "Kill switch deactivated - normal operation resumed"

        return jsonify({"success": True, "message": message, "active": activate})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kill-switch', methods=['GET'])
def get_kill_switch_status():
    """Get current kill switch status."""
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503

    try:
        active = ff_client.engine._use_baseline
        return jsonify({"success": True, "active": active})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================================
# Supabase / Project Endpoints
# ============================================================================

@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all projects"""
    if not supabase_client:
        return jsonify({"success": False, "error": "Supabase not configured"}), 503

    try:
        projects = supabase_client.list_projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new project"""
    if not supabase_client:
        return jsonify({"success": False, "error": "Supabase not configured"}), 503

    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        repository_url = data.get('repository_url', '')
        metadata = data.get('metadata', {})

        if not name:
            return jsonify({"success": False, "error": "Project name required"}), 400

        project = supabase_client.create_project(name, description, repository_url, metadata)
        return jsonify({"success": True, "project": project})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({"error": "Not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Vercel Handler
# ============================================================================

# Log that app is ready
logger.info("=" * 50)
logger.info("Flask app initialized and ready for Vercel")
logger.info(f"Environment: {os.environ.get('FLASK_ENV', 'production')}")
logger.info(f"Root directory: {ROOT_DIR}")
logger.info("=" * 50)

# For local testing
if __name__ == '__main__':
    logger.info("Running Flask app locally...")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))