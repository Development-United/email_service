# Vercel Deployment Guide

Complete guide to deploy the Email Service API to Vercel.

## Important Considerations

**Vercel Limitations:**
- Serverless function timeout: 10 seconds (Hobby), 60 seconds (Pro)
- No persistent state between requests
- Cold starts may affect first request performance
- Rate limiting uses in-memory storage (resets between cold starts)

**Best Practices:**
- Keep SMTP timeout reasonable (10-30 seconds)
- Monitor function execution time
- Consider upgrading to Pro for 60-second timeout if needed

## Prerequisites

1. **Vercel Account**: Sign up at https://vercel.com
2. **Vercel CLI**: Install globally
   ```bash
   npm install -g vercel
   ```
3. **Git Repository**: Your code should be in a Git repository (GitHub, GitLab, or Bitbucket)
4. **Gmail App Password**: If using Gmail SMTP

## Step-by-Step Deployment

### Step 1: Prepare Your Project

1. **Ensure all files are committed:**
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   ```

2. **Verify required files exist:**
   - ✓ `vercel.json` - Vercel configuration
   - ✓ `api/index.py` - Serverless entry point
   - ✓ `requirements.txt` - Python dependencies
   - ✓ `.vercelignore` - Files to ignore
   - ✓ All application files (app.py, config.py, models.py, etc.)

### Step 2: Login to Vercel

```bash
vercel login
```

Follow the prompts to authenticate.

### Step 3: Configure Environment Variables

**Option A: Using Vercel CLI (Recommended)**

```bash
# Navigate to your project directory
cd C:\Users\kaush\OneDrive\Desktop\Voice-AI\send_mail

# Set environment variables
vercel env add EMAIL_PASSWORD
# Paste your Gmail app password when prompted

# Add other optional environment variables if needed
vercel env add ENVIRONMENT
# Enter: production

vercel env add SENDER_EMAIL
# Enter: your_email@domain.com
```

**Option B: Using Vercel Dashboard**

1. Go to https://vercel.com/dashboard
2. Select your project (after first deployment)
3. Go to Settings → Environment Variables
4. Add the following variables:

| Name | Value | Environment |
|------|-------|-------------|
| `EMAIL_PASSWORD` | Your Gmail app password | Production, Preview, Development |
| `ENVIRONMENT` | production | Production |
| `SENDER_EMAIL` | tech@asklena.ai | Production |

### Step 4: Deploy to Vercel

**Initial Deployment:**

```bash
# From your project directory
vercel

# Follow the prompts:
# - Set up and deploy: Y
# - Which scope: [Select your account]
# - Link to existing project: N
# - Project name: email-service (or your preferred name)
# - Directory: ./
# - Override settings: N
```

This creates a preview deployment. You'll get a URL like: `https://email-service-xxx.vercel.app`

**Production Deployment:**

```bash
vercel --prod
```

This deploys to production. You'll get a URL like: `https://email-service.vercel.app`

### Step 5: Verify Deployment

1. **Check Health Endpoint:**
   ```bash
   curl https://your-project.vercel.app/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "environment": "production",
     "email_configured": true,
     "smtp_reachable": true
   }
   ```

2. **View API Documentation:**
   Open in browser: `https://your-project.vercel.app/docs`

3. **Test Email Sending:**
   ```bash
   curl -X POST "https://your-project.vercel.app/api/v1/send-email" \
     -H "Content-Type: application/json" \
     -d '{
       "user_name": "Test User",
       "user_email": "your-email@example.com",
       "meeting_time": "Tomorrow at 2:00 PM EST"
     }'
   ```

## Alternative: Deploy via GitHub Integration

### Step 1: Push to GitHub

```bash
# Create a new repository on GitHub (if you haven't)
git remote add origin https://github.com/yourusername/email-service.git
git branch -M main
git push -u origin main
```

### Step 2: Connect to Vercel

1. Go to https://vercel.com/new
2. Click "Import Project"
3. Select your GitHub repository
4. Configure project:
   - Framework Preset: Other
   - Root Directory: ./
   - Build Command: (leave empty)
   - Output Directory: (leave empty)

5. Add Environment Variables:
   - Click "Environment Variables"
   - Add `EMAIL_PASSWORD` with your Gmail app password
   - Add any other variables from `.env.example`

6. Click "Deploy"

### Step 3: Enable Auto-Deploy

Once connected, every push to `main` branch will automatically deploy to production!

## Configuration

### Custom Domain

1. Go to your project in Vercel Dashboard
2. Settings → Domains
3. Add your domain (e.g., `api.yourdomain.com`)
4. Follow DNS configuration instructions
5. Update CORS in Vercel environment variables:
   ```
   CORS_ORIGINS=["https://yourdomain.com"]
   ```

### Environment-Specific Variables

Set different values for different environments:

```bash
# Production only
vercel env add RATE_LIMIT_REQUESTS production
# Enter: 10

# Preview and Development
vercel env add RATE_LIMIT_REQUESTS preview development
# Enter: 100
```

## Vercel CLI Commands Cheat Sheet

