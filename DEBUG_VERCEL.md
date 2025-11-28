# Debugging Vercel Function Crash

## Current Status
✅ Deployment succeeded
❌ Function crashes when invoked (500 error)

## Step 1: Check Function Logs

1. Go to https://vercel.com/dashboard
2. Click on your project
3. Click on the deployment (Status: Ready)
4. Click on **"Functions"** tab
5. Click on the function (api/index.py)
6. View the **Runtime Logs**

**This will show you the exact error!**

## Step 2: Check Environment Variables

Make sure `EMAIL_PASSWORD` is set:

1. Go to Project Settings
2. Environment Variables
3. Verify `EMAIL_PASSWORD` exists

## Likely Issues & Solutions

### Issue 1: Missing Environment Variable

**Error in logs might be:**
```
ValidationError: 1 validation error for Settings
email_password
  Field required
```

**Solution:**
```bash
# Add the environment variable
vercel env add EMAIL_PASSWORD

# Then redeploy
vercel --prod
```

### Issue 2: Import Error

**Error in logs might be:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:** The pyproject.toml has all dependencies. This shouldn't happen.

### Issue 3: Template Not Found

**Error in logs might be:**
```
EmailTemplateNotFoundError: Email template not found
```

**Solution:** Verify email_template.html is in the repo and not ignored.

## Quick Fix Commands

### Option 1: Using Vercel CLI

```bash
# View live logs
vercel logs https://emailservice-wine.vercel.app --follow

# Or
vercel logs --follow
```

### Option 2: Check via Dashboard

1. Open https://vercel.com/asklenas-projects/emailservice
2. Go to latest deployment
3. Click "Functions" tab
4. Click on the function
5. View "Runtime Logs"

## Most Likely Solution

Based on the error, the most common issue is **missing EMAIL_PASSWORD**.

**Fix it now:**

1. Go to: https://vercel.com/asklenas-projects/emailservice/settings/environment-variables

2. Add new variable:
   - Name: `EMAIL_PASSWORD`
   - Value: `mwoy vurr ymmq bwhr`
   - Environments: ✅ Production ✅ Preview ✅ Development

3. Redeploy:
   ```bash
   vercel --prod
   ```

## Alternative: Make EMAIL_PASSWORD Optional (Quick Test)

If you want to test without email functionality first, we can make it optional.

Let me know if you want me to create a version that works without EMAIL_PASSWORD set, just to verify everything else is working.
