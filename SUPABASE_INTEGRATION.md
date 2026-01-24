# Supabase Integration Guide

## Overview

This feature flagging system uses **Supabase (PostgreSQL)** for persistent storage of:
- Projects and code analysis metadata
- Function definitions and call graphs
- Feature flag definitions and mappings
- Client configurations and ruleset assignments
- Impact analysis and dependency tracking

## Quick Start

### 1. Set Up Supabase

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Create a new project
3. Go to **Settings > API**
4. Copy your **Project URL** and **anon public key**

### 2. Configure Environment

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:

```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_key_here
FLASK_ENV=development
FLASK_DEBUG=False
```

### 3. Create Database Schema

Copy and paste the contents of `supabase_schema.sql` into your Supabase SQL Editor:

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy the contents of `supabase_schema.sql`
4. Paste into the editor
5. Click **Run**

This creates 9 tables with proper relationships and indexes.

### 4. Validate Integration

Run the validation script:

```bash
python supabase_integration.py
```

Expected output:
```
============================================================
SUPABASE INTEGRATION VALIDATION REPORT
============================================================

✅ All checks passed!

Summary: 4 passed, 0 failed
============================================================
```

### 5. (Optional) Load Demo Data

Create sample projects, features, and clients:

```bash
python supabase_integration.py --create-demo
```

Or run the end-to-end workflow example:

```bash
python e2e_workflow.py
```

## System Architecture

### Database Tables

#### `projects`
Stores project metadata for code analysis
```sql
id, name, description, repository_url, created_at, metadata
```

#### `functions`
Individual function definitions from analyzed code
```sql
id, project_id, function_name, file_path, is_feature_flagged,
is_helper, is_shared_helper, line_number, complexity_score
```

#### `features`
Feature flag definitions
```sql
id, project_id, feature_name, description, is_enabled, created_at
```

#### `function_mappings`
Maps features to the functions they affect
```sql
id, feature_id, function_id, is_entry_point, dependency_type
```

#### `dependencies`
Function call relationships (who calls whom)
```sql
id, project_id, caller_function_id, callee_function_id, call_count
```

#### `impact_analysis`
Cached analysis of feature impact
```sql
id, feature_id, analysis_data, total_affected_functions,
functions_unreachable, functions_need_fallback
```

#### `clients`
Registered client/service configurations
```sql
id, client_id, project_id, ruleset_name, metadata, created_at
```

#### `rulesets`
Feature flag rulesets (which features enabled per client)
```sql
id, project_id, ruleset_name, description, rules, is_active
```

#### `function_graphs`
Complete AST analysis call graphs
```sql
id, project_id, graph_data (JSON), file_path, total_functions, total_calls
```

## API Endpoints

### Health & Validation

```bash
# Health check
GET /health

# Detailed validation
GET /api/validate
```

### Projects

```bash
# List projects
GET /api/projects

# Create project
POST /api/projects
{
  "name": "MyProject",
  "description": "...",
  "repository_url": "https://..."
}

# Get project
GET /api/projects/<project_id>

# Analyze full codebase
POST /api/projects/<project_id>/analyze-full
{
  "directory": "/path/to/code"
}
```

### Features

```bash
# List features in project
GET /api/projects/<project_id>/features

# Create feature
POST /api/projects/<project_id>/features
{
  "feature_name": "new_oauth",
  "description": "OAuth2 integration"
}

# Get feature functions
GET /api/features/<feature_id>/functions

# Get feature impact
GET /api/features/<feature_id>/impact
```

### Clients

```bash
# List clients
GET /api/clients

# Register client
POST /api/client
{
  "client_id": "mobile_app",
  "ruleset": "stable_features"
}

# Check if feature enabled for client
GET /api/client/<client_id>/feature/<feature_name>

# Change client ruleset
PUT /api/client/<client_id>/ruleset
{
  "ruleset": "beta_features"
}
```

### Rulesets

```bash
# List rulesets
GET /api/rulesets

# Create ruleset
POST /api/rulesets
{
  "name": "canary_release",
  "description": "5% rollout"
}

# Get ruleset
GET /api/rulesets/<ruleset_id>

# Update ruleset
PUT /api/rulesets/<ruleset_id>

# Delete ruleset
DELETE /api/rulesets/<ruleset_id>
```

### Kill Switch

```bash
# Check status
GET /api/kill-switch

# Activate/deactivate
POST /api/kill-switch
{
  "activate": true
}
```

## Practical Usage Examples

### Example 1: Register a New Project

