#!/usr/bin/env python3
"""
Setup Verification Script for UPI FinAnalyzer
Checks if all required components are properly configured
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and print status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False

def check_env_var(var_name, description):
    """Check if environment variable is set"""
    value = os.getenv(var_name)
    if value and value != "your_value_here" and "REPLACE" not in value:
        print(f"✅ {description}: {var_name} (configured)")
        return True
    else:
        print(f"❌ {description}: {var_name} (not configured)")
        return False

def check_tesseract():
    """Check if Tesseract is installed"""
    try:
        import pytesseract
        # Try to get version
        pytesseract.get_tesseract_version()
        print("✅ Tesseract OCR: Installed and accessible")
        return True
    except Exception as e:
        print(f"❌ Tesseract OCR: Not properly installed ({e})")
        return False

def main():
    print("🔍 UPI FinAnalyzer Setup Verification")
    print("=" * 50)
    
    # Load environment variables from .env file
    env_file = Path('.env')
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded")
    else:
        print("❌ .env file not found - copy from .env.template")
    
    print("\n📁 Required Files:")
    files_ok = True
    files_ok &= check_file_exists('.env', '.env file')
    files_ok &= check_file_exists('FIREBASE_CREDENTIALS.json', 'Firebase service account key')
    files_ok &= check_file_exists('requirements.txt', 'Requirements file')
    
    print("\n🔧 Environment Variables:")
    env_ok = True
    env_ok &= check_env_var('FIREBASE_API_KEY', 'Firebase API Key')
    env_ok &= check_env_var('FIREBASE_PROJECT_ID', 'Firebase Project ID')
    env_ok &= check_env_var('FIREBASE_AUTH_DOMAIN', 'Firebase Auth Domain')
    env_ok &= check_env_var('SMTP_USER', 'SMTP Email User')
    env_ok &= check_env_var('SMTP_PASS', 'SMTP Email Password')
    
    print("\n🛠 Dependencies:")
    deps_ok = True
    deps_ok &= check_tesseract()
    
    try:
        import flask
        print("✅ Flask: Installed")
    except ImportError:
        print("❌ Flask: Not installed (run: pip install -r requirements.txt)")
        deps_ok = False
    
    try:
        import firebase_admin
        print("✅ Firebase Admin: Installed")
    except ImportError:
        print("❌ Firebase Admin: Not installed (run: pip install -r requirements.txt)")
        deps_ok = False
    
    print("\n" + "=" * 50)
    
    if files_ok and env_ok and deps_ok:
        print("🎉 Setup verification PASSED! You're ready to run the application.")
        print("Run: python app.py")
    else:
        print("⚠️  Setup verification FAILED. Please fix the issues above.")
        print("📖 See SETUP_GUIDE.md for detailed instructions.")
    
    print("\n🔗 Repository: https://github.com/VaishnaviVadla33/upi-finanalyzer")

if __name__ == "__main__":
    main()