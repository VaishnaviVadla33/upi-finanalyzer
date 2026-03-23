# Quick Setup Guide for UPI FinAnalyzer

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/VaishnaviVadla33/upi-finanalyzer.git
cd upi-finanalyzer
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.template .env
```

Edit `.env` with your Firebase credentials:
```env
# Get these from Firebase Console > Project Settings > Your apps
FIREBASE_API_KEY=your_api_key_here
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abcdef123456789

# For email notifications
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-gmail-app-password
```

### 3. Firebase Setup
1. Create Firebase project at https://console.firebase.google.com/
2. Enable Authentication (Email/Password)
3. Enable Firestore Database
4. Download service account key → rename to `FIREBASE_CREDENTIALS.json`

### 4. Install Tesseract OCR
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`

### 5. Run Application
```bash
python app.py
```
Visit: http://localhost:5000

## 🔐 Security Checklist

✅ **Environment Variables**: All sensitive data moved to `.env`  
✅ **Firebase Config**: Loaded from environment variables  
✅ **Credentials**: Service account key in `.gitignore`  
✅ **API Keys**: No hardcoded keys in templates  
✅ **SMTP**: Email credentials in environment variables  

## 📁 Important Files

- `.env` - Your environment variables (NOT in git)
- `FIREBASE_CREDENTIALS.json` - Service account key (NOT in git)
- `.env.template` - Template for environment setup
- `firebase_config.json.template` - Template for Firebase config

## 🛠 Troubleshooting

**Firebase Error**: Check your `.env` file has correct Firebase credentials  
**OCR Not Working**: Ensure Tesseract is installed and in PATH  
**Email Not Sending**: Use Gmail App Password, not regular password  

## 📞 Support

Create an issue on GitHub: https://github.com/VaishnaviVadla33/upi-finanalyzer/issues