# 🚀 Quick Start - Feature Flagging Platform

## 5-Minute Setup

### Prerequisites
- Python 3.8+
- Supabase account (free: supabase.com)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Supabase
1. Create a free project at https://supabase.com
2. Go to Settings → API
3. Copy your **Project URL** and **anon (public) key**
4. Create `.env` file:
```bash
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
```

### Step 3: Create Database Tables
1. Go to SQL Editor in Supabase dashboard
2. Copy the SQL schema from `supabase_schema.sql`
3. Paste and execute

### Step 4: Run Locally
```bash
python app.py
```
Visit: http://localhost:5000

## 🎯 First Steps

### 1. Create a Project
- Click "+ New Project"
- Enter project name and repository URL
- Click Create

### 2. Analyze Your Code
- Select your project
- Go to "Overview" tab
- Click "🔍 Analyze Project"
- Enter path to Python project (e.g., `/home/user/myproject`)

### 3. Create a Ruleset
- Click "⚙️ Rulesets"
- Go to "Create Ruleset" tab
- Enter name and add features
- Click "Create Ruleset"

### 4. Register a Client
- Click "+ New Client"
- Enter client ID (e.g., `client_acme`)
- Select a ruleset
- Choose tier (free/pro/enterprise)
- Click Create

### 5. View Call Graph
- Select your project
- Go to "Call Graph" tab
- Interactive visualization appears
- Drag nodes to explore

## 🎨 UI Features

### Dashboard
- **Project Selector**: Top left dropdown
- **Rulesets**: ⚙️ button in header
- **Kill Switch**: Toggle in top right
- **Statistics**: Main welcome screen

### Sidebars
- **Left**: Client search and list
- **Main**: Project details or client info

### Modals
- Click any "+ New" button to create
- Click "Change Ruleset" to update
- Close by clicking outside

## 🔧 API Examples

### Create Project
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "MyApp", "repository_url": "https://github.com/user/app"}'
```

### Create Ruleset
```bash
curl -X POST http://localhost:5000/api/rulesets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "premium",
    "features": ["feature1", "feature2"],
    "rollout_percentage": 100
  }'
```

### Register Client
```bash
curl -X POST http://localhost:5000/api/client \
  -H "Content-Type: application/json" \
  -d '{"client_id": "acme", "ruleset": "premium"}'
```

## 🚀 Deploy to Vercel

### Prerequisites
- GitHub account
- Vercel account
- Supabase project

### Steps
1. Push to GitHub
2. Go to https://vercel.com
3. Import project
4. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
5. Deploy!

**Or use Vercel CLI:**
```bash
npm i -g vercel
vercel login
vercel --prod
```

## 🎨 Theme Customization

All colors are in `static/css/style.css`:

```css
:root {
  --primary-pink: #ff69b4;      /* Main color */
  --light-pink: #ffb6d9;         /* Light accents */
  --pale-pink: #ffe4f0;          /* Backgrounds */
  --white: #ffffff;              /* Panels */
}
```

Change these to customize the theme!

## 📊 What You Can Do

✅ Analyze Python projects
✅ Generate call graphs
✅ Create feature rulesets
✅ Manage clients
✅ Enable/disable features globally
✅ View function dependencies
✅ Track complexity
✅ Identify shared helpers
✅ Export visualizations

## 🆘 Troubleshooting

### Port 5000 in use?
```bash
python app.py --port 8000
```

### Supabase connection fails?
- Check `.env` file exists
- Verify `SUPABASE_URL` and `SUPABASE_KEY`
- Ensure Supabase project is active

### Analysis fails?
- Check Python files are syntactically correct
- Verify directory path is absolute
- Check file permissions

### Frontend won't load?
- Clear browser cache
- Check console for errors (F12)
- Verify Flask is running

## 📚 Full Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Full setup guide
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Technical details
- [README.md](README.md) - Project overview

## 🎓 Learning Path

1. **Basics** - Set up and run locally
2. **Core** - Create projects and analyze code
3. **Advanced** - Build complex rulesets
4. **Expert** - Deploy and scale on Vercel

## 🆘 Getting Help

### Common Issues

**Issue: "Supabase not configured"**
- Solution: Add SUPABASE_URL and SUPABASE_KEY to .env

**Issue: Analysis takes too long**
- Solution: Smaller projects analyze faster; exclude test files

**Issue: Graph visualization is empty**
- Solution: Run analysis first; wait for completion

## 🚀 Next Steps

1. ✅ Complete local setup
2. ✅ Analyze your first project
3. ✅ Create a ruleset
4. ✅ Register a client
5. ✅ Deploy to Vercel
6. ✅ Share with team

---

**Happy feature flagging! 🚩**

For more help, check the [DEPLOYMENT.md](DEPLOYMENT.md) guide.
