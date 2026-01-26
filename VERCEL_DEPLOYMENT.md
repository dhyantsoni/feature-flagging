# Vercel Deployment Guide

## Pre-Deployment Checklist

### ✅ System Setup
- [x] Vercel CLI installed (`vercel --version`: 50.5.0)
- [x] app.py syntax verified
- [x] requirements.txt complete
- [x] vercel.json configured
- [x] .vercelignore optimized

### ✅ Configuration
- [x] SUPABASE_URL environment variable needed
- [x] SUPABASE_KEY environment variable needed
- [x] FLASK_ENV set to production
- [x] FLASK_DEBUG set to False

### ✅ Code Quality
- [x] No import errors
- [x] Error handling in place
- [x] Logging configured
- [x] CORS enabled

---

## Step 1: Login to Vercel

```bash
vercel login
```

This will open a browser window to authenticate with your Vercel account.

---

## Step 2: Add Environment Variables to Vercel

Go to https://vercel.com/dashboard and:

1. Select your project (or create new one)
2. Go to **Settings > Environment Variables**
3. Add these variables:

```
SUPABASE_URL = https://your-project-id.supabase.co
SUPABASE_KEY = your_anon_key_here
FLASK_ENV = production
FLASK_DEBUG = False
```

**Get these values from:**
- Supabase: https://app.supabase.com → Settings > API

---

## Step 3: Deploy

### Option A: Deploy to Production (Recommended)

```bash
vercel --prod
```

This will:
1. Build your app
2. Deploy to production domain
3. Show live URL
4. Set up CI/CD for future pushes

### Option B: Deploy to Preview

```bash
vercel
```

This creates a temporary preview URL for testing before production.

---

## Step 4: Verify Deployment

After deployment completes, visit your URL:

```bash
# Test health check
curl https://your-vercel-url.vercel.app/health

# Test validation
curl https://your-vercel-url.vercel.app/api/validate

# Test projects endpoint
curl https://your-vercel-url.vercel.app/api/projects
```

Expected response:
```json
{
  "status": "healthy",
  "supabase": {
    "configured": true,
    "error": null
  },
  ...
}
```

---

## Common Issues & Solutions

### Issue: "Supabase not configured"

**Cause:** Environment variables not set in Vercel

**Solution:**
1. Go to Vercel dashboard
2. Select your project
3. Settings > Environment Variables
4. Add SUPABASE_URL and SUPABASE_KEY
5. Redeploy: `vercel --prod`

### Issue: "Module not found" errors

**Cause:** Missing dependencies in requirements.txt

**Solution:**
```bash
# Add missing package to requirements.txt
pip3 freeze | grep package_name >> requirements.txt
# Then redeploy
vercel --prod
```

### Issue: Build fails with timeout

**Cause:** Large dependencies or slow build

**Solution:**
- Verify all dependencies are necessary
- Check vercel.json maxLambdaSize (currently 50mb)
- Check network connection
- Try again with more verbose output: `vercel --prod --debug`

### Issue: 502 Bad Gateway

**Cause:** App crashed or environment variables not loaded

**Solution:**
1. Check environment variables are set
2. Check Supabase project is active
3. Check logs: `vercel logs https://your-url.vercel.app`
4. Test locally: `python3 app.py`

---

## Post-Deployment

### 1. Monitor Logs

```bash
vercel logs https://your-deployment-url.vercel.app --follow
```

### 2. Set Up Custom Domain

1. Go to Vercel dashboard
2. Select project
3. Settings > Domains
4. Add your custom domain
5. Follow DNS configuration instructions

### 3. Configure CI/CD

By default, Vercel automatically deploys on git push to main branch.

To disable auto-deploy:
- Go to Project Settings
- Git > Production Branch
- Set to manual or different branch

### 4. Rollback if Needed

```bash
# View deployment history
vercel list

# Rollback to previous version
vercel rollback <deployment-url>
```

---

## Useful Commands

```bash
# Deploy to production
vercel --prod

# Deploy to preview
vercel

# View current deployments
vercel list

# View deployment logs
vercel logs https://your-url.vercel.app

# Check build status
vercel inspect https://your-url.vercel.app

# Remove a deployment
vercel rm <deployment-url>

# View environment variables
vercel env list

# Pull Vercel settings locally
vercel pull

# Deploy without git push
vercel --prod --force
```

---

## Environment Variables Configuration

### Required Variables

These MUST be set in Vercel dashboard:

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJxxx...
FLASK_ENV=production
FLASK_DEBUG=False
```

### Optional Variables

```env
# For debugging (development only)
FLASK_ENV=development
FLASK_DEBUG=True

# For specific features
LOG_LEVEL=INFO
```

---

## Performance Optimization

### Current Configuration

```json
{
  "maxLambdaSize": "50mb",
  "runtime": "python3.11"
}
```

### Optimization Tips

1. **Reduce bundle size:**
   - Remove unused imports
   - Use CDN for static files
   - Minimize dependencies

2. **Enable caching:**
   - Static files cache for 1 year
   - API responses cache where appropriate

3. **Monitor performance:**
   - Use Vercel Analytics
   - Check deployment logs
   - Monitor Supabase usage

---

## Security Checklist

- [x] Never commit .env file
- [x] Use Vercel environment variables for secrets
- [x] Enable CORS only for trusted origins (if needed)
- [x] Use HTTPS (automatic on Vercel)
- [x] Keep dependencies updated
- [x] Validate all user input
- [x] Use SUPABASE_KEY (anon key), not SERVICE_ROLE_KEY

---

## Next Steps

1. ✅ Ensure Vercel CLI is installed
2. ✅ Login to Vercel: `vercel login`
3. ✅ Set environment variables in Vercel dashboard
4. ✅ Deploy: `vercel --prod`
5. ✅ Verify: Test `/health` and `/api/validate` endpoints
6. ✅ Monitor: Check logs for any errors
7. ✅ Configure: Set up custom domain (optional)

---

## Deployment Status

- [x] Vercel CLI: **Installed** (v50.5.0)
- [x] App code: **Verified** (syntax OK)
- [x] Configuration: **Ready** (vercel.json updated)
- [x] Dependencies: **Complete** (requirements.txt)
- [x] Build script: **Configured** (pip install)
- [x] Environment setup: **Documented** (this guide)

**Ready to deploy!** Run: `vercel login && vercel --prod`

---

## Support

For issues:
1. Check logs: `vercel logs <your-url>`
2. Review [DEPLOYMENT.md](DEPLOYMENT.md)
3. Check [SUPABASE_INTEGRATION.md](SUPABASE_INTEGRATION.md)
4. Vercel docs: https://vercel.com/docs
