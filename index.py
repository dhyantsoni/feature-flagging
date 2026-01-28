"""Feature Flagging API - Vercel"""
import os, sys, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

ff_client = None
supabase_client = None

try:
    from feature_flag_client import FeatureFlagClient
    ff_client = FeatureFlagClient(config_path='rulesets.yaml', clients_path='clients.yaml', bootstrap_path='bootstrap_defaults.json')
    logger.info("✓ FeatureFlagClient initialized")
except Exception as e:
    logger.warning(f"⚠️ FeatureFlagClient: {e}")

try:
    from enhanced_ast_analyzer import analyze_codebase_with_helpers, get_functions_for_feature
except ImportError as e:
    logger.warning(f"⚠️ AST analyzer: {e}")

try:
    from supabase_client import SupabaseClient
    supabase_client = SupabaseClient()
    logger.info("✓ SupabaseClient initialized")
except Exception as e:
    logger.warning(f"⚠️ SupabaseClient: {e}")

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except:
        return jsonify({"message": "Feature Flagging API", "status": "ok"})

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "feature_flags": ff_client is not None, "supabase": supabase_client is not None})

@app.route('/api/clients')
def get_clients():
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503
    try:
        clients = ff_client.get_all_clients()
        result = {cid: {**cd, 'features': list(ff_client.get_client_features(cid)), 'feature_count': len(list(ff_client.get_client_features(cid)))} for cid, cd in clients.items()}
        return jsonify({"success": True, "clients": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/rulesets')
def get_rulesets():
    if not ff_client:
        return jsonify({"success": False, "error": "Feature flag client not initialized"}), 503
    return jsonify({"success": True, "rulesets": ff_client.get_all_rulesets()})

@app.route('/api/client/<client_id>/feature/<feature_name>')
def check_feature(client_id, feature_name):
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    enabled = ff_client.isEnabled(client_id, feature_name, {"user_id": request.args.get('user_id')} if request.args.get('user_id') else None)
    return jsonify({"success": True, "enabled": enabled})

@app.route('/api/kill-switch', methods=['GET', 'POST'])
def kill_switch():
    if not ff_client:
        return jsonify({"success": False, "error": "Not initialized"}), 503
    if request.method == 'POST':
        activate = request.get_json().get('activate', False)
        ff_client.activate_kill_switch() if activate else ff_client.deactivate_kill_switch()
        return jsonify({"success": True, "active": activate})
    return jsonify({"success": True, "active": ff_client.engine._use_baseline})

application = app
