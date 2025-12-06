# 🚀 Deployment Guide for upskillsinstitute.org

This guide covers deploying Upskill Institute to production.

---

## 📋 Pre-Deployment Checklist

- [ ] Domain registered: `upskillsinstitute.org` ✅
- [ ] Cloudflare account set up ✅
- [ ] Git repository created
- [ ] Paystack production keys obtained
- [ ] Environment variables prepared

---

## Option 1: Railway (Recommended - Easiest)

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub

### Step 2: Deploy from GitHub
1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial deployment"
   git remote add origin https://github.com/YOUR_USERNAME/upskillsinstitute.git
   git push -u origin main
   ```

2. In Railway:
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Choose your repository

### Step 3: Add PostgreSQL Database
1. In your Railway project, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway will automatically set `DATABASE_URL`

### Step 4: Set Environment Variables
In Railway dashboard → Variables:
```
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
FLASK_ENV=production
FLASK_DEBUG=false
PAYSTACK_SECRET_KEY=sk_live_your_key_here
```

### Step 5: Get Your Railway URL
Railway will give you a URL like: `upscale-production.up.railway.app`

---

## Option 2: Render (Also Easy)

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Create Web Service
1. Click **"New +" → "Web Service"**
2. Connect your GitHub repo
3. Configure:
   - **Name:** upskillsinstitute
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

### Step 3: Add PostgreSQL
1. Click **"New +" → "PostgreSQL"**
2. Connect it to your web service
3. Render sets `DATABASE_URL` automatically

### Step 4: Environment Variables
Add in Render dashboard:
```
SECRET_KEY=<your-secret-key>
FLASK_ENV=production
PAYSTACK_SECRET_KEY=sk_live_your_key
```

---

## 🌐 Cloudflare DNS Configuration

Once your app is deployed (on Railway, Render, etc.):

### Step 1: Get Your App URL
- Railway: `your-app.up.railway.app`
- Render: `your-app.onrender.com`

### Step 2: Configure DNS in Cloudflare

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select `upskillsinstitute.org`
3. Go to **DNS** tab
4. Add these records:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| CNAME | @ | your-app.up.railway.app | ✅ Proxied |
| CNAME | www | your-app.up.railway.app | ✅ Proxied |

### Step 3: SSL/TLS Settings
1. Go to **SSL/TLS** tab
2. Set encryption mode to **"Full (strict)"**

### Step 4: Configure Custom Domain on Host

**Railway:**
1. Go to your project → Settings → Domains
2. Add `upskillsinstitute.org` and `www.upskillsinstitute.org`

**Render:**
1. Go to your service → Settings → Custom Domains
2. Add both domains

---

## 🔐 Production Security Checklist

### Environment Variables (Required)
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

### Database Migration
Your app automatically creates tables on first run. For PostgreSQL:
1. The `DATABASE_URL` environment variable will be used
2. Tables are created automatically

### Paystack Production Keys
1. Go to [Paystack Dashboard](https://dashboard.paystack.com)
2. Switch to **Live Mode**
3. Copy your **Secret Key** (starts with `sk_live_`)
4. Add to environment variables

---

## 🧪 Post-Deployment Testing

After deployment, test these URLs:

1. **Homepage:** `https://upskillsinstitute.org`
2. **Courses:** `https://upskillsinstitute.org/courses`
3. **Health Check:** `https://upskillsinstitute.org/health`
4. **404 Page:** `https://upskillsinstitute.org/nonexistent`

### Security Headers Check
```bash
curl -I https://upskillsinstitute.org
```

Should show:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Strict-Transport-Security` (via Cloudflare)

---

## 📊 Monitoring & Logs

### Railway
- Dashboard shows real-time logs
- Built-in metrics for CPU/Memory

### Render
- Logs available in dashboard
- Auto-restarts on crashes

### Recommended: Add Error Tracking
Consider adding [Sentry](https://sentry.io) for error tracking:
```bash
pip install sentry-sdk[flask]
```

---

## 🔄 Updating Your App

1. Make changes locally
2. Commit and push:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
3. Railway/Render auto-deploys from GitHub

---

## 💰 Cost Breakdown

### Railway
- **Free tier:** 500 hours/month, $5 credit
- **Pro:** $5/month + usage (usually $5-15/month total)

### Render
- **Free tier:** 750 hours/month (spins down after inactivity)
- **Starter:** $7/month (always on)

### Cloudflare
- **Free tier:** DNS, CDN, SSL included ✅

### Estimated Monthly Cost
- **Minimum:** $0 (free tiers)
- **Recommended:** $7-15/month for always-on service

---

## 🆘 Troubleshooting

### App won't start
- Check logs for errors
- Verify all environment variables are set
- Ensure `Procfile` is in root directory

### Database errors
- Confirm `DATABASE_URL` is set
- Check if PostgreSQL addon is running

### Domain not working
- Verify DNS records in Cloudflare
- Wait 5-10 minutes for DNS propagation
- Check custom domain settings on host

### HTTPS issues
- Ensure Cloudflare SSL is set to "Full (strict)"
- Verify domain is added to hosting platform

---

## 📞 Support Resources

- **Railway Docs:** https://docs.railway.app
- **Render Docs:** https://render.com/docs
- **Cloudflare Docs:** https://developers.cloudflare.com

---

## Quick Deploy Commands

```bash
# Initialize git (if not done)
cd /Users/ndmx0/DEV/Upscale
git init
git add .
git commit -m "Initial production deployment"

# Create GitHub repo and push
# (Create repo on github.com first, then:)
git remote add origin https://github.com/YOUR_USERNAME/upskillsinstitute.git
git branch -M main
git push -u origin main

# Generate secret key for production
python -c "import secrets; print(secrets.token_hex(32))"
```

Good luck with your launch! 🎉

