# 🚀 Feature Flagging System - Deployment Guide

## Overview

This is a comprehensive feature flagging system with:
- **Supabase Integration**: Store and manage feature flags, clients, and rulesets
- **AST Analysis**: Analyze Python projects to generate call graphs
- **Beautiful Frontend**: Pink and white themed dashboard with Vercel deployment ready
- **Ruleset Builder**: Create and manage feature rulesets from the UI
- **Call Graph Visualization**: Interactive D3.js-based visualization

## Prerequisites

1. **Node.js** (for Vercel CLI)
2. **Python 3.8+**
3. **Supabase Account** (free tier available at https://supabase.com)

## Local Development Setup

### 1. Clone and Install Dependencies

```bash
cd feature-flagging
pip install -r requirements.txt
```

### 2. Configure Supabase

1. Create a free account at https://supabase.com
2. Create a new project
3. Get your Supabase URL and API Key from Settings → API
4. Create a `.env` file:

```bash
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```

### 3. Create Supabase Tables

Run this SQL in your Supabase SQL Editor:

```sql
-- Projects table
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  repository_url TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Functions table
CREATE TABLE functions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id),
  function_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  is_feature_flagged BOOLEAN DEFAULT FALSE,
  is_helper BOOLEAN DEFAULT FALSE,
  is_shared_helper BOOLEAN DEFAULT FALSE,
  line_number INTEGER,
  complexity_score INTEGER DEFAULT 0,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, function_name)
);

-- Rulesets table
CREATE TABLE rulesets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  features JSONB DEFAULT '[]',
  baseline_ruleset TEXT,
  rollout_percentage INTEGER DEFAULT 100,
  metadata JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Clients table
CREATE TABLE clients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id TEXT UNIQUE NOT NULL,
  ruleset_name TEXT REFERENCES rulesets(name),
  project_id UUID REFERENCES projects(id),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Function graphs table
CREATE TABLE function_graphs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id),
  file_path TEXT,
  graph_data JSONB NOT NULL,
  total_functions INTEGER,
  total_calls INTEGER,
  metadata JSONB DEFAULT '{}',
  analysis_timestamp TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, file_path)
);

-- Features table
CREATE TABLE features (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID REFERENCES projects(id),
  feature_name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(project_id, feature_name)
);

-- Function mappings table
CREATE TABLE function_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  feature_id UUID REFERENCES features(id),
  function_id UUID REFERENCES functions(id),
  is_entry_point BOOLEAN DEFAULT FALSE,
  dependency_type TEXT, -- 'direct', 'downstream', 'helper'
  created_at TIMESTAMP DEFAULT NOW()
);

-- Impact analysis table
CREATE TABLE impact_analysis (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  feature_id UUID REFERENCES features(id),
  analysis_data JSONB NOT NULL,
  total_affected_functions INTEGER,
  functions_unreachable INTEGER,
  functions_need_fallback INTEGER,
  analyzed_at TIMESTAMP DEFAULT NOW()
);
```

### 4. Run Locally

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
python app.py
```

Visit http://localhost:5000

## Features

### 🎨 Frontend (Pink & White Theme)

- **Project Management**: Create and manage analysis projects
- **Ruleset Builder**: Visually create and manage rulesets with features
- **Client Management**: Assign clients to rulesets
- **AST Visualization**: Interactive call graph visualization
- **Kill Switch**: Global feature flag control
- **Real-time Updates**: Live statistics and status

### 🔧 Backend API

#### Project Endpoints
- `POST /api/projects` - Create project
- `GET /api/projects` - List projects
- `GET /api/projects/<id>` - Get project details
- `POST /api/projects/<id>/analyze-full` - Analyze full project
- `GET /api/projects/<id>/graph/data` - Get graph for visualization
- `GET /api/projects/<id>/functions` - Get all functions in project

#### Ruleset Endpoints
- `POST /api/rulesets` - Create ruleset
- `GET /api/rulesets` - List all rulesets
- `GET /api/rulesets/<id>` - Get ruleset details
- `PUT /api/rulesets/<id>` - Update ruleset
- `DELETE /api/rulesets/<id>` - Delete ruleset

#### Client Endpoints
- `POST /api/client` - Create client
- `GET /api/clients` - List all clients
- `GET /api/client/<id>` - Get client details
- `PUT /api/client/<id>/ruleset` - Update client ruleset

#### Feature Control
- `GET /api/kill-switch` - Get kill switch status
- `POST /api/kill-switch` - Toggle kill switch

## Deployment to Vercel

### Prerequisites
1. Install Vercel CLI: `npm i -g vercel`
2. Have a GitHub account
3. Supabase project set up

### Steps

1. **Login to Vercel**
```bash
vercel login
```

2. **Set Environment Variables**
```bash
vercel env add SUPABASE_URL
vercel env add SUPABASE_KEY
```

3. **Deploy**
```bash
vercel --prod
```

Or push to GitHub and connect your repo to Vercel for automatic deployments.

### Vercel Configuration

The `vercel.json` file is pre-configured for Python apps with:
- Python runtime via `@vercel/python`
- All routes routed to Flask app
- Environment variables for Supabase

## Usage Examples

### Create a Project

```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My App",
    "description": "My awesome application",
    "repository_url": "https://github.com/user/my-app"
  }'
```

### Create a Ruleset

```bash
curl -X POST http://localhost:5000/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "premium_tier",
    "description": "Features for premium users",
    "features": ["advanced_analytics", "custom_integrations"],
    "rollout_percentage": 100
  }'
```

### Analyze a Project

```bash
curl -X POST http://localhost:5000/api/projects/{project_id}/analyze-full \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/path/to/python/project"
  }'
```

## Architecture

### Frontend
- **HTML/CSS/JavaScript**: Vanilla JS with D3.js for visualization
- **Pink & White Theme**: Modern, accessible design
- **Responsive**: Works on desktop and mobile
- **Modal-based**: Clean UX for create/edit operations

### Backend
- **Flask**: Lightweight Python framework
- **Supabase**: PostgreSQL database with automatic APIs
- **NetworkX**: Graph analysis and traversal
- **AST Analysis**: Python abstract syntax tree parsing
- **Matplotlib**: Graph visualization and export

## Troubleshooting

### Supabase Connection Issues
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are correctly set
- Verify your Supabase project is active
- Check that tables are created with correct schema

### Analysis Fails
- Ensure Python files are syntactically correct
- Check file permissions on the directory
- Verify the directory path exists

### Vercel Deployment Issues
- Check logs: `vercel logs`
- Ensure `requirements.txt` has all dependencies
- Verify environment variables are set in Vercel dashboard

## Development

### Adding New Features

1. **Backend API**: Add endpoints in `app.py`
2. **Database**: Update schema and add Supabase client methods
3. **Frontend**: Add UI in `dashboard.html` and handlers in `dashboard.js`

### Customization

- **Theme Colors**: Edit `static/css/style.css` (search for `--primary-pink`)
- **Supabase Schema**: Modify tables in Supabase dashboard
- **API Responses**: Update Flask route handlers

## Support & License

This project is provided as-is for feature flagging and AST analysis use cases.

## Next Steps

1. **Set up Supabase** with the provided SQL schema
2. **Deploy to Vercel** for production access
3. **Create your first project** and analyze it
4. **Build rulesets** and assign clients
5. **Monitor features** via the dashboard

---

**Happy feature flagging! 🚩**
