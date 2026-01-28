# Quick Start Guide - Feature Flagging System

## 🚀 Access Your Dashboard

**Live URL**: https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app

## 🎯 Quick Actions

### 1. View Client Features (UI)
1. Open the dashboard URL
2. Click any client in the left sidebar
3. See all enabled features displayed as cards

### 2. Create a New Ruleset (Easy Way)

#### Via UI:
1. Click "Create Ruleset" button (if available)
2. Enter ruleset name (e.g., "premium_tier")
3. Enter description (e.g., "Premium plan features")
4. Enter features comma-separated (e.g., "api_access,advanced_reports,priority_support")
5. Optionally enter baseline ruleset (e.g., "baseline")
6. Click Create

#### Via API (Copy & Paste):
```bash
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "premium_tier",
    "description": "Premium plan with advanced features",
    "features": [
      "api_access",
      "advanced_reports",
      "priority_support",
      "custom_integrations",
      "white_labeling"
    ],
    "baseline_ruleset": "baseline"
  }'
```

### 3. Analyze Your Codebase (Local)

```bash
# This extracts features from your code automatically
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/your/project",
    "project_name": "MyAwesomeApp"
  }'

# Response will show:
# - Extracted features from function names
# - Suggested ruleset name
# - Total functions analyzed
```

The analyzer will:
- Read all Python files in your codebase
- Extract function names
- Convert them to feature names (e.g., `send_email` → `send_email`)
- Suggest a ruleset name based on your project

### 4. Emergency Kill Switch

**Via UI**: Toggle the switch in the header

**Via API**:
```bash
# Activate (disable all features except baseline)
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"activate": true}'

# Deactivate (restore normal operation)
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"activate": false}'
```

## 📝 Smart Ruleset Creation Workflow

### Scenario 1: Analyze Existing Code
```bash
# Step 1: Analyze your codebase
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "./myapp", "project_name": "MyApp"}'

# Step 2: Response gives you features array
# Copy the features from response

# Step 3: Create ruleset with those features
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "myapp_features",
    "description": "Auto-generated from MyApp",
    "features": ["<paste features here>"]
  }'
```

### Scenario 2: Manual Feature List
```bash
# You know exactly what features you want
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mobile_tier",
    "description": "Mobile app specific features",
    "features": [
      "push_notifications",
      "offline_mode",
      "biometric_auth",
      "mobile_dashboard"
    ],
    "baseline_ruleset": "baseline"
  }'
```

### Scenario 3: Extend Existing Ruleset
```bash
# Build on top of another ruleset
curl -X POST https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "enterprise_plus",
    "description": "Enterprise with extra features",
    "features": [
      "dedicated_support",
      "custom_sla",
      "priority_updates"
    ],
    "baseline_ruleset": "enterprise_tier"
  }'
```

## 🔍 Check Feature Status

### For a Specific Client
```bash
curl https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/clients/acme_corp/feature/advanced_analytics

# Response:
# {
#   "success": true,
#   "enabled": true,
#   "client_id": "acme_corp",
#   "feature_name": "advanced_analytics"
# }
```

### List All Client Features
```bash
curl https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app/api/clients/acme_corp

# Response includes:
# - All enabled features
# - Feature count
# - Client metadata
# - Ruleset name
```

## 🎨 Using in Your Application

### Python Example
```python
import requests

API_URL = "https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app"

def is_feature_enabled(client_id, feature_name):
    response = requests.get(f"{API_URL}/api/clients/{client_id}/feature/{feature_name}")
    data = response.json()
    return data.get('enabled', False)

# Usage
if is_feature_enabled('acme_corp', 'advanced_analytics'):
    # Show advanced analytics
    show_advanced_analytics()
else:
    # Show basic analytics
    show_basic_analytics()
```

### JavaScript Example
```javascript
const API_URL = 'https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app';

async function isFeatureEnabled(clientId, featureName) {
  const response = await fetch(`${API_URL}/api/clients/${clientId}/feature/${featureName}`);
  const data = await response.json();
  return data.enabled || false;
}

// Usage
if (await isFeatureEnabled('acme_corp', 'advanced_analytics')) {
  // Show advanced analytics
  showAdvancedAnalytics();
} else {
  // Show basic analytics
  showBasicAnalytics();
}
```

## 📊 Available Features (Current)

Based on existing rulesets, here are all available features:
- `user_management`
- `profile_settings`
- `basic_dashboard`
- `enhanced_dashboard`
- `enterprise_dashboard`
- `experimental_dashboard`
- `basic_reports`
- `advanced_reports`
- `custom_reports`
- `real_time_reports`
- `email_notifications`
- `webhook_notifications`
- `api_access`
- `slack_integration`
- `teams_integration`
- `custom_integrations`
- `export_data`
- `bulk_import`
- `advanced_analytics`
- `predictive_analytics`
- `white_labeling`
- `sso_authentication`
- `audit_logs`
- `dedicated_support`
- `ai_insights`
- `new_feature_preview`

Use these in your rulesets or create your own!

## 🎯 Best Practices

1. **Name Features Consistently**: Use snake_case like `advanced_analytics`
2. **Use Baseline Rulesets**: Build on existing rulesets instead of starting from scratch
3. **Test Before Deploy**: Use local analysis to preview features
4. **Document Features**: Add descriptions in rulesets
5. **Monitor Kill Switch**: Don't leave it activated long-term

## 🆘 Troubleshooting

### UI Not Showing Data
- Check browser console for errors
- Verify `/api/clients` returns data
- Check network tab in dev tools

### API Returns 503
- Check `/health` endpoint
- Verify feature_flags is true
- Review server logs

### Features Not Working
- Verify client exists in clients.yaml
- Check ruleset is defined in rulesets.yaml
- Confirm feature is in ruleset's feature list

## 📞 Quick Reference

- **Health Check**: `GET /health`
- **List Clients**: `GET /api/clients`
- **List Rulesets**: `GET /api/rulesets`
- **Check Feature**: `GET /api/clients/{id}/feature/{name}`
- **Create Ruleset**: `POST /api/rulesets`
- **Analyze Code**: `POST /api/analyze` (local only)
- **Kill Switch**: `GET|POST /api/kill-switch`

---

**Dashboard**: https://feature-flagging-qauz0zj1y-dhyan-sonis-projects-905dd53f.vercel.app
**Status**: Production Ready ✅
