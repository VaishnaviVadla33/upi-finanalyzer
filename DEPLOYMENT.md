# Deployment Guide for UPI FinAnalyzer

This guide covers multiple deployment options for your Flask application with Tesseract OCR dependency.

## 🚀 Deployment Options

### 1. Railway (Recommended)
Railway supports Docker deployments and handles system dependencies well.

**Steps:**
1. Connect your GitHub repository to Railway
2. Select the `deployment` branch
3. Railway will automatically detect the Dockerfile
4. Set environment variables in Railway dashboard
5. Deploy!

**Environment Variables to Set:**
```
FIREBASE_API_KEY=your_key
FIREBASE_AUTH_DOMAIN=your_domain
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_bucket
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
SMTP_USER=your_email
SMTP_PASS=your_app_password
SECRET_KEY=generate_random_secret
FLASK_ENV=production
FLASK_DEBUG=false
```

### 2. Render
Render supports Docker deployments with the render.yaml configuration.

**Steps:**
1. Connect GitHub repository to Render
2. Select `deployment` branch
3. Render will use the render.yaml configuration
4. Set environment variables in Render dashboard
5. Deploy!

### 3. Google Cloud Run
Best for containerized applications with automatic scaling.

**Steps:**
```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/upi-finanalyzer

# Deploy to Cloud Run
gcloud run deploy upi-finanalyzer \
  --image gcr.io/YOUR_PROJECT_ID/upi-finanalyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 4. DigitalOcean App Platform
Supports Docker deployments with good performance.

**Steps:**
1. Create new app in DigitalOcean
2. Connect GitHub repository
3. Select `deployment` branch
4. Choose Docker as build method
5. Set environment variables
6. Deploy!

## 🔧 Local Docker Testing

Test your deployment locally before pushing:

```bash
# Build the image
docker build -t upi-finanalyzer .

# Run with environment file
docker run -p 5000:5000 --env-file .env upi-finanalyzer

# Or use docker-compose
docker-compose up
```

## 📋 Pre-Deployment Checklist

- [ ] Firebase credentials configured
- [ ] Environment variables set
- [ ] Secret key generated (use: `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] SMTP settings configured for email
- [ ] APP_URL updated to production domain
- [ ] Test Docker build locally
- [ ] Firebase security rules configured
- [ ] Domain/SSL configured (if custom domain)

## 🔒 Security Notes

1. **Never commit sensitive files:**
   - `.env` files
   - `FIREBASE_CREDENTIALS.json`
   - Any files with API keys

2. **Use environment variables for:**
   - Database credentials
   - API keys
   - Secret keys
   - SMTP passwords

3. **Firebase Security:**
   - Configure Firestore security rules
   - Enable Firebase Authentication
   - Set up proper CORS settings

## 🐛 Troubleshooting

### Tesseract Issues
- Ensure Dockerfile installs tesseract-ocr
- Check TESSDATA_PREFIX environment variable
- Verify image processing permissions

### Firebase Connection
- Verify all Firebase environment variables
- Check Firebase project settings
- Ensure service account has proper permissions

### Memory Issues
- Increase container memory limits
- Optimize image processing
- Consider using smaller base images

## 📊 Monitoring

After deployment, monitor:
- Application logs
- Memory usage
- Response times
- Error rates
- OCR processing success rates

## 🔄 CI/CD Pipeline

Consider setting up automated deployments:
1. Push to `deployment` branch
2. Automated tests run
3. Docker image builds
4. Deployment to staging
5. Manual promotion to production