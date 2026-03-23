# FinAnalyzer - Smart UPI Financial Management Platform

A comprehensive financial management application that helps users track, analyze, and manage their UPI transactions through intelligent OCR-powered receipt scanning and advanced analytics.

## Live Demo

Visit the live application: [https://upi-finanalyzer.onrender.com/](https://upi-finanalyzer.onrender.com/)

## Overview

FinAnalyzer is a modern web application built with Flask and Firebase that transforms the way you manage your finances. Simply upload screenshots of your UPI payment receipts, and our intelligent OCR system automatically extracts transaction details, categorizes expenses, and provides actionable insights to help you make better financial decisions.

## Key Features

### Smart OCR Scanning
- Automatic extraction of transaction details from UPI receipt screenshots
- Intelligent amount and payee name recognition
- Support for multiple UPI payment apps (Google Pay, PhonePe, Paytm, etc.)
- Bulk upload capability for processing up to 10 receipts at once
- Advanced text preprocessing for improved accuracy

### Comprehensive Dashboard
- Real-time financial overview with income, expenses, and balance tracking
- Recent transaction history with quick access
- Monthly savings goal tracking with progress indicators
- Spending alerts when budget limits are exceeded
- Visual representation of financial health

### Advanced Analytics
- Interactive charts and graphs for spending patterns
- Category-wise expense breakdown
- Monthly and yearly spending trends
- AI-powered savings suggestions based on spending behavior
- Peak spending time analysis
- Cash flow analysis with detailed insights

### Group Expense Management
- Create and manage financial groups for shared expenses
- Invite members via email or shareable invite codes
- Role-based access control (Admin, Member, Viewer)
- Group analytics and spending reports
- Track individual contributions within groups
- Archive or transfer group ownership

### User Settings & Alerts
- Set monthly savings goals with progress tracking
- Configure spending alerts by category and time period
- Email notifications for savings reports and budget alerts
- Customizable alert thresholds
- Transaction history with edit and delete capabilities

### Security & Authentication
- Secure Firebase Authentication integration
- Password reset functionality via email
- Session management with automatic timeout
- Environment-based configuration for sensitive data
- PBKDF2 password hashing
- Input validation and sanitization

## Technology Stack

### Backend
- **Framework**: Flask (Python 3.8+)
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **OCR Engine**: Tesseract OCR with custom preprocessing
- **Data Processing**: Pandas, NumPy
- **Email Service**: SMTP with Gmail integration

### Frontend
- **HTML5** with Jinja2 templating
- **CSS3** with custom design system
- **JavaScript** (ES6+) for dynamic interactions
- **Chart.js** for data visualization
- **Font Awesome** for icons

### Deployment
- **Platform**: Render
- **Containerization**: Docker
- **CI/CD**: Automated deployment from GitHub

## Screenshots

### Landing Page
![Landing Page](https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/landing.png)

### Dashboard
![Dashboard](https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/dashboard.png)

### OCR Scan
![OCR Scan](https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/ocr-scan.png)

### Analytics
![Analytics](https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/analytics.png)

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR
- Firebase Project with Firestore and Authentication enabled
- Git
- Gmail account (for email notifications)

### Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/VaishnaviVadla33/upi-finanalyzer.git
cd upi-finanalyzer
```

#### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Install Tesseract OCR

**Windows:**
- Download installer from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Install to default location: `C:\Program Files\Tesseract-OCR\`
- Add to system PATH if not done automatically

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

#### 5. Firebase Configuration

1. Create a new project at [Firebase Console](https://console.firebase.google.com/)
2. Enable **Authentication** (Email/Password provider)
3. Enable **Firestore Database** (Start in production mode)
4. Go to Project Settings > Service Accounts
5. Click "Generate New Private Key" and download the JSON file
6. Rename the file to `FIREBASE_CREDENTIALS.json` and place it in the project root

#### 6. Environment Variables

Create a `.env` file in the project root:

```env
# Firebase Admin SDK
FIREBASE_KEY_PATH=FIREBASE_CREDENTIALS.json

# Firebase Client Configuration (from Firebase Console > Project Settings > General)
FIREBASE_API_KEY=your_api_key_here
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abc123def456
FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX

# Email Configuration (Gmail SMTP)
SENDER_EMAIL=your-email@gmail.com
SENDER_APP_PASSWORD=your-16-char-app-password
```

#### 7. Gmail App Password Setup

1. Enable 2-Factor Authentication on your Gmail account
2. Go to [Google Account Security](https://myaccount.google.com/security)
3. Navigate to "App passwords" under "Signing in to Google"
4. Generate a new app password for "Mail"
5. Copy the 16-character password to `SENDER_APP_PASSWORD` in `.env`

#### 8. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Docker Deployment

### Using Docker Compose

```bash
# Build and run
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop containers
docker-compose down
```

### Using Docker Directly

```bash
# Build image
docker build -t finanalyzer .

# Run container
docker run -p 5000:5000 --env-file .env finanalyzer
```

## Deployment to Render

The application is configured for automatic deployment to Render.

### Steps:

1. Fork this repository to your GitHub account
2. Create a new Web Service on [Render](https://render.com/)
3. Connect your GitHub repository
4. Configure the following:
   - **Branch**: `deployment`
   - **Build Command**: (handled by Dockerfile)
   - **Start Command**: (handled by Dockerfile)
5. Add environment variables from your `.env` file
6. Add `FIREBASE_CREDENTIALS.json` as a secret file at path `/etc/secrets/FIREBASE_CREDENTIALS.json`
7. Deploy

The application will automatically redeploy on every push to the deployment branch.

## Usage Guide

### Getting Started

1. **Sign Up**: Create a new account at `/auth`
2. **Upload Receipt**: Navigate to "OCR Scan" and upload a UPI payment screenshot
3. **Review Data**: Check the automatically extracted transaction details
4. **Save Transaction**: Confirm and save to your transaction history
5. **View Dashboard**: See your financial overview with real-time updates

### Bulk Upload

1. Go to "OCR Scan" and click "Bulk Upload"
2. Select up to 10 UPI receipt screenshots
3. Wait for processing (do not refresh the page)
4. Review all extracted transactions
5. Edit any incorrect details
6. Save all transactions at once

### Setting Up Savings Goals

1. Navigate to "Settings"
2. Set your monthly savings target
3. Enable savings goal tracking
4. View progress on your dashboard
5. Receive email reports on savings achievement

### Creating Spending Alerts

1. Go to "Settings" > "Spending Alerts"
2. Click "Add New Alert"
3. Configure alert name, limit, category, and period
4. Enable the alert
5. Receive notifications when limits are exceeded

### Managing Groups

1. Navigate to "Groups"
2. Click "Create New Group"
3. Configure group details (name, type, currency)
4. Invite members via email or share invite code
5. View group analytics and member contributions

## Project Structure

```
finanalyzer/
├── app.py                      # Main Flask application
├── dashboard_helpers.py        # Analytics and utility functions
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose configuration
├── render.yaml                 # Render deployment configuration
├── .dockerignore              # Docker ignore rules
├── .gitignore                 # Git ignore rules
├── .env                       # Environment variables (not in git)
├── FIREBASE_CREDENTIALS.json  # Firebase service account (not in git)
├── DEPLOYMENT.md              # Deployment documentation
├── README.md                  # This file
├── templates/                 # HTML templates
│   ├── base.html             # Base template with navigation
│   ├── simple_base.html      # Simple base for landing page
│   ├── index.html            # Landing page
│   ├── auth.html             # Login/Register page
│   ├── dashboard.html        # Main dashboard
│   ├── upload.html           # Single upload page
│   ├── upload_multiple.html  # Bulk upload page
│   ├── analytics.html        # Analytics page
│   ├── history.html          # Transaction history
│   ├── group.html            # Group management
│   ├── group_dashboard.html  # Group analytics
│   ├── settings.html         # User settings
│   └── reset_password.html   # Password reset page
├── static/                    # Static assets
│   ├── css/
│   │   └── main.css          # Main stylesheet
│   ├── js/
│   │   └── main.js           # Main JavaScript
│   └── favicon.ico           # Application icon
└── uploads/                   # Uploaded images (not in git)
```

## API Documentation

### Authentication Endpoints

- `POST /login` - User login
- `POST /register` - User registration
- `POST /api/forgot-password` - Request password reset
- `POST /reset-password` - Reset password with token
- `GET /logout` - User logout

### Transaction Endpoints

- `POST /api/upload` - Upload and process receipt image
- `POST /api/save-transaction` - Save single transaction
- `POST /api/save-transactions-bulk` - Save multiple transactions
- `GET /api/transactions` - Get all user transactions
- `PUT /api/transaction/<id>` - Update transaction
- `DELETE /api/transaction/<id>` - Delete transaction

### Dashboard Endpoints

- `GET /api/dashboard-data` - Get dashboard summary
- `GET /api/analytics-data` - Get detailed analytics
- `GET /api/spending-categories` - Get category breakdown
- `GET /api/dashboard-alerts` - Get active alerts and savings progress

### Group Endpoints

- `GET /api/groups` - Get all user groups
- `POST /api/create-group` - Create new group
- `GET /api/group/<id>` - Get group details
- `PUT /api/group/<id>/settings` - Update group settings
- `POST /api/join-group` - Join group with invite code
- `POST /api/group/<id>/leave` - Leave group
- `DELETE /api/group/<id>/member/<email>` - Remove member
- `GET /api/group-analytics/<id>` - Get group analytics

### Settings Endpoints

- `GET /api/user-settings` - Get user settings
- `PUT /api/user-settings/savings-goal` - Update savings goal
- `POST /api/user-settings/spending-alerts` - Add spending alert
- `DELETE /api/user-settings/spending-alerts/<id>` - Delete alert
- `PUT /api/user-settings/spending-alerts/<id>/toggle` - Toggle alert

## OCR Processing Details

### Supported UPI Apps
- PhonePe

### Extraction Capabilities
- Transaction amount with rupee symbol normalization
- Payee/Payer name with intelligent cleaning
- Transaction date and time
- Payment type (Credit/Debit)
- Automatic category detection

### Preprocessing Pipeline
1. Image conversion to grayscale
2. Contrast enhancement
3. Noise reduction
4. Text extraction with Tesseract
5. Rupee symbol normalization (handles OCR misreads)
6. Context-aware amount extraction
7. Name cleaning (removes emojis, artifacts, phone numbers)
8. Category classification based on keywords

## Troubleshooting

### Common Issues

**Issue**: Tesseract not found error
**Solution**: Ensure Tesseract is installed and added to system PATH

**Issue**: Firebase connection failed
**Solution**: Verify `FIREBASE_CREDENTIALS.json` is in the correct location and contains valid credentials

**Issue**: OCR extraction inaccurate
**Solution**: Ensure receipt images are clear, well-lit, and not blurry. Supported formats: PNG, JPG, WEBP

**Issue**: Email notifications not working
**Solution**: Verify Gmail app password is correct and 2FA is enabled on your Google account

**Issue**: Port 5000 already in use
**Solution**: Change the port in `app.py` or stop the process using port 5000

### Debug Mode

Enable debug logging by setting `debug=True` in `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

## Performance Optimization

- Transaction data is cached for faster dashboard loading
- Firestore queries are optimized with proper indexing
- Images are processed asynchronously to prevent blocking
- Static assets are minified for production
- Database queries use field filters for efficiency

## Security Best Practices

- All sensitive data is stored in environment variables
- Firebase credentials are never committed to version control
- Passwords are hashed using PBKDF2 with salt
- Session tokens expire after inactivity
- Input validation on all user-submitted data
- HTTPS enforced in production
- CORS configured for API endpoints

## Contributing

We welcome contributions to FinAnalyzer!
