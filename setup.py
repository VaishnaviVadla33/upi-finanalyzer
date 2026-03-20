#!/usr/bin/env python3
"""
FinAnalyzer Setup Script
Helps users set up the application quickly
"""

import os
import sys
import subprocess
import json

def print_header():
    print("=" * 60)
    print("🚀 FinAnalyzer Setup Script")
    print("=" * 60)
    print()

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_tesseract():
    """Check if Tesseract is installed"""
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ Tesseract OCR: {version}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Tesseract OCR not found")
    print("   Please install Tesseract OCR:")
    print("   - Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    print("   - macOS: brew install tesseract")
    print("   - Ubuntu: sudo apt install tesseract-ocr")
    return False

def install_requirements():
    """Install Python requirements"""
    print("\n📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_firebase_config():
    """Help user create Firebase configuration"""
    print("\n🔥 Firebase Configuration")
    print("1. Go to https://console.firebase.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Firestore Database")
    print("4. Go to Project Settings > Service Accounts")
    print("5. Generate new private key")
    print("6. Save the JSON file as 'FIREBASE_CREDENTIALS.json' in this directory")
    
    firebase_file = "FIREBASE_CREDENTIALS.json"
    if os.path.exists(firebase_file):
        print(f"✅ Found {firebase_file}")
        return True
    else:
        print(f"❌ {firebase_file} not found")
        print("   Please add your Firebase credentials file")
        return False

def create_env_file():
    """Create .env file if it doesn't exist"""
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"\n📝 Creating {env_file}...")
        env_content = """# Firebase Configuration
FIREBASE_KEY_PATH=FIREBASE_CREDENTIALS.json

# Google Cloud Vision API (Optional)
GOOGLE_CLOUD_VISION_KEY_PATH=google-cloud-vision-key.json

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
"""
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"✅ Created {env_file}")
    else:
        print(f"✅ {env_file} already exists")

def run_application():
    """Ask user if they want to run the application"""
    print("\n🎉 Setup Complete!")
    print("\nTo run the application:")
    print("  python app.py")
    print("\nThen open http://localhost:5000 in your browser")
    
    response = input("\nWould you like to start the application now? (y/n): ")
    if response.lower() in ['y', 'yes']:
        print("\n🚀 Starting FinAnalyzer...")
        try:
            subprocess.run([sys.executable, 'app.py'])
        except KeyboardInterrupt:
            print("\n👋 Application stopped")

def main():
    print_header()
    
    # Check prerequisites
    if not check_python_version():
        return
    
    if not check_tesseract():
        print("\n⚠️  Tesseract is required for OCR functionality")
        response = input("Continue anyway? (y/n): ")
        if response.lower() not in ['y', 'yes']:
            return
    
    # Install dependencies
    if not install_requirements():
        return
    
    # Create configuration files
    create_env_file()
    
    # Check Firebase configuration
    firebase_ready = create_firebase_config()
    
    if not firebase_ready:
        print("\n⚠️  Firebase configuration is required for full functionality")
        response = input("Continue anyway? (y/n): ")
        if response.lower() not in ['y', 'yes']:
            return
    
    # Offer to run the application
    run_application()

if __name__ == "__main__":
    main()