```bash
# Deploy preview
vercel

# Deploy production
vercel --prod

# View logs
vercel logs [deployment-url]

# List deployments
vercel ls

# List environment variables
vercel env ls

# Remove deployment
vercel rm [deployment-name]

# Pull environment variables locally
vercel env pull

# Link local project to Vercel
vercel link
```

## Troubleshooting

### Issue: "Function execution timed out"

**Solution 1: Reduce SMTP timeout**
```bash
vercel env add EMAIL_TIMEOUT
# Enter: 10
```

**Solution 2: Upgrade to Pro plan**
- Hobby: 10-second limit
- Pro: 60-second limit

### Issue: "Module not found"

**Solution: Check requirements.txt**
```bash
# Ensure all dependencies are listed
cat requirements.txt

# Re-deploy
vercel --prod
```

### Issue: "Email template not found"

**Solution: Verify file is not in .vercelignore**
```bash
# Check .vercelignore doesn't exclude email_template.html
cat .vercelignore

# Re-deploy
vercel --prod
```

### Issue: "CORS error"

**Solution: Update CORS_ORIGINS**
```bash
vercel env add CORS_ORIGINS
# Enter: ["https://yourdomain.com"]

# Re-deploy
vercel --prod
```

### Issue: Rate limiting not working

**Note:** In-memory rate limiting resets on cold starts. For production rate limiting, consider:
- Using Vercel Edge Config
- Adding Redis (Upstash Redis)
- Using a third-party rate limiting service

### Viewing Logs

```bash
# Real-time logs
vercel logs --follow

# Last 100 lines
vercel logs -n 100

# Specific deployment
vercel logs https://email-service-xxx.vercel.app
```

## Performance Optimization

### Reduce Cold Starts

1. **Keep functions warm** (Pro plan):
   - Vercel automatically keeps frequently-used functions warm

2. **Optimize imports:**
   ```python
   # Import only what you need
   from fastapi import FastAPI, Request
   # Instead of: from fastapi import *
   ```

3. **Use caching:**
   - Template caching is already implemented
   - Consider adding Vercel Edge Config for configuration caching

### Monitor Performance

1. Go to Vercel Dashboard
2. Select your project
3. View Analytics tab
4. Monitor:
   - Function duration
   - Function invocations
   - Error rates
   - Response times

## Cost Considerations

**Hobby Plan (Free):**
- 100 GB bandwidth
- 100 GB-hours serverless execution
- 10-second function timeout
- Good for testing and low-traffic applications

**Pro Plan ($20/month):**
- 1 TB bandwidth
- 1000 GB-hours serverless execution
- 60-second function timeout
- Better for production applications

## Security Best Practices

1. **Never commit .env file**
   ```bash
   # Verify .env is in .gitignore
   cat .gitignore | grep .env
   ```

2. **Use environment variables for all secrets**
   ```bash
   vercel env add EMAIL_PASSWORD production
   ```

3. **Rotate credentials regularly**
   - Update Gmail app password
   - Update in Vercel dashboard

4. **Enable rate limiting** (when not using serverless)
   - Consider Upstash Redis for distributed rate limiting

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
          vercel-args: '--prod'
```

## Testing Deployment

### Local Testing with Vercel Dev

```bash
# Install dependencies
pip install -r requirements.txt

# Start Vercel dev server
vercel dev

# Access at http://localhost:3000
```

### Test Email Sending

```bash
# Using curl
curl -X POST "https://your-project.vercel.app/api/v1/send-email" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "John Doe",
    "user_email": "john@example.com",
    "meeting_time": "Thursday, December 1st at 2:00 PM EST"
  }'

# Using Python
python -c "
import requests
response = requests.post(
    'https://your-project.vercel.app/api/v1/send-email',
    json={
        'user_name': 'John Doe',
        'user_email': 'john@example.com',
        'meeting_time': 'Thursday at 2PM'
    }
)
print(response.json())
"
```

## Rollback

If something goes wrong:

```bash
# List recent deployments
vercel ls

# View specific deployment
vercel inspect [deployment-url]

# Promote previous deployment to production
vercel promote [deployment-url]
```

## Support and Resources

- **Vercel Documentation**: https://vercel.com/docs
- **Vercel Community**: https://github.com/vercel/vercel/discussions
- **Python on Vercel**: https://vercel.com/docs/functions/serverless-functions/runtimes/python
- **FastAPI on Vercel**: https://vercel.com/guides/fastapi

## Next Steps

After successful deployment:

1. ✓ Test all endpoints
2. ✓ Configure custom domain
3. ✓ Set up monitoring/alerting
4. ✓ Update CORS origins
5. ✓ Test email delivery
6. ✓ Monitor function execution times
7. ✓ Set up CI/CD (optional)
8. ✓ Document your deployment URL

## Quick Reference

**Deploy:** `vercel --prod`
**Logs:** `vercel logs --follow`
**Env Vars:** `vercel env add EMAIL_PASSWORD`
**Domains:** Vercel Dashboard → Settings → Domains
**Rollback:** `vercel promote [previous-deployment-url]`

---

**Your deployment URL will be:** `https://email-service-[random].vercel.app`

Remember to save this URL and update your application to use it!
