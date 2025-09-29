# UPI Financial Analyzer - Deployment Guide

## 🚀 Free Deployment Options for OCR-Heavy App

### 🥇 **Option 1: Railway.app (RECOMMENDED)**

**Why Railway is perfect for your project:**
- ✅ **$5/month free credits** (sufficient for small-medium traffic)
- ✅ **Handles heavy dependencies** (OCR, ML libraries)
- ✅ **Built-in Tesseract OCR**
- ✅ **Easy GitHub integration**
- ✅ **Environment variables** support
- ✅ **No sleep/wake cycles**

**Step-by-step deployment:**

1. **Prepare your repository:**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Deploy to Railway:**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and deploy

3. **Set Environment Variables:**
   - Go to your project → Variables tab
   - Add: `FLASK_ENV=production`
   - Upload your `FIREBASE_CREDENTIALS.json` as a file

4. **Custom Domain (Optional):**
   - Go to Settings → Domain
   - Add custom domain or use Railway subdomain

---

### 🥈 **Option 2: Render.com**

**Free tier specifications:**
- ✅ **Completely free** web services
- ✅ **750 hours/month** (enough for most projects)
- ⚠️ **Sleeps after 15 minutes** of inactivity
- ⚠️ **Cold start delays** (30-60 seconds)

**Step-by-step deployment:**

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

2. **Deploy to Render:**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub
   - Click "New" → "Web Service"
   - Connect your GitHub repository

3. **Configure Build Settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --host 0.0.0.0 --port $PORT`
   - Python Version: `3.10.0`

4. **Environment Variables:**
   - Add `FLASK_ENV=production`
   - Add Firebase credentials (copy-paste JSON content)

---

### 🥉 **Option 3: Google Cloud Run (Advanced)**

**Why Cloud Run is excellent:**
- ✅ **$300 free credits** for new users
- ✅ **Perfect Firebase integration**
- ✅ **Scales to zero** (pay per request)
- ✅ **Container-based** deployment
- 🔧 **Requires Docker knowledge**

**Step-by-step deployment:**

1. **Install Google Cloud CLI:**
   ```bash
   # Windows
   # Download from: https://cloud.google.com/sdk/docs/install
   
   # Mac/Linux
   curl https://sdk.cloud.google.com | bash
   ```

2. **Build and Deploy:**
   ```bash
   # Authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID

   # Build container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/upi-analyzer

   # Deploy to Cloud Run
   gcloud run deploy --image gcr.io/YOUR_PROJECT_ID/upi-analyzer --platform managed
   ```

---

## 📋 **Pre-Deployment Checklist**

### ✅ **Files Created:**
- [x] `Dockerfile` - Container configuration
- [x] `Procfile` - Process configuration  
- [x] `requirements.txt` - Python dependencies
- [x] `railway.json` - Railway configuration
- [x] `render.yaml` - Render configuration
- [x] `.dockerignore` - Docker ignore file

### ⚙️ **Environment Variables to Set:**
```
FLASK_ENV=production
TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/
PORT=5000 (auto-set by platform)
```

### 🔐 **Firebase Credentials:**
Your `FIREBASE_CREDENTIALS.json` file needs to be uploaded securely:
- **Railway**: Upload as file in dashboard
- **Render**: Copy-paste JSON content as env var
- **Google Cloud**: Use Secret Manager

---

## � **Cost Comparison**

| Platform | Free Tier | Limitations | Best For |
|----------|-----------|-------------|----------|
| **Railway** | $5/month credit | Usage-based billing | Production apps |
| **Render** | 750 hours/month | Sleeps after inactivity | Development/demos |
| **Google Cloud** | $300 credit (3 months) | Complex setup | Enterprise features |
| **Vercel** | ❌ Not suitable | No OCR support | Frontend only |
| **Netlify** | ❌ Not suitable | Static sites only | Frontend only |

---

## 🎯 **Recommended Deployment Path**

### For Development/Testing: **Render.com**
- Quick setup
- Zero cost
- Perfect for demos

### For Production: **Railway.app**
- Reliable uptime
- Better performance
- Worth the $5/month

### For Enterprise: **Google Cloud Run**
- Unlimited scaling
- Advanced features
- Perfect Firebase integration

---

## � **Important Notes for OCR Apps**

1. **Heavy Dependencies:** Your app uses large libraries (pandas, numpy, opencv). Railway handles this best.

2. **OCR Processing Time:** Tesseract can be slow. Consider:
   - Adding loading indicators
   - Implementing timeouts
   - Caching processed results

3. **Memory Usage:** OCR + ML libraries use significant RAM. Monitor usage on free tiers.

4. **File Uploads:** Ensure upload limits are sufficient for transaction images.

---

## � **Quick Start (Railway - Recommended)**

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Connect GitHub repository
4. Add Firebase credentials
5. Deploy automatically
6. Your app will be live in 2-3 minutes!

**Estimated monthly cost:** $2-5 (within free credits)
**Deployment time:** 2-5 minutes
**OCR performance:** Excellent
**Uptime:** 99.9%