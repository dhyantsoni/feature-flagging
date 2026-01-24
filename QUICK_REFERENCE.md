# Quick Reference Card

## Getting Started (Copy-Paste)

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 2. Create Schema
Paste this in Supabase SQL Editor:
```bash
cat supabase_schema.sql
```

### 3. Validate
```bash
python supabase_integration.py
```

### 4. See Examples
```bash
python e2e_workflow.py
```

---

## API Quick Reference

### Projects
```bash
# Create
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"MyProject"}'

# List
curl http://localhost:5000/api/projects

# Get
curl http://localhost:5000/api/projects/{id}
```

### Features
```bash
# Create
curl -X POST http://localhost:5000/api/projects/{id}/features \
  -H "Content-Type: application/json" \
  -d '{"feature_name":"new_feature"}'

# List
curl http://localhost:5000/api/projects/{id}/features

# Get functions for feature
curl http://localhost:5000/api/features/{id}/functions
```

### Clients
```bash
# Register
curl -X POST http://localhost:5000/api/client \
  -H "Content-Type: application/json" \
  -d '{"client_id":"myapp","ruleset":"stable"}'

# List
curl http://localhost:5000/api/clients

# Check feature
curl http://localhost:5000/api/client/{id}/feature/{name}
```

### Rulesets
```bash
# Create
curl -X POST http://localhost:5000/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{"name":"canary","description":"5% rollout"}'

# List
curl http://localhost:5000/api/rulesets

# Update
curl -X PUT http://localhost:5000/api/rulesets/{id} \
  -H "Content-Type: application/json" \
  -d '{"rules":{}}'
```

### Validation
```bash
# Health check
curl http://localhost:5000/health

# Full validation
curl http://localhost:5000/api/validate
```

---

## Python Quick Reference

### Initialize
```python
from supabase_client import SupabaseClient

supabase = SupabaseClient()
```

### Projects
```python
# Create
project = supabase.create_project(
    name="MyProject",
    description="My project"
)

# List
projects = supabase.list_projects()

# Get
project = supabase.get_project(project_id)
```

### Features
```python
# Create
feature = supabase.create_feature(
    project_id=project['id'],
    feature_name="oauth2",
    description="OAuth2 integration"
)

# List
features = supabase.list_features(project['id'])

# Get
feature = supabase.get_feature(project['id'], "oauth2")

# Toggle
supabase.toggle_feature(feature['id'], is_enabled=True)
```

### Functions
```python
# Save
func = supabase.save_function(
    project_id=project['id'],
    function_name="authenticate",
    file_path="auth.py",
    is_feature_flagged=True,
    complexity_score=8
)

# List
functions = supabase.list_functions(project['id'])

# Get
func = supabase.get_function(project['id'], "authenticate")
```

### Mappings
```python
# Map feature to function
supabase.create_function_mapping(
    feature_id=feature['id'],
    function_id=func['id'],
    is_entry_point=True
)

# Get functions for feature
functions = supabase.get_feature_functions(feature['id'])

# Get features for function
features = supabase.get_function_features(func['id'])
```

### Clients
```python
# Register
client = supabase.save_client(
    client_id="mobile_app",
    ruleset_name="stable",
    project_id=project['id']
)

# List
clients = supabase.list_clients(project['id'])

# Get
client = supabase.get_client("mobile_app")
```

### Rulesets
```python
# Create
ruleset = supabase.create_ruleset(
    name="stable",
    description="Stable features only"
)

# List
rulesets = supabase.list_all_rulesets()

# Get
ruleset = supabase.get_ruleset_by_id(ruleset_id)

# Update
supabase.update_ruleset(ruleset_id, {"name": "new_name"})

# Delete
supabase.delete_ruleset(ruleset_id)
```

### Impact Analysis
```python
# Save
impact = supabase.save_impact_analysis(
    feature_id=feature['id'],
    analysis_data={"risk": "medium"},
    total_affected=3,
    unreachable=0,
    need_fallback=1
)

# Get
impact = supabase.get_impact_analysis(feature['id'])
```

---

## Common Patterns

