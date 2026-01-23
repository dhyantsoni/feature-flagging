# Deployment Guide

## Quick Setup

### 1. Supabase Setup

**Your Credentials:**
- URL: `https://plyatinqbfrcbfltmflo.supabase.co`
- Publishable Key: `sb_publishable_feXbrCzRnn1xVbxN_h5hXQ_bYhzvPFb`
- Secret Key: `sb_secret_pVAWxuhriV05lfA_PFhL0g_gtYnodRl`

**Steps:**
1. Go to [Supabase SQL Editor](https://supabase.com/dashboard/project/plyatinqbfrcbfltmflo/sql)
2. Copy the contents of `supabase_schema.sql`
3. Run the SQL to create all tables and indexes
4. Tables will be created with RLS (Row Level Security) enabled

### 2. Vercel Deployment

**Steps:**
1. Install Vercel CLI (if not installed):
   ```bash
   npm i -g vercel
   ```

2. Deploy to Vercel:
   ```bash
   vercel
   ```

3. Add environment variables in Vercel dashboard:
   - `SUPABASE_URL` = `https://plyatinqbfrcbfltmflo.supabase.co`
   - `SUPABASE_KEY` = `sb_publishable_feXbrCzRnn1xVbxN_h5hXQ_bYhzvPFb`

4. Redeploy:
   ```bash
   vercel --prod
   ```

### 3. Local Development

**Setup:**
```bash
# Create .env file
cat > .env << EOF
SUPABASE_URL=https://plyatinqbfrcbfltmflo.supabase.co
SUPABASE_KEY=sb_publishable_feXbrCzRnn1xVbxN_h5hXQ_bYhzvPFb
EOF

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

**Access:**
- API: http://localhost:5000
- Endpoints: http://localhost:5000/ (lists all endpoints)

## API Documentation

### Core Endpoints

#### Feature Flagging (Original)
- `GET /api/clients` - List all clients
- `GET /api/rulesets` - List all rulesets
- `GET /api/client/<client_id>` - Get client details
- `POST /api/client` - Create new client
- `PUT /api/client/<client_id>/ruleset` - Update client ruleset
- `POST /api/kill-switch` - Toggle global kill switch

#### Projects & Analysis (New)
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/<project_id>` - Get project details
- `POST /api/analyze` - Analyze Python codebase

#### Functions & Features
- `GET /api/projects/<project_id>/functions` - List functions (filterable)
- `GET /api/projects/<project_id>/features` - List features
- `GET /api/features/<feature_id>/functions` - Get feature's functions
- `GET /api/features/<feature_id>/impact` - Get feature impact analysis
- `GET /api/functions/<function_id>/dependencies` - Get function dependencies

### Example Usage

#### 1. Create a Project
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "description": "Feature-flagged application",
    "repository_url": "https://github.com/user/repo"
  }'
```

#### 2. Analyze Codebase
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project_id_from_step_1>",
    "file_path": "/path/to/code.py"
  }'
```

#### 3. Get Function Graph
```bash
curl http://localhost:5000/api/projects/<project_id>/functions
```

#### 4. Get Feature Impact
```bash
curl http://localhost:5000/api/features/<feature_id>/impact
```

## System Architecture

### Components

1. **AST Analyzer** (`enhanced_ast_analyzer.py`)
   - Parses Python code using AST
   - Builds function call graphs with NetworkX
   - Detects feature flags via decorators
   - Identifies shared vs feature-specific helpers
   - Calculates complexity metrics

2. **Supabase Client** (`supabase_client.py`)
   - Database operations
   - CRUD for projects, functions, features
   - Stores call graphs and analysis results

3. **Flask API** (`app.py`)
   - REST API endpoints
   - Integrates AST analysis with Supabase
   - Serves feature flag configurations

### Database Schema

**Tables:**
- `projects` - Analyzed codebases
- `function_graphs` - Call graph data
- `functions` - Individual function metadata
- `features` - Feature flag definitions
- `function_mappings` - Feature-to-function relationships
- `dependencies` - Function call relationships
- `impact_analysis` - Cached impact reports
- `clients` - Client configurations
- `rulesets` - Feature flag rulesets

### Key Features

✅ **AST-Based Analysis**
- Static analysis of Python code
- No code execution required
- Extracts function definitions and calls

✅ **Smart Helper Detection**
- Identifies helper functions
- Distinguishes shared helpers (used by multiple features)
- Prevents breaking other features when disabling

✅ **Impact Analysis**
- Shows functions that can be disabled with feature
- Shows functions that must remain active (shared)
- Lists functions needing fallback logic

✅ **Feature Flagging**
- Client-based configuration
- Ruleset system for different environments
- Global kill switch support

## Troubleshooting

**Supabase Connection Issues:**
```bash
# Test connection
python -c "from supabase_client import SupabaseClient; c = SupabaseClient(); print('Connected!')"
```

**Missing Dependencies:**
```bash
pip install -r requirements.txt
```

**Vercel Build Errors:**
- Ensure `vercel.json` is present
- Check environment variables are set
- Review build logs in Vercel dashboard

## Next Steps

1. Run SQL schema in Supabase
2. Deploy to Vercel
3. Create a project via API
4. Analyze your first codebase
5. View function graphs and impact analysis
