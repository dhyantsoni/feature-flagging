"""
Flask Backend for Feature Flagging Dashboard

Provides REST API and serves the frontend dashboard.
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import yaml

from feature_flag_client import FeatureFlagClient

app = Flask(__name__)
CORS(app)

# Initialize feature flag client
ff_client = FeatureFlagClient()


# Frontend Routes
@app.route('/')
def index():
    """Serve the main dashboard."""
    return render_template('index.html')


# API Routes

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all registered clients."""
    try:
        clients = ff_client.get_all_clients()
        # Enhance with feature information
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
    try:
        rulesets = ff_client.get_all_rulesets()
        return jsonify({"success": True, "rulesets": rulesets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/client/<client_id>', methods=['GET'])
def get_client_details(client_id):
    """Get detailed information about a specific client."""
    try:
        clients = ff_client.get_all_clients()
        if client_id not in clients:
            return jsonify({"success": False, "error": "Client not found"}), 404

        client_data = clients[client_id]
        features = list(ff_client.get_client_features(client_id))
        ruleset_name = client_data.get('ruleset')

        # Get ruleset info
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


@app.route('/api/client/<client_id>/ruleset', methods=['PUT'])
def update_client_ruleset(client_id):
    """Update a client's assigned ruleset."""
    try:
        data = request.get_json()
        new_ruleset = data.get('ruleset')

        if not new_ruleset:
            return jsonify({"success": False, "error": "Ruleset name required"}), 400

        # Check if ruleset exists
        rulesets = ff_client.get_all_rulesets()
        if new_ruleset not in rulesets:
            return jsonify({"success": False, "error": "Ruleset not found"}), 404

        success = ff_client.update_client_ruleset(client_id, new_ruleset)

        if success:
            # Also update the YAML file
            _update_client_yaml(client_id, new_ruleset)
            return jsonify({"success": True, "message": "Ruleset updated successfully"})
        else:
            return jsonify({"success": False, "error": "Client not found"}), 404

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/client', methods=['POST'])
def create_client():
    """Register a new client."""
    try:
        data = request.get_json()
        client_id = data.get('client_id')
        ruleset = data.get('ruleset')
        metadata = data.get('metadata', {})

        if not client_id or not ruleset:
            return jsonify({"success": False, "error": "client_id and ruleset required"}), 400

        # Check if ruleset exists
        rulesets = ff_client.get_all_rulesets()
        if ruleset not in rulesets:
            return jsonify({"success": False, "error": "Ruleset not found"}), 404

        # Check if client already exists
        clients = ff_client.get_all_clients()
        if client_id in clients:
            return jsonify({"success": False, "error": "Client already exists"}), 400

        ff_client.register_client(client_id, ruleset, metadata)

        # Update the YAML file
        _add_client_to_yaml(client_id, ruleset, metadata)

        return jsonify({"success": True, "message": "Client created successfully"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kill-switch', methods=['POST'])
def toggle_kill_switch():
    """Toggle the global kill switch."""
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
    try:
        active = ff_client.engine._use_baseline
        return jsonify({"success": True, "active": active})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Helper functions

def _update_client_yaml(client_id, new_ruleset):
    """Update client ruleset in YAML file."""
    try:
        with open('clients.yaml', 'r') as f:
            clients = yaml.safe_load(f) or {}

        if client_id in clients:
            clients[client_id]['ruleset'] = new_ruleset

        with open('clients.yaml', 'w') as f:
            yaml.dump(clients, f, default_flow_style=False, sort_keys=False)

    except Exception as e:
        print(f"Error updating clients.yaml: {e}")


def _add_client_to_yaml(client_id, ruleset, metadata):
    """Add new client to YAML file."""
    try:
        with open('clients.yaml', 'r') as f:
            clients = yaml.safe_load(f) or {}

        clients[client_id] = {
            'ruleset': ruleset,
            'metadata': metadata
        }

        with open('clients.yaml', 'w') as f:
            yaml.dump(clients, f, default_flow_style=False, sort_keys=False)

    except Exception as e:
        print(f"Error updating clients.yaml: {e}")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