### Register a Project with Analysis
```python
# Create project
project = supabase.create_project(name="MyApp")

# Save functions
funcs = []
for func_name in ["authenticate", "process_payment", "hash_password"]:
    f = supabase.save_function(
        project_id=project['id'],
        function_name=func_name,
        file_path="main.py"
    )
    funcs.append(f)

# Create features
feature = supabase.create_feature(
    project_id=project['id'],
    feature_name="new_auth",
    description="New authentication"
)

# Map functions to feature
for func in funcs[:2]:  # First 2 functions
    supabase.create_function_mapping(
        feature_id=feature['id'],
        function_id=func['id']
    )
```

### Register Client with Ruleset
```python
# Create ruleset
ruleset = supabase.create_ruleset(
    name="canary_release",
    description="Testing with 5% users"
)

# Register client
client = supabase.save_client(
    client_id="mobile_v2",
    ruleset_name=ruleset['name'],
    project_id=project['id'],
    metadata={"platform": "iOS"}
)
```

### Check Feature Status
```python
# Get feature
feature = supabase.get_feature(project['id'], "new_auth")

# Check if enabled
if feature['is_enabled']:
    # Run new code
    pass
else:
    # Run fallback
    pass

# Get affected functions
functions = supabase.get_feature_functions(feature['id'])
print(f"Feature affects {len(functions)} functions")

# Get impact
impact = supabase.get_impact_analysis(feature['id'])
print(f"Risk level: {impact['analysis_data'].get('risk_level')}")
```

### Gradual Rollout
```python
# Canary (5%)
canary = supabase.create_ruleset(
    name="mfa_canary",
    rollout_percentage=5
)

# Beta (25%)
beta = supabase.create_ruleset(
    name="mfa_beta",
    rollout_percentage=25
)

# Production (100%)
prod = supabase.create_ruleset(
    name="mfa_production",
    rollout_percentage=100
)
```

---

## Troubleshooting

### Test Connection
```bash
python -c "from supabase_client import SupabaseClient; SupabaseClient()"
```

### Check Logs
```bash
python app.py 2>&1 | grep -i supabase
```

### Validate System
```bash
python supabase_integration.py
```

### Test Schema
```bash
# In Supabase SQL Editor:
SELECT COUNT(*) FROM projects;
```

---

## Database Schema at a Glance

```
projects
├── functions (project_id)
│   ├── function_mappings (function_id)
│   │   └── features (feature_id)
│   │       ├── impact_analysis
│   │       └── rulesets (project_id)
│   └── dependencies (caller/callee)
├── features (project_id)
│   ├── function_mappings
│   └── impact_analysis
├── function_graphs (project_id)
└── clients (project_id)
```

---

## File Structure

```
feature-flagging/
├── supabase_client.py          # Main Supabase interface
├── supabase_integration.py     # Validation script
├── e2e_workflow.py             # Practical examples
├── app.py                      # Flask backend
├── requirements.txt
├── .env.example                # Configuration template
├── supabase_schema.sql         # Database schema
├── SETUP_CHECKLIST.md          # Step-by-step guide
├── SUPABASE_INTEGRATION.md     # Full documentation
└── INTEGRATION_SUMMARY.md      # What was fixed
```

---

## Documentation Links

| Document | Use Case |
|----------|----------|
| [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md) | Getting started (15 min) |
| [SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md) | Complete reference |
| [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) | What was changed |
| [e2e_workflow.py](e2e_workflow.py) | 5 practical examples |
| This file | Quick lookup |

---

## Environment Variables

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyXxxx...
FLASK_ENV=development
FLASK_DEBUG=False
```

Get these from: https://app.supabase.com → Settings > API

---

## API Response Format

### Success
```json
{
  "success": true,
  "data": { ... } or "project": { ... }
}
```

### Error
```json
{
  "success": false,
  "error": "Description of what went wrong"
}
```

### Validation
```bash
curl http://localhost:5000/api/validate
```

Returns detailed system health check.

---

## Tips & Tricks

- Use `python supabase_integration.py` to test before deploying
- Run `e2e_workflow.py` to understand the system
- Check `/api/validate` if something seems wrong
- All errors are logged - check `python app.py` output
- Use `.env` file - never hardcode secrets
- Test with `curl` before writing frontend code

---

**Estimated Setup Time: 15-20 minutes**
**Total Learning Time: 30-45 minutes**
