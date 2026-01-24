# Supabase Integration - Setup Checklist

Follow these steps to get Supabase integration working in your local development environment.

## ✅ Step 1: Get Supabase Credentials (5 minutes)

- [ ] Go to https://app.supabase.com
- [ ] Click "New Project"
- [ ] Choose a name (e.g., "feature-flagging-dev")
- [ ] Choose a region
- [ ] Set a secure database password
- [ ] Click "Create new project" and wait for it to finish
- [ ] Go to **Settings > API**
- [ ] Copy the **Project URL** (looks like: `https://xxxxx.supabase.co`)
- [ ] Copy the **anon public** key (long string)

## ✅ Step 2: Create Environment File (2 minutes)

```bash
# In the root directory of feature-flagging project
cp .env.example .env
```

Edit `.env`:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_anon_key_here
FLASK_ENV=development
FLASK_DEBUG=False
```

## ✅ Step 3: Create Database Schema (2 minutes)

1. In Supabase dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Open the file [supabase_schema.sql](supabase_schema.sql) 
4. Copy the entire contents
5. Paste into the Supabase SQL editor
6. Click **"Run"** button
7. Wait for all statements to complete (check for green checkmarks)

You should see:
```
✓ Created tables (9)
✓ Created indexes (11)
✓ Created triggers (4)
✓ Enabled RLS
✓ Created policies
```

## ✅ Step 4: Validate Integration (2 minutes)

Run the validation script:

```bash
python supabase_integration.py
```

**Expected output:**
```
============================================================
SUPABASE INTEGRATION VALIDATION REPORT
============================================================

✅ All checks passed!

Summary: 4 passed, 0 failed
============================================================
```

**If validation fails:**
- Check that `.env` file exists and has correct values
- Verify Supabase project is running (check dashboard)
- Make sure schema SQL was fully executed
- Check internet connection

## ✅ Step 5: Create Demo Data (1 minute)

Load example projects and features:

```bash
python supabase_integration.py --create-demo
```

Or see a complete end-to-end workflow:

```bash
python e2e_workflow.py
```

## ✅ Step 6: Start the Application

```bash
python app.py
```

Open browser to: http://localhost:5000

Test the integration:
- Visit http://localhost:5000/health (should show Supabase configured)
- Visit http://localhost:5000/api/validate (detailed validation)
- Visit http://localhost:5000/api/projects (should show demo projects if created)

## ✅ Step 7: Test API Endpoints

Create a new project via API:

```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Test Project",
    "description": "Testing Supabase integration",
    "repository_url": "https://github.com/example/test"
  }'
```

Should return:
```json
{
  "success": true,
  "project": {
    "id": "uuid-...",
    "name": "My Test Project",
    "created_at": "2024-...",
    ...
  }
}
```

## What's Working Now

✅ **Supabase Connection** - Verified and error-handled
✅ **Database Schema** - 9 tables with relationships
✅ **Project Management** - Create/read/list projects
✅ **Function Analysis** - Store and query function definitions
✅ **Feature Flags** - Create and manage features
✅ **Rulesets** - Create and assign rulesets to clients
✅ **Impact Analysis** - Store feature dependency analysis
✅ **Error Handling** - Comprehensive logging and error messages
✅ **API Validation** - `/api/validate` endpoint for debugging

## Practical Usage

### From Python
```python
from supabase_client import SupabaseClient

supabase = SupabaseClient()

# Create a project
project = supabase.create_project(
    name="MyProject",
    description="My awesome project"
)

# List projects
projects = supabase.list_projects()

# Create a feature
feature = supabase.create_feature(
    project_id=project['id'],
    feature_name="new_payment_system",
    description="New payment processing"
)
```

### From API
```bash
# Create project
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"MyProject"}'

# List projects
curl http://localhost:5000/api/projects

# List features
curl http://localhost:5000/api/projects/{project_id}/features
```

## Troubleshooting

### Problem: "SUPABASE_URL and SUPABASE_KEY environment variables are required"

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Check it has values
cat .env | grep SUPABASE

# Make sure no extra whitespace
# SUPABASE_URL=https://your-url.supabase.co  (correct)
# SUPABASE_URL = https://your-url.supabase.co (wrong - extra spaces)
```

### Problem: "Table 'projects' does not exist"

**Solution:**
1. Re-run the SQL schema in Supabase SQL Editor
2. Make sure ALL statements completed (check for ✓ marks)
3. Wait 10 seconds and try again (sometimes takes time to apply)

### Problem: "Authentication failed"

**Solution:**
1. Check SUPABASE_KEY is correct (copy-paste from dashboard again)
2. Make sure you used the `anon public` key, NOT the service role key
3. Verify project is active in Supabase dashboard

### Problem: Connection timeout

**Solution:**
1. Check SUPABASE_URL has no typos
2. Ping the URL: `curl -I https://your-url.supabase.co` 
3. Check internet connection
4. Try creating new Supabase project (current one might be down)

## Files Created/Modified

- ✅ `supabase_client.py` - All methods now have proper error handling
- ✅ `supabase_integration.py` - Validation script
- ✅ `e2e_workflow.py` - Practical examples
- ✅ `SUPABASE_INTEGRATION.md` - Complete documentation
- ✅ `.env.example` - Configuration template
- ✅ `supabase_schema.sql` - Database schema (already existed)
- ✅ `app.py` - Added `/api/validate` endpoint and better initialization

## Next Steps

1. ✅ Complete this checklist
2. ✅ Read [SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md) for detailed documentation
3. ✅ Look at [e2e_workflow.py](e2e_workflow.py) for practical usage patterns
4. ✅ Build your feature flagging logic using the system
5. ✅ Deploy to Vercel with Supabase credentials as environment variables

## Need Help?

- Review error messages in logs (app prints detailed error info)
- Check validation: `python supabase_integration.py`
- See practical examples: `python e2e_workflow.py`
- Read detailed docs: [SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md)

---

**Estimated Total Time: 15-20 minutes**
