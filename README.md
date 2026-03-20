# UPI FinAnalyzer - Smart Financial Management

A comprehensive financial management application built with Flask and Firebase that helps users track, analyze, and manage their financial transactions through OCR-powered receipt scanning and intelligent analytics.

## Features

- 🔍 **OCR Receipt Scanning**: Extract transaction details from images using Tesseract OCR
- 📊 **Financial Analytics**: Comprehensive spending analysis and visualization
- 🔐 **Secure Authentication**: Firebase-powered user authentication with password reset
- 👥 **Group Management**: Create and manage financial groups for shared expenses
- 📈 **Smart Insights**: AI-powered spending suggestions and alerts
- 📱 **Responsive Design**: Modern, mobile-friendly interface
- 🔄 **Real-time Data**: Live dashboard updates with transaction history

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **OCR**: Tesseract OCR
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **Data Processing**: Pandas, NumPy

## Prerequisites

- Python 3.8+
- Tesseract OCR
- Firebase Project
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/VaishnaviVadla33/upi-finanalyzer.git
cd upi-finanalyzer
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Install to default location: `C:\Program Files\Tesseract-OCR\`

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

### 5. Firebase Setup

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Authentication and Firestore Database
3. Download the service account key JSON file
4. Rename it to `FIREBASE_CREDENTIALS.json` and place in project root

### 6. Environment Configuration

1. Copy the environment template:
```bash
cp .env.template .env
```

2. Edit `.env` file with your configuration:
```env
# Firebase Configuration
FIREBASE_KEY_PATH=FIREBASE_CREDENTIALS.json

# Firebase Client Configuration (from Firebase Console > Project Settings > Your apps)
FIREBASE_API_KEY=your_firebase_api_key_here
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789012
FIREBASE_APP_ID=1:123456789012:web:abcdef123456789
FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX

# Email Configuration (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
SMTP_FROM=your-email@gmail.com
APP_URL=http://localhost:5000
```

### 7. Gmail App Password Setup (for password reset emails)

1. Enable 2-factor authentication on your Gmail account
2. Go to Google Account settings > Security > App passwords
3. Generate an app password for "Mail"
4. Use that app password in `SMTP_PASS` (not your regular Gmail password)

## Running the Application

### Development Mode

```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Mode

For production deployment, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usage

### 1. User Registration/Login
- Navigate to `/auth` to create an account or sign in
- Use the password reset feature if needed

### 2. Upload Transactions
- Go to `/upload` to scan receipts or manually enter transactions
- The OCR system will automatically extract transaction details
- Review and save the extracted information

### 3. View Analytics
- Visit `/analytics` to see spending patterns and insights
- View categorized expenses and income trends
- Get AI-powered savings suggestions

### 4. Manage Groups
- Create or join financial groups at `/group`
- Share expenses with family or friends
- Track group spending and contributions

## Project Structure

```
upi-finanalyzer/
├── app.py                 # Main Flask application
├── dashboard_helpers.py   # Analytics and helper functions
├── requirements.txt       # Python dependencies
├── .env.template         # Environment variables template
├── .gitignore           # Git ignore rules
├── templates/           # HTML templates
│   ├── base.html
│   ├── auth.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── analytics.html
│   └── ...
├── static/              # Static assets
│   ├── css/
│   ├── js/
│   └── images/
└── venv/               # Virtual environment (not in git)
```

## API Endpoints

- `GET /` - Landing page
- `GET /auth` - Authentication page
- `POST /login` - User login
- `POST /register` - User registration
- `GET /dashboard` - Main dashboard
- `POST /api/upload` - Upload transaction image
- `GET /api/dashboard-data` - Dashboard analytics data
- `GET /api/analytics-data` - Detailed analytics
- `POST /api/forgot-password` - Password reset request
- `GET /api/firebase-config` - Firebase client configuration

## Security Features

- Environment-based configuration (no hardcoded secrets)
- Firebase Authentication integration
- Password hashing with PBKDF2
- CSRF protection
- Input validation and sanitization
- Secure session management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Troubleshooting

### Common Issues

1. **Tesseract not found**: Ensure Tesseract is installed and in your PATH
2. **Firebase connection failed**: Check your credentials and internet connection
3. **OCR accuracy issues**: Ensure images are clear and well-lit
4. **Email not sending**: Verify SMTP configuration and Gmail app password

### Logs

Check the console output for detailed error messages and debugging information.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, email [your-email@example.com] or create an issue on GitHub.

## Acknowledgments

- Firebase for backend services
- Tesseract OCR for text extraction
- Chart.js for data visualization
- Flask community for the excellent framework