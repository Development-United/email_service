# Vercel Quick Start Guide

Deploy your email service to Vercel in 5 minutes!

## Prerequisites

- Vercel account (sign up at https://vercel.com)
- Gmail app password
- Node.js installed (for Vercel CLI)

## Quick Deploy (5 Steps)

### 1. Install Vercel CLI

```bash
npm install -g vercel
```

### 2. Login to Vercel

```bash
vercel login
```

### 3. Set Email Password

```bash
# Navigate to your project folder
cd C:\Users\kaush\OneDrive\Desktop\Voice-AI\send_mail

# Add your Gmail app password
vercel env add EMAIL_PASSWORD
# When prompted, paste your Gmail app password
# Select: Production, Preview, Development (all environments)
```

**How to get Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer"
3. Click "Generate"
4. Copy the 16-character password
5. Paste it when running the command above

### 4. Deploy!

```bash
# Deploy to production
vercel --prod
```

That's it! You'll get a URL like: `https://email-service-xxx.vercel.app`

### 5. Test Your API

```bash
# Check health
curl https://your-url.vercel.app/health

# View API docs (open in browser)
https://your-url.vercel.app/docs

# Send test email
curl -X POST "https://your-url.vercel.app/api/v1/send-email" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Test User",
    "user_email": "your-email@gmail.com",
    "meeting_time": "Tomorrow at 2:00 PM"
  }'
```

## Using the Deployment Script

### Windows:

```cmd
deploy-vercel.bat
```

### Mac/Linux:

```bash
chmod +x deploy-vercel.sh
./deploy-vercel.sh
```

## Common Issues & Solutions

### Issue: "vercel: command not found"

**Solution:**
```bash
# Install Vercel CLI
npm install -g vercel

# Or use npx (no installation needed)
npx vercel --prod
```

### Issue: "EMAIL_PASSWORD not set"

**Solution:**
```bash
vercel env add EMAIL_PASSWORD
# Paste your Gmail app password
```

### Issue: "Module not found"

**Solution:**
```bash
# Ensure requirements.txt is present
ls requirements.txt

# Re-deploy
vercel --prod
```

### Issue: Function timeout

**Solution:**
- Hobby plan has 10-second limit
- Upgrade to Pro for 60-second limit
- Or reduce EMAIL_TIMEOUT:
  ```bash
  vercel env add EMAIL_TIMEOUT
  # Enter: 10
  ```

## Next Steps

✅ **Add Custom Domain:**
1. Go to Vercel Dashboard
2. Select your project
3. Settings → Domains
4. Add your domain

✅ **Update CORS:**
```bash
vercel env add CORS_ORIGINS
# Enter: ["https://yourdomain.com"]
```

✅ **Monitor Usage:**
- Vercel Dashboard → Analytics
- Check function invocations
- Monitor error rates

## Important URLs

After deployment, save these URLs:

- **API Base:** `https://your-project.vercel.app`
- **Health Check:** `https://your-project.vercel.app/health`
- **API Docs:** `https://your-project.vercel.app/docs`
- **Send Email:** `POST https://your-project.vercel.app/api/v1/send-email`

## Environment Variables Reference

Set these in Vercel (if needed):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_PASSWORD` | ✅ Yes | - | Gmail app password |
| `SENDER_EMAIL` | No | tech@asklena.ai | From email |
| `ENVIRONMENT` | No | production | Environment name |
| `EMAIL_TIMEOUT` | No | 30 | SMTP timeout (seconds) |
| `CORS_ORIGINS` | No | ["*"] | Allowed origins |

## Useful Commands

```bash
# View logs
vercel logs --follow

# List deployments
vercel ls

# Remove deployment
vercel rm [deployment-name]

# Pull environment variables
vercel env pull .env.local

# Redeploy
vercel --prod --force
```

## Need Help?

- 📖 Full Guide: See `VERCEL_DEPLOYMENT.md`
- 🌐 Vercel Docs: https://vercel.com/docs
- 💬 Support: https://vercel.com/support

---

**Deployment Time:** ~2-3 minutes

**Cost:** Free (Hobby plan) or $20/month (Pro plan)

**Auto-deploys:** Push to GitHub = automatic deployment!