```python
from supabase_client import SupabaseClient

supabase = SupabaseClient()

# Create project
project = supabase.create_project(
    name="UserService",
    description="Authentication microservice",
    repository_url="https://github.com/company/user-service"
)

print(f"Project ID: {project['id']}")
```

### Example 2: Create Feature and Map Functions

```python
# Create feature
feature = supabase.create_feature(
    project_id=project['id'],
    feature_name="oauth2_integration",
    description="New OAuth2 provider support"
)

# Get existing function
function = supabase.get_function(
    project_id=project['id'],
    function_name="authenticate_user"
)

# Map feature to function
mapping = supabase.create_function_mapping(
    feature_id=feature['id'],
    function_id=function['id'],
    is_entry_point=True  # This is the main feature function
)
```

### Example 3: Register Client and Assign Ruleset

```python
# Create ruleset
ruleset = supabase.create_ruleset(
    name="stable",
    description="Only stable features",
    features=["oauth2_integration"]
)

# Register client
client = supabase.save_client(
    client_id="web_app_v2",
    ruleset_name="stable",
    project_id=project['id']
)

print(f"Registered client: {client['client_id']}")
```

### Example 4: Query Feature Status

```python
# Get all features for project
features = supabase.list_features(project['id'])

# Get functions affected by feature
feature = features[0]
functions = supabase.get_feature_functions(feature['id'])

print(f"Feature '{feature['feature_name']}' affects {len(functions)} functions")
```

### Example 5: Analyze Feature Impact

```python
# Save impact analysis
impact = supabase.save_impact_analysis(
    feature_id=feature['id'],
    analysis_data={
        "complexity_increase": 0.15,
        "risky_patterns": ["unhandled_exception"]
    },
    total_affected=3,
    unreachable=0,
    need_fallback=1
)

# Retrieve impact
latest_impact = supabase.get_impact_analysis(feature['id'])
print(f"Affected: {latest_impact['total_affected_functions']}")
```

## Error Handling

All Supabase methods include proper error handling with logging:

```python
import logging

logger = logging.getLogger(__name__)

try:
    project = supabase.create_project(name="Test")
except Exception as e:
    logger.error(f"Failed to create project: {e}")
    # Exception is re-raised for caller to handle
    raise
```

Log levels:
- `INFO`: Successful operations (project created, feature updated, etc.)
- `WARNING`: Configuration issues (Supabase not configured)
- `ERROR`: Operation failures (table not found, connection error, etc.)

## Testing the Integration

### 1. Unit Tests

Test individual Supabase operations:

```bash
python -m pytest tests/test_supabase.py -v
```

### 2. Integration Tests

Test complete workflows:

```bash
python e2e_workflow.py
```

### 3. API Tests

Test HTTP endpoints:

```bash
# Validate system
curl http://localhost:5000/api/validate

# List projects
curl http://localhost:5000/api/projects

# Health check
curl http://localhost:5000/health
```

## Troubleshooting

### Issue: "SUPABASE_URL and SUPABASE_KEY environment variables are required"

**Solution**: Make sure your `.env` file is in the root directory and has correct values:
```bash
cat .env | grep SUPABASE
```

### Issue: "Table 'projects' does not exist"

**Solution**: Run the schema creation SQL in your Supabase dashboard:
1. Go to SQL Editor
2. Run contents of `supabase_schema.sql`

### Issue: "Permission denied" errors

**Solution**: Ensure your Supabase anon key has proper permissions. In Supabase dashboard:
1. Go to Authentication > Policies
2. Verify "Allow read for anon" and authenticated policies are set

### Issue: Connection timeout

**Solution**: 
1. Check SUPABASE_URL is correct (should start with `https://`)
2. Verify network connection
3. Check Supabase project is running (go to dashboard)

## Performance Considerations

- The schema includes indexes on all foreign key relationships
- Queries are optimized for common access patterns (feature lookups, client queries)
- JSON columns (graph_data, metadata) support filtering via JSONB operators
- Row-level security policies can be customized for multi-tenant deployments

## Security Notes

- The schema enables Row Level Security (RLS) for all tables
- Default policies allow authenticated and public read access
- Adjust RLS policies based on your authentication model
- The `anon` key is suitable for public APIs; use service role key for admin operations only
- Never commit real API keys to version control (use `.env` file)

## Next Steps

1. ✅ Set up Supabase project
2. ✅ Create database schema
3. ✅ Validate integration with `python supabase_integration.py`
4. ✅ Run `python e2e_workflow.py` to see practical examples
5. ✅ Test API endpoints with your client application
6. ✅ Deploy to production with environment variables

## References

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL JSON Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
