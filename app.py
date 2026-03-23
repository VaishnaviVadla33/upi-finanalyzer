from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from PIL import Image
import pytesseract
import re
import random
import string
import hashlib
import secrets
from datetime import datetime
import os
import json                          # ← REQUIRED for load_firebase_config()
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore_v1.base_query import FieldFilter
from dotenv import load_dotenv
from functools import wraps
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
import certifi
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['REQUESTS_CA_BUNDLE']               = certifi.where()
os.environ['SSL_CERT_FILE']                    = certifi.where()
os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = certifi.where()
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GRPC_TRACE']     = ''


from dashboard_helpers import (
    get_savings_suggestions,
    compare_spending,
    cash_flow_analysis,
    spending_alerts,
    get_top_time_intervals,
)

# ── Rupee normalization ────────────────────────────────────────────────────────
# OCR misreads ₹ as: 2, 3, 7, 1, Z, %, $, @, ¥, 8, S, £, R, 5, and sometimes
# leaves no symbol at all but puts a space before the digits.
# Strategy: after basic cleanup, replace any of these characters that are
# immediately followed by digits (with optional space) → ₹
_RUPEE_NOISE = re.compile(r'(?<!\w)'           # not preceded by a word char (avoid mid-word hits)
                         r'[₹Rs23781Z%$@¥£SR5]'  # expanded misread set + real symbol
                         r'\.?'               # optional dot (Rs. style)
                         r'\s?'               # optional space
                         r'(?=\d)'            # must be followed by a digit
                         )

def normalize_rupee(text: str) -> str:
    """Replace all OCR-garbled rupee symbols with ₹."""
    return _RUPEE_NOISE.sub('₹', text)

# ── Amount extraction ─────────────────────────────────────────────────────────
# After normalizing, all real amounts start with ₹.
# UPI receipts always show the amount right after "Paid to <Name>" or
# "Received from <Name>" on the SAME line or the next.
# The "Debited from XXXXXXX4090  ₹200" line is a confirmation duplicate —
# we want the FIRST occurrence, not the bank-account-debit line.
_AMOUNT_RE = re.compile(r'₹\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?)')

def extract_amount(text: str) -> str:
    """Extract amount - PRIORITIZE comma-separated amounts, then any amount with ₹"""
    # High priority: comma-separated amounts
    amount_patterns = [
        (r'₹\s*(\d{1,3}(?:,\d{3})+)', 'high'),  # ₹1,500
        (r'Rs\.?\s*(\d{1,3}(?:,\d{3})+)', 'high'),  # Rs.1,500
        # Medium priority: amounts with rupee symbol (2-6 digits)
        (r'₹\s*(\d{2,6})', 'medium'),  # ₹500 or ₹1500
        (r'Rs\.?\s*(\d{2,6})', 'medium'),  # Rs.500
        # Low priority: standalone amounts
        (r'(?:Amount|Total)[:\s]*₹?\s*(\d{1,3}(?:,\d{3})+)', 'low'),
        (r'(?:Amount|Total)[:\s]*₹?\s*(\d{2,6})', 'low'),
    ]
    
    found_amounts = []
    for pattern, priority in amount_patterns:
        for match in re.finditer(pattern, text, re.I):
            try:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if 10 <= amount <= 10_000_000:  # Reasonable amount range
                    found_amounts.append((amount, priority, pattern))
            except ValueError:
                continue
    
    # Select the best amount based on priority
    if found_amounts:
        # Sort by priority (high > medium > low), then by amount (larger is more likely correct)
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        found_amounts.sort(key=lambda x: (priority_order[x[1]], -x[0]))
        best_amount = found_amounts[0][0]
        return str(best_amount)
    
    # If still no amount, look for any comma-separated number OR any 2-6 digit number
    comma_numbers = re.findall(r'\b(\d{1,3}(?:,\d{3})+)\b', text)
    for num_str in comma_numbers:
        try:
            amount = float(num_str.replace(',', ''))
            if 10 <= amount <= 10_000_000:
                return str(amount)
        except ValueError:
            continue
    
    # Last resort: find any reasonable number
    all_numbers = re.findall(r'\b(\d{2,6})\b', text)
    for num in all_numbers:
        try:
            amount = float(num)
            # Skip transaction IDs and phone numbers (too long)
            if 10 <= amount <= 100000:
                return str(amount)
        except ValueError:
            continue
    
    return '0'

# ── Name extraction ────────────────────────────────────────────────────────────
# UPI receipts structure:
#   "Paid to"          → next non-empty line or rest of same line is the name
#   "Received from"    → same
#   "From"             → same
# After grabbing the candidate, strip:
#   - phone numbers (10+ digits)
#   - amounts (₹ or comma-number patterns)
#   - common OCR artifacts (leading rh/th/lh, trailing sa/ot etc.)
#   - anything that's mostly digits
_NAME_ANCHORS = [
    (re.compile(r'paid\s+to[:\s]*(.*)$',         re.I), 1),
    (re.compile(r'received\s+from[:\s]*(.*)$',    re.I), 1),
    (re.compile(r'from[:\s]+(.+)$',               re.I), 1),
    (re.compile(r'to[:\s]+([A-Z].+)$',            re.I), 1),
    (re.compile(r'pay\s+to[:\s]*(.*)$',           re.I), 1),
]

_PHONE_RE    = re.compile(r'\+?\d[\d\s\-]{8,}')
_DIGIT_HEAVY = re.compile(r'^\s*[\d\W]+\s*$')          # line is mostly digits/symbols
_OCR_LEAD    = re.compile(r'^(rh|th|lh|ih|1h|Il)\s*', re.I)
_OCR_TRAIL   = re.compile(r'\s+(sa|ot|at|et|it|ut|Sa)$', re.I)
_NOISE_CHARS = re.compile(r'[^A-Za-z\s&.\'-]')         # keep only name chars
_EMOJI_RE    = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F270]')  # emoji patterns

def _clean_name_candidate(raw: str) -> str:
    """Strip noise from a name candidate string."""
    raw = _AMOUNT_RE.sub('', raw)           # remove ₹ amounts
    raw = _PHONE_RE.sub('', raw)            # remove phone numbers
    raw = _EMOJI_RE.sub('', raw)            # remove emojis
    raw = _OCR_LEAD.sub('', raw)            # leading OCR artifacts
    raw = _OCR_TRAIL.sub('', raw)           # trailing OCR artifacts
    raw = _NOISE_CHARS.sub(' ', raw)        # keep only name-legal chars
    raw = re.sub(r'\s{2,}', ' ', raw)      # collapse whitespace
    return raw.strip()

def extract_name(text: str, payment_type: str) -> str:
    """Extract payee/payer name using anchor-relative line scanning."""
    lines = [l.strip() for l in text.splitlines()]
    
    for i, line in enumerate(lines):
        for anchor_re, _ in _NAME_ANCHORS:
            m = anchor_re.search(line)
            if not m:
                continue
            
            # Candidate is text after the anchor on the same line
            candidate = m.group(1).strip()
            
            # If the same line had nothing useful, try the next lines
            if not candidate or _DIGIT_HEAVY.match(candidate):
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j]
                    # Skip lines that are clearly not names
                    if not next_line:
                        continue
                    if _DIGIT_HEAVY.match(next_line):
                        continue
                    if re.search(r'(transaction|UTR|UPI|ref|bank|HDFC|SBI|ICICI|axis|amount|debited|credited|transfer)', next_line, re.I):
                        continue
                    candidate = next_line
                    break
            
            if not candidate:
                continue
            
            # Take only the first line of multi-line candidate
            candidate = candidate.split('\n')[0]
            
            # Additional cleaning before the main clean function
            # Remove common OCR artifacts that appear before names
            candidate = re.sub(r'^[^\w\s]*', '', candidate)  # remove leading non-word chars
            candidate = re.sub(r'[^\w\s]*$', '', candidate)  # remove trailing non-word chars
            
            cleaned = _clean_name_candidate(candidate)
            
            # Must be at least 2 chars, not all digits, and contain at least one letter
            if len(cleaned) >= 2 and not cleaned.isdigit() and re.search(r'[A-Za-z]', cleaned):
                # Final validation: name shouldn't be mostly numbers or symbols
                letter_count = len(re.findall(r'[A-Za-z]', cleaned))
                if letter_count >= len(cleaned) * 0.5:  # at least 50% letters
                    return cleaned
    
    return ''

app = Flask(__name__, template_folder='templates', static_folder='static')

# Use environment variable for secret key in production
app.secret_key = os.getenv('SECRET_KEY', 'finanalyzer_secret_key_2024')

# ── Firebase ──────────────────────────────────────────────────────────────────
load_dotenv()

try:
    # Method 1: Try Render Secret File first (production)
    secret_file_path = "/etc/secrets/FIREBASE_CREDENTIALS.json"
    if os.path.exists(secret_file_path):
        print(f"✅ Found Firebase credentials at: {secret_file_path}")
        cred = credentials.Certificate(secret_file_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized from Secret File")
    
    # Method 2: Try environment variable (backup)
    elif os.getenv('FIREBASE_CREDENTIALS_JSON'):
        print("🔄 Trying Firebase credentials from environment variable")
        firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        cred_dict = json.loads(firebase_creds_json)
        # Fix newline escaping in private key
        if 'private_key' in cred_dict:
            cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase initialized from environment variable")
    
    # Method 3: Try local file (development)
    else:
        firebase_key_path = os.getenv('FIREBASE_KEY_PATH', 'FIREBASE_CREDENTIALS.json')
        if os.path.exists(firebase_key_path):
            print(f"✅ Found local Firebase credentials at: {firebase_key_path}")
            cred = credentials.Certificate(firebase_key_path)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("✅ Firebase initialized from local file")
        else:
            print("❌ No Firebase credentials found")
            db = None
            
except Exception as e:
    print(f"❌ Firebase initialization failed: {str(e)}")
    db = None

if db:
    credit_collection = db.collection('credit_transactions')
    debit_collection  = db.collection('debit_transactions')
    groups_collection = db.collection('groups')
    users_collection  = db.collection('users')
    user_settings_collection = db.collection('user_settings')
    
    # Auto-fix string dates on startup
    def fix_string_dates():
        """Convert string dates to datetime objects in existing transactions"""
        try:
            for collection_name, collection in [('credit_transactions', credit_collection), ('debit_transactions', debit_collection)]:
                docs = collection.stream()
                fixed_count = 0
                for doc in docs:
                    data = doc.to_dict()
                    date_field = data.get('date')
                    
                    if isinstance(date_field, str):
                        try:
                            parsed_date = datetime.strptime(date_field, '%Y-%m-%d')
                            collection.document(doc.id).update({'date': parsed_date})
                            fixed_count += 1
                        except Exception:
                            pass
                
                if fixed_count > 0:
                    pass
        except Exception as e:
            pass
    
    # Run migration in background
    import threading
    threading.Thread(target=fix_string_dates, daemon=True).start()
else:
    credit_collection = debit_collection = groups_collection = users_collection = user_settings_collection = None

# ── Firebase client config loader ─────────────────────────────────────────────
def load_firebase_config():
    """
    Load Firebase CLIENT config from environment variables.
    ALWAYS returns a dict (never None) so the API endpoint never errors.
    """
    try:
        config = {
            "apiKey": os.getenv('FIREBASE_API_KEY'),
            "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
            "databaseURL": os.getenv('FIREBASE_DATABASE_URL'),
            "projectId": os.getenv('FIREBASE_PROJECT_ID'),
            "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
            "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
            "appId": os.getenv('FIREBASE_APP_ID'),
            "measurementId": os.getenv('FIREBASE_MEASUREMENT_ID')
        }
        
        # Check if all required fields are present
        required_fields = ['apiKey', 'authDomain', 'projectId', 'storageBucket', 'messagingSenderId', 'appId']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            # Return empty config to prevent errors
            return {}
            
        return config
    except Exception as e:
        return {}

# Load once at startup so we can see any errors in the console immediately
FIREBASE_CLIENT_CONFIG = load_firebase_config()

# ── Tesseract ─────────────────────────────────────────────────────────────────
def configure_tesseract():
    """Configure Tesseract OCR path for different environments"""
    # Set environment variable for tessdata
    possible_tessdata_paths = [
        '/usr/share/tesseract-ocr/4.00/tessdata/',
        '/usr/share/tesseract-ocr/5/tessdata/',
        '/usr/share/tessdata/',
        '/usr/local/share/tessdata/',
    ]
    
    for tessdata_path in possible_tessdata_paths:
        if os.path.exists(tessdata_path):
            os.environ['TESSDATA_PREFIX'] = tessdata_path
            print(f"✅ Set TESSDATA_PREFIX to: {tessdata_path}")
            break
    else:
        print("❌ No tessdata directory found")
    
    paths = [
        '/usr/bin/tesseract',  # Docker/Linux (production)
        'tesseract',  # System PATH
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',  # Windows
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',  # Windows x86
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),  # Windows local
    ]
    
    for p in paths:
        if os.path.exists(p) or p == 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = p
            print(f"✅ Tesseract configured at: {p}")
            
            # Test Tesseract configuration
            try:
                version = pytesseract.get_tesseract_version()
                print(f"✅ Tesseract version: {version}")
                
                # Test language availability
                langs = pytesseract.get_languages()
                print(f"✅ Available languages: {langs}")
                
                if 'eng' in langs:
                    print("✅ English language data available")
                else:
                    print("❌ English language data NOT available")
                    
            except Exception as e:
                print(f"❌ Tesseract test failed: {e}")
            
            return
    
    print("❌ Tesseract not found in any expected location")
    # Try to find tesseract in PATH
    import shutil
    tesseract_path = shutil.which('tesseract')
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"✅ Tesseract found in PATH: {tesseract_path}")
    else:
        print("❌ Tesseract not found in PATH either")

configure_tesseract()

# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h    = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
    return salt + h.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        if not stored or len(stored) < 32:
            return False
        salt = stored[:32]
        h    = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
        return h.hex() == stored[32:]
    except Exception:
        return False

# ── Validation ────────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

def valid_email(e: str) -> bool:
    return bool(e and EMAIL_RE.match(e))

# ── Email Notification Helpers ────────────────────────────────────────────────
def send_email_notification(to_email, subject, body):
    """Send email notification using Gmail SMTP"""
    try:
        SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'baluvadla444@gmail.com')
        SENDER_PASSWORD = os.getenv('SENDER_APP_PASSWORD', '').strip()
        
        if not SENDER_PASSWORD:
            return False
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        return False

def send_savings_report_email(user_email, savings_data):
    """Send monthly savings report email"""
    subject = f"💰 Your Monthly Savings Report - {datetime.now().strftime('%B %Y')}"
    
    status_emoji = "🎉" if savings_data['status'] == 'achieved' else ("⚠️" if savings_data['status'] == 'negative' else "📊")
    
    body = f"""Hi there!

Here's your monthly savings report:

{status_emoji} Savings Status: {savings_data['status'].replace('_', ' ').title()}

📊 Summary:
• Income: ₹{savings_data['income']:,.0f}
• Expenses: ₹{savings_data['expenses']:,.0f}
• Savings: ₹{savings_data['current']:,.0f}
• Target: ₹{savings_data['target']:,.0f}
• Progress: {savings_data['percentage']:.1f}%

"""
    
    if savings_data['status'] == 'achieved':
        body += f"🎉 Congratulations! You've achieved your savings goal!\n"
    elif savings_data['status'] == 'negative':
        body += f"⚠️ Your expenses exceeded your income this month. Consider reviewing your spending.\n"
    else:
        body += f"💪 Keep going! You need ₹{savings_data['remaining']:,.0f} more to reach your goal.\n"
    
    body += f"""
Keep tracking your finances with FinAnalyzer!

- FinAnalyzer Team"""
    
    return send_email_notification(user_email, subject, body)

def send_alert_triggered_email(user_email, alert_data):
    """Send spending alert email when limit is exceeded"""
    subject = f"⚠️ Spending Alert: {alert_data['name']}"
    
    period_text = alert_data['type'].title()
    category_text = alert_data['category'] if alert_data['category'] != 'all' else 'All Categories'
    
    body = f"""Hi there!

⚠️ Your spending alert has been triggered!

Alert: {alert_data['name']}
Period: {period_text}
Category: {category_text}

💰 Spending Details:
• Limit: ₹{alert_data['limit']:,.0f}
• Current: ₹{alert_data['current']:,.0f}
• Exceeded by: ₹{(alert_data['current'] - alert_data['limit']):,.0f}
• Percentage: {alert_data['percentage']:.1f}%

💡 Suggestion: Review your {category_text.lower()} spending and consider adjusting your budget.

Stay on track with FinAnalyzer!

- FinAnalyzer Team"""
    
    return send_email_notification(user_email, subject, body)

# ── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated

# ═════════════════════════════ PAGE ROUTES ════════════════════════════════════

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/health')
def health_check():
    """Health check endpoint for deployment monitoring"""
    try:
        # Basic health checks
        checks = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'tesseract': False,
            'firebase': False,
            'firebase_method': 'none',
            'debug_info': {}
        }
        
        # Check Tesseract
        try:
            version = pytesseract.get_tesseract_version()
            checks['tesseract'] = True
            checks['debug_info']['tesseract_version'] = str(version)
            checks['debug_info']['tesseract_path'] = pytesseract.pytesseract.tesseract_cmd
        except Exception as e:
            checks['debug_info']['tesseract_error'] = str(e)
            checks['debug_info']['tesseract_path'] = pytesseract.pytesseract.tesseract_cmd
            
        # Check Firebase connection with detailed info
        try:
            if 'db' in globals() and db is not None:
                # Try a simple database operation
                test_collection = db.collection('health_check')
                test_collection.limit(1).get()
                checks['firebase'] = True
                
                # Determine which method was used
                if os.path.exists("/etc/secrets/FIREBASE_CREDENTIALS.json"):
                    checks['firebase_method'] = 'secret_file'
                elif os.getenv('FIREBASE_CREDENTIALS_JSON'):
                    checks['firebase_method'] = 'env_variable'
                elif os.path.exists('FIREBASE_CREDENTIALS.json'):
                    checks['firebase_method'] = 'local_file'
                else:
                    checks['firebase_method'] = 'unknown'
            else:
                checks['debug_info']['firebase_error'] = 'db is None or not initialized'
                
        except Exception as e:
            checks['debug_info']['firebase_error'] = str(e)
            
        # Add file existence checks for debugging
        checks['debug_info']['files'] = {
            'secret_file_exists': os.path.exists("/etc/secrets/FIREBASE_CREDENTIALS.json"),
            'local_file_exists': os.path.exists("FIREBASE_CREDENTIALS.json"),
            'env_var_exists': bool(os.getenv('FIREBASE_CREDENTIALS_JSON'))
        }
            
        return jsonify(checks), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    return '', 204

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth_page():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    # Pass firebase_config so {{ firebase_config | tojson }} works in auth.html
    return render_template('auth.html', firebase_config=FIREBASE_CLIENT_CONFIG)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html',
                           user_name=session.get('user_name'),
                           active_page='dashboard')

@app.route('/group-dashboard')
@login_required
def group_dashboard():
    return render_template('group_dashboard.html',
                           user_name=session.get('user_name'),
                           active_page='group-dashboard')

@app.route('/upload')
@login_required
def upload_page():
    return render_template('upload.html',
                           user_name=session.get('user_name'),
                           active_page='upload')

@app.route('/upload-bulk')
@login_required
def upload_bulk_page():
    return render_template('upload_multiple.html',
                           user_name=session.get('user_name'),
                           active_page='upload')

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html',
                           user_name=session.get('user_name'),
                           active_page='analytics')

@app.route('/history')
@login_required
def history():
    return render_template('history.html',
                           user_name=session.get('user_name'),
                           active_page='history')

@app.route('/group')
@login_required
def group():
    return render_template('group.html',
                           user_name=session.get('user_name'),
                           active_page='group')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html',
                           user_name=session.get('user_name'),
                           active_page='settings')

# ═════════════════════════════ AUTH API ═══════════════════════════════════════

@app.route('/api/firebase-config')
def firebase_config_route():
    """
    Serves Firebase client config as JSON.
    Used by auth.html and reset_password.html via fetch() instead of Jinja templating.
    This avoids all Jinja-in-script-tag issues.
    """
    return jsonify(FIREBASE_CLIENT_CONFIG)


@app.route('/login', methods=['POST'])
def login():
    try:
        body     = request.get_json(silent=True) or {}
        email    = body.get('email', '').strip().lower()
        password = body.get('password', '')

        if not email:
            return jsonify({'success': False, 'message': 'Please enter your email address.', 'field': 'email'})
        if not valid_email(email):
            return jsonify({'success': False, 'message': 'Please enter a valid email address.', 'field': 'email'})
        if not password:
            return jsonify({'success': False, 'message': 'Please enter your password.', 'field': 'password'})
        if not db or users_collection is None:
            return jsonify({'success': False, 'message': 'Service temporarily unavailable. Please try again.'})

        try:
            doc = users_collection.document(email).get()
        except Exception as e:
            return jsonify({'success': False, 'message': 'Login failed. Please try again.'})

        if not doc.exists:
            return jsonify({
                'success': False,
                'message': 'This email is not registered. Please create an account first.',
                'field'  : 'email'
            })

        user_data   = doc.to_dict()
        stored_hash = user_data.get('password', '')

        if not stored_hash:
            return jsonify({
                'success': False,
                'message': 'Please reset your password using "Forgot password".',
                'field'  : 'password'
            })

        if not verify_password(password, stored_hash):
            return jsonify({
                'success': False,
                'message': 'Wrong password. Please try again.',
                'field'  : 'password'
            })

        display_name          = user_data.get('name') or email.split('@')[0].title()
        session['user_email'] = email
        session['user_name']  = display_name

        try:
            users_collection.document(email).update({'last_login': datetime.now()})
        except Exception:
            pass

        return jsonify({
            'success': True,
            'message': f'Welcome back, {display_name}!',
            'user'   : {'email': email, 'name': display_name}
        })

    except Exception as e:
        return jsonify({'success': False, 'message': 'An unexpected error occurred. Please try again.'})


@app.route('/register', methods=['POST'])
def register():
    try:
        body     = request.get_json(silent=True) or {}
        email    = body.get('email', '').strip().lower()
        password = body.get('password', '')
        name     = body.get('name', '').strip()

        if not email:
            return jsonify({'success': False, 'message': 'Please enter your email address.', 'field': 'email'})
        if not valid_email(email):
            return jsonify({'success': False, 'message': 'Please enter a valid email address.', 'field': 'email'})
        if not name or len(name) < 2:
            return jsonify({'success': False, 'message': 'Please enter your full name.', 'field': 'name'})
        if not password:
            return jsonify({'success': False, 'message': 'Please enter a password.', 'field': 'password'})
        if len(password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters.', 'field': 'password'})
        if not db or users_collection is None:
            return jsonify({'success': False, 'message': 'Service temporarily unavailable. Please try again.'})

        try:
            existing = users_collection.document(email).get()
        except Exception as e:
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'})

        if existing.exists:
            return jsonify({
                'success': False,
                'message': 'An account with this email already exists. Please sign in instead.',
                'field'  : 'email'
            })

        try:
            users_collection.document(email).set({
                'name'              : name,
                'email'             : email,
                'password'          : hash_password(password),
                'created_at'        : datetime.now(),
                'last_login'        : datetime.now(),
                'group_id'          : None,
                'total_transactions': 0,
                'total_spending'    : 0.0,
            })
        except Exception as e:
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'})

        session['user_email'] = email
        session['user_name']  = name

        return jsonify({
            'success': True,
            'message': f'Welcome to FinAnalyzer, {name}! Account created.',
            'user'   : {'email': email, 'name': name}
        })

    except Exception as e:
        return jsonify({'success': False, 'message': 'An unexpected error occurred. Please try again.'})


# ── Forgot password ───────────────────────────────────────────────────────────
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """
    Verifies email exists in Firestore, then ensures a Firebase Auth user exists
    so the frontend can call sendPasswordResetEmail() via Firebase Client SDK.
    """
    try:
        body  = request.get_json(silent=True) or {}
        email = body.get('email', '').strip().lower()

        if not email or not valid_email(email):
            return jsonify({'success': False, 'message': 'Please enter a valid email address.'})

        if not db or users_collection is None:
            return jsonify({'success': False, 'message': 'Service temporarily unavailable.'})

        try:
            doc = users_collection.document(email).get()
        except Exception as e:
            return jsonify({'success': False, 'message': 'Something went wrong. Please try again.'})

        if not doc.exists:
            # Always return success to avoid email enumeration
            return jsonify({'success': True, 'message': 'ok'})

        user_data = doc.to_dict()

        # Ensure user exists in Firebase Auth so reset email can be sent
        try:
            auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            auth.create_user(
                email=email,
                display_name=user_data.get('name', ''),
                email_verified=False
            )
        except Exception as e:
            pass

        return jsonify({'success': True, 'message': 'ok'})

    except Exception as e:
        return jsonify({'success': False, 'message': 'Something went wrong. Please try again.'})


# ── Reset password page ───────────────────────────────────────────────────────
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password_page():
    if request.method == 'GET':
        # Firebase reset emails contain: ?mode=resetPassword&oobCode=XXX&apiKey=YYY
        oob_code = request.args.get('oobCode', '')
        # Pass firebase_config so {{ firebase_config | tojson }} works in reset_password.html
        return render_template(
            'reset_password.html',
            oob_code=oob_code
        )

    # POST — sync new password to Firestore after Firebase Auth confirms it
    try:
        body         = request.get_json(silent=True) or {}
        email        = body.get('email', '').strip().lower()
        new_password = body.get('password', '')

        if not email or not new_password:
            return jsonify({'success': False, 'message': 'Missing required fields.'})
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'})
        if not db or users_collection is None:
            return jsonify({'success': False, 'message': 'Service unavailable.'})

        users_collection.document(email).update({
            'password': hash_password(new_password),
        })
        return jsonify({'success': True, 'message': 'Password updated. You can now sign in.'})

    except Exception as e:
        return jsonify({'success': False, 'message': 'Something went wrong. Please try again.'})

# ═════════════════════════════ TRANSACTION API ════════════════════════════════

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_transaction():
    try:
        file = request.files.get('file') or request.files.get('image')
        if not file or file.filename == '':
            return jsonify({'success': False, 'message': 'No file uploaded.'})
        extracted = extract_transaction_details(file)
        return jsonify({'success': True, 'message': 'File processed.', 'data': extracted})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/save-transaction', methods=['POST'])
@login_required
def save_transaction():
    try:
        data       = request.get_json(silent=True) or {}
        user_email = session.get('user_email')
        # Parse date and time together to create a proper datetime
        date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        time_str = data.get('time', datetime.now().strftime('%H:%M'))
        
        try:
            # Combine date and time into a single datetime object
            datetime_str = f"{date_str} {time_str}"
            transaction_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            # Make it timezone-aware as IST (UTC+5:30)
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            transaction_datetime = transaction_datetime.replace(tzinfo=ist)
        except Exception:
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            transaction_datetime = datetime.now(ist)
        
        tx = {
            'submitted_by': user_email,
            'name'        : data.get('name', ''),
            'amount'      : float(data.get('amount', 0)),
            'payment_type': data.get('payment_type', 'debit'),
            'payee_type'  : data.get('payee_type', 'Other'),
            'date'        : transaction_datetime,
            'time'        : time_str,
            'created_at'  : datetime.now(),
        }
        if db:
            (credit_collection if tx['payment_type'] == 'credit' else debit_collection).add(tx)
        return jsonify({'success': True, 'message': 'Transaction saved.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/save-transactions-bulk', methods=['POST'])
@login_required
def save_transactions_bulk():
    """Save multiple transactions at once"""
    try:
        data = request.get_json(silent=True) or {}
        transactions = data.get('transactions', [])
        user_email = session.get('user_email')
        
        if not transactions:
            return jsonify({'success': False, 'message': 'No transactions provided'})
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        saved_count = 0
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        
        for tx_data in transactions:
            try:
                # Parse date and time
                date_str = tx_data.get('date', datetime.now().strftime('%Y-%m-%d'))
                time_str = tx_data.get('time', datetime.now().strftime('%H:%M'))
                
                try:
                    datetime_str = f"{date_str} {time_str}"
                    transaction_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                    transaction_datetime = transaction_datetime.replace(tzinfo=ist)
                except Exception:
                    transaction_datetime = datetime.now(ist)
                
                tx = {
                    'submitted_by': user_email,
                    'name'        : tx_data.get('name', ''),
                    'amount'      : float(tx_data.get('amount', 0)),
                    'payment_type': tx_data.get('payment_type', 'debit'),
                    'payee_type'  : tx_data.get('payee_type', 'Other'),
                    'date'        : transaction_datetime,
                    'time'        : time_str,
                    'created_at'  : datetime.now(),
                }
                
                (credit_collection if tx['payment_type'] == 'credit' else debit_collection).add(tx)
                saved_count += 1
            except Exception as e:
                continue
        
        return jsonify({
            'success': True,
            'message': f'{saved_count} transactions saved successfully',
            'saved_count': saved_count
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})

        credit_docs = credit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_docs  = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()

        credit_df = pd.DataFrame([d.to_dict() for d in credit_docs])
        debit_df  = pd.DataFrame([d.to_dict() for d in debit_docs])

        total_income   = float(credit_df['amount'].sum()) if not credit_df.empty else 0.0
        total_expenses = float(debit_df['amount'].sum())  if not debit_df.empty  else 0.0
        balance        = total_income - total_expenses

        all_tx = pd.concat([credit_df, debit_df], ignore_index=True) \
            if not credit_df.empty or not debit_df.empty else pd.DataFrame()

        recent = []
        if not all_tx.empty:
            try:
                if 'created_at' in all_tx.columns:
                    all_tx['created_at'] = pd.to_datetime(all_tx['created_at'], errors='coerce', utc=True)
                    all_tx['created_at'] = all_tx['created_at'].fillna(pd.Timestamp.now(tz='UTC'))
                else:
                    all_tx['created_at'] = pd.Timestamp.now(tz='UTC')

                for _, row in all_tx.sort_values('created_at', ascending=False).head(5).iterrows():
                    t = row.to_dict()
                    if 'created_at' in t and pd.notna(t['created_at']):
                        ca = t['created_at']
                        if hasattr(ca, 'tz') and ca.tz is None:
                            ca = ca.tz_localize('UTC')
                        t['created_at'] = ca.isoformat()
                    if 'date' in t:
                        if isinstance(t['date'], datetime):
                            t['date'] = t['date'].isoformat()
                        elif hasattr(t['date'], 'isoformat'):
                            t['date'] = t['date'].isoformat()
                    t.setdefault('name', 'Unknown')
                    t.setdefault('amount', 0)
                    t.setdefault('payment_type', 'debit')
                    t.setdefault('payee_type', 'Other')
                    t.setdefault('date', datetime.now().isoformat())
                    recent.append(t)
            except Exception as err:
                pass

        return jsonify({'success': True, 'data': {
            'total_income'       : total_income,
            'total_expenses'     : total_expenses,
            'balance'            : balance,
            'recent_transactions': recent,
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/transactions')
@login_required
def get_all_transactions():
    """Get ALL transactions for history page"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})

        credit_docs = credit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_docs  = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        
        # Re-fetch since we consumed the iterators
        credit_docs = credit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_docs  = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()

        all_transactions = []
        
        # Process credit transactions
        for doc in credit_docs:
            t = doc.to_dict()
            t['id'] = doc.id
            if 'date' in t:
                if isinstance(t['date'], datetime):
                    t['date'] = t['date'].isoformat()
                elif hasattr(t['date'], 'isoformat'):
                    t['date'] = t['date'].isoformat()
            if 'created_at' in t:
                if isinstance(t['created_at'], datetime):
                    t['created_at'] = t['created_at'].isoformat()
                elif hasattr(t['created_at'], 'isoformat'):
                    t['created_at'] = t['created_at'].isoformat()
            t.setdefault('name', 'Unknown')
            t.setdefault('amount', 0)
            t.setdefault('payment_type', 'credit')
            t.setdefault('payee_type', 'Other')
            t.setdefault('time', '')
            all_transactions.append(t)
        
        # Process debit transactions
        for doc in debit_docs:
            t = doc.to_dict()
            t['id'] = doc.id
            if 'date' in t:
                if isinstance(t['date'], datetime):
                    t['date'] = t['date'].isoformat()
                elif hasattr(t['date'], 'isoformat'):
                    t['date'] = t['date'].isoformat()
            if 'created_at' in t:
                if isinstance(t['created_at'], datetime):
                    t['created_at'] = t['created_at'].isoformat()
                elif hasattr(t['created_at'], 'isoformat'):
                    t['created_at'] = t['created_at'].isoformat()
            t.setdefault('name', 'Unknown')
            t.setdefault('amount', 0)
            t.setdefault('payment_type', 'debit')
            t.setdefault('payee_type', 'Other')
            t.setdefault('time', '')
            all_transactions.append(t)

        return jsonify({'success': True, 'transactions': all_transactions})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/transaction/<transaction_id>', methods=['DELETE', 'PUT'])
@login_required
def manage_transaction(transaction_id):
    """Delete or update a transaction"""
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        
        if request.method == 'DELETE':
            # Try to find and delete from credit collection
            try:
                doc = credit_collection.document(transaction_id).get()
                if doc.exists and doc.to_dict().get('submitted_by') == user_email:
                    credit_collection.document(transaction_id).delete()
                    return jsonify({'success': True, 'message': 'Transaction deleted'})
            except Exception:
                pass
            
            # Try to find and delete from debit collection
            try:
                doc = debit_collection.document(transaction_id).get()
                if doc.exists and doc.to_dict().get('submitted_by') == user_email:
                    debit_collection.document(transaction_id).delete()
                    return jsonify({'success': True, 'message': 'Transaction deleted'})
            except Exception:
                pass
            
            return jsonify({'success': False, 'message': 'Transaction not found or unauthorized'})
        
        elif request.method == 'PUT':
            data = request.get_json(silent=True) or {}
            
            # Parse date and time
            date_str = data.get('date', datetime.now().strftime('%Y-%m-%d'))
            time_str = data.get('time', datetime.now().strftime('%H:%M'))
            
            try:
                datetime_str = f"{date_str} {time_str}"
                transaction_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
                # Make it timezone-aware as IST (UTC+5:30)
                from datetime import timezone, timedelta
                ist = timezone(timedelta(hours=5, minutes=30))
                transaction_datetime = transaction_datetime.replace(tzinfo=ist)
            except Exception:
                from datetime import timezone, timedelta
                ist = timezone(timedelta(hours=5, minutes=30))
                transaction_datetime = datetime.now(ist)
            
            update_data = {
                'name': data.get('name', ''),
                'amount': float(data.get('amount', 0)),
                'payment_type': data.get('payment_type', 'debit'),
                'payee_type': data.get('payee_type', 'Other'),
                'date': transaction_datetime,
                'time': time_str,
            }
            
            old_type = None
            new_type = data.get('payment_type', 'debit')
            
            # Find the transaction in credit collection
            try:
                doc = credit_collection.document(transaction_id).get()
                if doc.exists and doc.to_dict().get('submitted_by') == user_email:
                    old_type = 'credit'
                    if new_type == 'credit':
                        # Update in same collection
                        credit_collection.document(transaction_id).update(update_data)
                        return jsonify({'success': True, 'message': 'Transaction updated'})
                    else:
                        # Move to debit collection
                        update_data['submitted_by'] = user_email
                        update_data['created_at'] = doc.to_dict().get('created_at', datetime.now())
                        debit_collection.add(update_data)
                        credit_collection.document(transaction_id).delete()
                        return jsonify({'success': True, 'message': 'Transaction updated'})
            except Exception:
                pass
            
            # Find the transaction in debit collection
            try:
                doc = debit_collection.document(transaction_id).get()
                if doc.exists and doc.to_dict().get('submitted_by') == user_email:
                    old_type = 'debit'
                    if new_type == 'debit':
                        # Update in same collection
                        debit_collection.document(transaction_id).update(update_data)
                        return jsonify({'success': True, 'message': 'Transaction updated'})
                    else:
                        # Move to credit collection
                        update_data['submitted_by'] = user_email
                        update_data['created_at'] = doc.to_dict().get('created_at', datetime.now())
                        credit_collection.add(update_data)
                        debit_collection.document(transaction_id).delete()
                        return jsonify({'success': True, 'message': 'Transaction updated'})
            except Exception:
                pass
            
            return jsonify({'success': False, 'message': 'Transaction not found or unauthorized'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/spending-categories')
@login_required
def spending_categories():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        debit_docs = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_df   = pd.DataFrame([d.to_dict() for d in debit_docs])
        categories = {}
        if not debit_df.empty:
            cats = debit_df.groupby('payee_type')['amount'].sum()
            categories = {str(k): float(v) for k, v in cats.items()}
        return jsonify({'success': True, 'data': categories})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/analytics-data')
@login_required
def analytics_data():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})

        credit_docs = credit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_docs  = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()

        credit_df = pd.DataFrame([d.to_dict() for d in credit_docs])
        debit_df  = pd.DataFrame([d.to_dict() for d in debit_docs])
        all_tx    = pd.concat([credit_df, debit_df], ignore_index=True) \
            if not credit_df.empty or not debit_df.empty else pd.DataFrame()

        if all_tx.empty:
            return jsonify({'success': True, 'data': {
                'savings_suggestions': [], 'spending_comparison': {},
                'cash_flow': {'inflows': 0, 'outflows': 0},
                'alerts': [], 'peak_times': [],
                'all_transactions': [],
            }, 'message': 'No transactions yet.'})

        # Serialize all transactions for frontend charts
        all_transactions_list = []
        for _, row in all_tx.iterrows():
            t = {}
            for key, value in row.to_dict().items():
                # Handle datetime/Timestamp objects
                if pd.isna(value):
                    t[key] = None
                elif isinstance(value, (datetime, pd.Timestamp)):
                    t[key] = value.isoformat()
                elif hasattr(value, 'isoformat'):
                    t[key] = value.isoformat()
                elif isinstance(value, (np.integer, np.floating)):
                    t[key] = float(value)
                else:
                    t[key] = value
            all_transactions_list.append(t)

        inflows, outflows = cash_flow_analysis(credit_df, debit_df)
        return jsonify({'success': True, 'data': {
            'savings_suggestions': get_savings_suggestions(debit_df),
            'spending_comparison': compare_spending(all_tx),
            'cash_flow'          : {'inflows': inflows, 'outflows': outflows},
            'alerts'             : spending_alerts(all_tx),
            'peak_times'         : get_top_time_intervals(credit_df, debit_df),
            'all_transactions'   : all_transactions_list,
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ═════════════════════════════ OCR HELPERS ════════════════════════════════════

def extract_transaction_details(file):
    """Extract transaction details from uploaded image using OCR."""
    try:
        print("🔍 Starting OCR extraction...")
        image = Image.open(file.stream)
        print(f"📷 Image: {image.size}, mode: {image.mode}")
        
        # Grayscale + light contrast boost (don't over-threshold — it destroys ₹)
        image = image.convert('L')
        # Use a softer threshold (128 instead of 150) — high threshold destroys
        # complex glyphs like ₹ which have thin strokes
        image = image.point(lambda x: 0 if x < 128 else 255)
        
        # PSM 6 = assume uniform block of text (good for receipts)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        print(f"📝 OCR text ({len(text)} chars): {repr(text[:300])}")
        
        if not text or len(text.strip()) < 5:
            print("❌ OCR returned empty text")
            return _empty_tx()
        
        return parse_transaction_text(text)
    except Exception as e:
        print(f"❌ OCR extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return _empty_tx()


def parse_transaction_text(text: str) -> dict:
    """Parse OCR text from a UPI/bank receipt.
    Returns a dict with: name, amount, payment_type, payee_type, date, time
    """
    print(f"🔍 Parsing text: {repr(text[:120])}...")
    
    details = _empty_tx()
    tl = text.lower()

    # ── 1. Payment type ───────────────────────────────────────────────────────
    if re.search(r'\b(credited|received\s+from|money\s+received)\b', tl):
        details['payment_type'] = 'credit'
        print("💰 Detected: CREDIT")
    elif re.search(r'\b(debited|paid\s+to|payment\s+to|sent\s+to)\b', tl):
        details['payment_type'] = 'debit'
        print("💸 Detected: DEBIT")

    # ── 2. Normalize rupee symbol BEFORE any amount extraction ───────────────
    normalized = normalize_rupee(text)
    print(f"🔧 Normalized: {repr(normalized[:120])}")

    # ── 3. Date & time (unchanged — your existing logic works well) ──────────
    date_time = re.search(r'(\d{1,2}:\d{2}\s*[APap][Mm])\s*on\s*(\d{1,2}\s+\w+\s+\d{4})', text)
    if date_time:
        try:
            dt_str = f"{date_time.group(2).strip()} {date_time.group(1).strip()}"
            dt_obj = datetime.strptime(dt_str, '%d %b %Y %I:%M %p')
            details['date'] = dt_obj.strftime('%Y-%m-%d')
            details['time'] = dt_obj.strftime('%H:%M')
            print(f"📅 Date: {details['date']} {details['time']}")
        except ValueError as e:
            print(f"❌ Date parse error: {e}")

    # ── 4. Amount (anchor-relative, skips "Debited from" duplicate) ──────────
    details['amount'] = extract_amount(normalized)
    print(f"� Amount: {details['amount']}")

    # ── 5. Name (anchor-relative) ─────────────────────────────────────────────
    details['name'] = extract_name(normalized, details['payment_type'])
    print(f"👤 Name: {details['name']}")

    # ── 6. Category (unchanged) ───────────────────────────────────────────────
    categories = {
        'Food':          ['restaurant', 'food', 'zomato', 'swiggy', 'cafe', 'hotel', 'dining'],
        'Transport':     ['uber', 'ola', 'metro', 'bus', 'taxi', 'petrol', 'fuel', 'rapido'],
        'Entertainment': ['movie', 'cinema', 'netflix', 'spotify', 'bookmyshow'],
        'Utilities':     ['electricity', 'water', 'gas', 'internet', 'mobile', 'recharge', 'bill'],
        'Shopping':      ['amazon', 'flipkart', 'mall', 'store', 'shop', 'myntra'],
        'Government':    ['passport', 'seva', 'gov', 'government', 'tax', 'license'],
    }
    
    for category, keywords in categories.items():
        if any(k in tl for k in keywords):
            details['payee_type'] = category
            break

    print(f"📋 Final: {details}")
    return details


def _empty_tx():
    return {
        'name': '', 'amount': '', 'payment_type': 'debit',
        'payee_type': 'Other',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
    }

# ═════════════════════════════ GROUP API ══════════════════════════════════════

@app.route('/api/groups', methods=['GET'])
@login_required
def get_all_groups():
    """Get all groups where user is a member"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get all groups
        all_groups = groups_collection.stream()
        user_groups = []
        
        for doc in all_groups:
            group_data = doc.to_dict()
            
            # Check if user is a member
            is_member = any(m.get('email') == user_email for m in group_data.get('members', []))
            
            if is_member and not group_data.get('is_archived', False):
                group_data['id'] = doc.id
                
                # Convert datetime to ISO format
                if 'created_at' in group_data and isinstance(group_data['created_at'], datetime):
                    group_data['created_at'] = group_data['created_at'].isoformat()
                if 'updated_at' in group_data and isinstance(group_data['updated_at'], datetime):
                    group_data['updated_at'] = group_data['updated_at'].isoformat()
                
                # Convert member dates
                for member in group_data.get('members', []):
                    if 'joined_at' in member and isinstance(member['joined_at'], datetime):
                        member['joined_at'] = member['joined_at'].isoformat()
                
                user_groups.append(group_data)
        
        return jsonify({'success': True, 'groups': user_groups})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>', methods=['GET'])
@login_required
def get_group_detail(group_id):
    """Get single group details"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        group_data['id'] = group.id
        
        # Check if user is member
        is_member = any(m.get('email') == user_email for m in group_data.get('members', []))
        if not is_member:
            return jsonify({'success': False, 'message': 'You are not a member of this group'})
        
        # Convert datetime to ISO format
        if 'created_at' in group_data and isinstance(group_data['created_at'], datetime):
            group_data['created_at'] = group_data['created_at'].isoformat()
        if 'updated_at' in group_data and isinstance(group_data['updated_at'], datetime):
            group_data['updated_at'] = group_data['updated_at'].isoformat()
        
        for member in group_data.get('members', []):
            if 'joined_at' in member and isinstance(member['joined_at'], datetime):
                member['joined_at'] = member['joined_at'].isoformat()
        
        return jsonify({'success': True, 'data': group_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/create-group', methods=['POST'])
@login_required
def create_group():
    """Create a new group with enhanced features"""
    try:
        data = request.get_json(silent=True) or {}
        user_email = session.get('user_email')
        user_name = session.get('user_name', user_email.split('@')[0])
        
        # Generate unique invite code
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        group = {
            # Basic info
            'name': data.get('name', 'Untitled Group'),
            'description': data.get('description', ''),
            'type': data.get('type', 'Other'),  # Family, Friends, Roommates, Trip, Project, Other
            
            # Visual customization
            'avatar': data.get('avatar', ''),  # URL or base64
            'color': data.get('color', '#6366f1'),  # Hex color
            
            # Settings
            'currency': data.get('currency', 'INR'),
            'privacy': data.get('privacy', 'private'),  # public/private
            'auto_approve': data.get('auto_approve', False),
            
            # Access control
            'invite_code': invite_code,
            'admin_email': user_email,
            
            # Members
            'members': [{
                'email': user_email,
                'name': user_name,
                'role': 'admin',  # admin, member, viewer
                'status': 'active',
                'joined_at': datetime.now(),
                'total_spending': 0,
                'transaction_count': 0
            }],
            
            # Stats
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'total_transactions': 0,
            'total_spending': 0,
            'is_archived': False,
            
            # Notifications
            'notification_settings': {
                'new_expense': True,
                'payment_received': True,
                'member_joined': True,
                'budget_alert': True
            }
        }
        
        if db:
            doc_ref = groups_collection.add(group)
            group['id'] = doc_ref[1].id
            
        return jsonify({'success': True, 'group': group, 'message': 'Group created successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/settings', methods=['PUT'])
@login_required
def update_group_settings(group_id):
    """Update group settings (3.1-3.8)"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get group
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is admin
        is_admin = group_data.get('admin_email') == user_email
        if not is_admin:
            # Check if user has admin role in members
            for member in group_data.get('members', []):
                if member.get('email') == user_email and member.get('role') == 'admin':
                    is_admin = True
                    break
        
        if not is_admin:
            return jsonify({'success': False, 'message': 'Only admins can update group settings'})
        
        # Update fields
        updates = {'updated_at': datetime.now()}
        
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        if 'avatar' in data:
            updates['avatar'] = data['avatar']
        if 'color' in data:
            updates['color'] = data['color']
        if 'type' in data:
            updates['type'] = data['type']
        if 'currency' in data:
            updates['currency'] = data['currency']
        if 'privacy' in data:
            updates['privacy'] = data['privacy']
        if 'auto_approve' in data:
            updates['auto_approve'] = data['auto_approve']
        if 'notification_settings' in data:
            updates['notification_settings'] = data['notification_settings']
        
        # Regenerate invite code if requested
        if data.get('regenerate_invite_code'):
            updates['invite_code'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        group_ref.update(updates)
        
        return jsonify({'success': True, 'message': 'Group settings updated', 'updates': updates})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/archive', methods=['POST'])
@login_required
def archive_group(group_id):
    """Archive/unarchive group (3.6)"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check admin
        if group_data.get('admin_email') != user_email:
            return jsonify({'success': False, 'message': 'Only admin can archive group'})
        
        is_archived = data.get('archive', True)
        group_ref.update({
            'is_archived': is_archived,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': f"Group {'archived' if is_archived else 'unarchived'} successfully"})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/delete', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """Delete group permanently (3.5)"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Only admin can delete
        if group_data.get('admin_email') != user_email:
            return jsonify({'success': False, 'message': 'Only admin can delete group'})
        
        # Delete the group
        group_ref.delete()
        
        return jsonify({'success': True, 'message': 'Group deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/members', methods=['GET'])
@login_required
def get_group_members(group_id):
    """Get all group members with details (2.4, 2.9, 2.10)"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is member
        is_member = any(m.get('email') == user_email for m in group_data.get('members', []))
        if not is_member:
            return jsonify({'success': False, 'message': 'You are not a member of this group'})
        
        members = group_data.get('members', [])
        
        # Format member data
        formatted_members = []
        for member in members:
            formatted_members.append({
                'email': member.get('email'),
                'name': member.get('name'),
                'role': member.get('role', 'member'),
                'status': member.get('status', 'active'),
                'joined_at': member.get('joined_at').isoformat() if isinstance(member.get('joined_at'), datetime) else member.get('joined_at'),
                'total_spending': member.get('total_spending', 0),
                'transaction_count': member.get('transaction_count', 0)
            })
        
        return jsonify({'success': True, 'members': formatted_members})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/member/<member_email>', methods=['DELETE'])
@login_required
def remove_member(group_id, member_email):
    """Remove member from group (2.6)"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is admin
        is_admin = group_data.get('admin_email') == user_email
        if not is_admin:
            for member in group_data.get('members', []):
                if member.get('email') == user_email and member.get('role') == 'admin':
                    is_admin = True
                    break
        
        if not is_admin:
            return jsonify({'success': False, 'message': 'Only admins can remove members'})
        
        # Cannot remove admin
        if member_email == group_data.get('admin_email'):
            return jsonify({'success': False, 'message': 'Cannot remove group owner'})
        
        # Remove member
        members = group_data.get('members', [])
        members = [m for m in members if m.get('email') != member_email]
        
        group_ref.update({
            'members': members,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': 'Member removed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/member/role', methods=['PUT'])
@login_required
def update_member_role(group_id):
    """Assign member roles (2.5)"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        member_email = data.get('member_email')
        new_role = data.get('role')  # admin, member, viewer
        
        if not member_email or not new_role:
            return jsonify({'success': False, 'message': 'Member email and role required'})
        
        if new_role not in ['admin', 'member', 'viewer']:
            return jsonify({'success': False, 'message': 'Invalid role'})
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is admin
        if group_data.get('admin_email') != user_email:
            return jsonify({'success': False, 'message': 'Only group owner can change roles'})
        
        # Update member role
        members = group_data.get('members', [])
        updated = False
        for member in members:
            if member.get('email') == member_email:
                member['role'] = new_role
                updated = True
                break
        
        if not updated:
            return jsonify({'success': False, 'message': 'Member not found'})
        
        group_ref.update({
            'members': members,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': f"Member role updated to {new_role}"})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/transfer-ownership', methods=['POST'])
@login_required
def transfer_ownership(group_id):
    """Transfer group ownership (2.8)"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        new_admin_email = data.get('new_admin_email')
        
        if not new_admin_email:
            return jsonify({'success': False, 'message': 'New admin email required'})
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Only current admin can transfer
        if group_data.get('admin_email') != user_email:
            return jsonify({'success': False, 'message': 'Only current admin can transfer ownership'})
        
        # Check if new admin is a member
        members = group_data.get('members', [])
        new_admin_exists = False
        for member in members:
            if member.get('email') == new_admin_email:
                new_admin_exists = True
                member['role'] = 'admin'
            elif member.get('email') == user_email:
                member['role'] = 'member'
        
        if not new_admin_exists:
            return jsonify({'success': False, 'message': 'New admin must be a group member'})
        
        group_ref.update({
            'admin_email': new_admin_email,
            'members': members,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': 'Ownership transferred successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/invite-link', methods=['GET'])
@login_required
def get_invite_link(group_id):
    """Generate shareable invite link (2.3)"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is member
        is_member = any(m.get('email') == user_email for m in group_data.get('members', []))
        if not is_member:
            return jsonify({'success': False, 'message': 'You are not a member of this group'})
        
        invite_code = group_data.get('invite_code')
        base_url = request.host_url.rstrip('/')
        invite_link = f"{base_url}/group/join?code={invite_code}"
        
        return jsonify({
            'success': True,
            'invite_code': invite_code,
            'invite_link': invite_link,
            'group_name': group_data.get('name')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/invite-email', methods=['POST'])
@login_required
def invite_by_email(group_id):
    """Invite member via email"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        invite_email = data.get('email')
        
        if not invite_email:
            return jsonify({'success': False, 'message': 'Email required'})
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is member
        is_member = any(m.get('email') == user_email for m in group_data.get('members', []))
        if not is_member:
            return jsonify({'success': False, 'message': 'You are not a member of this group'})
        
        # Check if email already a member
        if any(m.get('email') == invite_email for m in group_data.get('members', [])):
            return jsonify({'success': False, 'message': 'User is already a member'})
        
        invite_code = group_data.get('invite_code')
        group_name = group_data.get('name')
        inviter_name = session.get('user_name', user_email)
        
        # Send email
        SENDER_EMAIL = "baluvadla444@gmail.com"
        SENDER_PASSWORD = os.getenv('SENDER_APP_PASSWORD', '').strip()
        
        if not SENDER_PASSWORD:
            return jsonify({
                'success': False,
                'message': f'Email password not configured. Share this code manually: {invite_code}'
            })
        
        try:
            # Email message
            message = f"""Hi!

{inviter_name} invited you to join "{group_name}" on FinAnalyzer.

Your invite code: {invite_code}

Go to the Groups page and enter this code to join.

- FinAnalyzer Team"""
            
            msg = MIMEText(message)
            msg['Subject'] = f'Join "{group_name}" - Code: {invite_code}'
            msg['From'] = SENDER_EMAIL
            msg['To'] = invite_email
            
            # Send via Gmail
            with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            
            return jsonify({
                'success': True,
                'message': f'Invite sent to {invite_email}'
            })
            
        except smtplib.SMTPAuthenticationError:
            return jsonify({
                'success': False,
                'message': f'Gmail authentication failed. Check app password. Code: {invite_code}'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Email error: {str(e)}. Share code manually: {invite_code}'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/join-group', methods=['POST'])
@login_required
def join_group():
    """Join group via invite code with auto-approve support"""
    try:
        data = request.get_json(silent=True) or {}
        invite_code = data.get('invite_code')
        user_email = session.get('user_email')
        user_name = session.get('user_name', user_email.split('@')[0])
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        
        groups = groups_collection.where(filter=FieldFilter('invite_code', '==', invite_code)).get()
        if not groups:
            return jsonify({'success': False, 'message': 'Invalid invite code.'})
        
        group_doc = groups[0]
        group_data = group_doc.to_dict()
        
        # Check if already a member
        if any(m['email'] == user_email for m in group_data.get('members', [])):
            return jsonify({'success': False, 'message': 'You are already a member of this group.'})
        
        # Check auto-approve setting
        auto_approve = group_data.get('auto_approve', False)
        
        new_member = {
            'email': user_email,
            'name': user_name,
            'role': 'member',
            'status': 'active' if auto_approve else 'pending',
            'joined_at': datetime.now(),
            'total_spending': 0,
            'transaction_count': 0
        }
        
        group_data['members'].append(new_member)
        group_doc.reference.update({
            'members': group_data['members'],
            'updated_at': datetime.now()
        })
        
        message = 'Joined group successfully!' if auto_approve else 'Join request sent. Waiting for admin approval.'
        
        return jsonify({
            'success': True,
            'group': group_data,
            'message': message,
            'status': 'active' if auto_approve else 'pending'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group/<group_id>/leave', methods=['POST'])
@login_required
def leave_group(group_id):
    """Leave group (2.7)"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Admin cannot leave - must transfer ownership first
        if group_data.get('admin_email') == user_email:
            return jsonify({'success': False, 'message': 'Admin must transfer ownership before leaving'})
        
        # Remove user from members
        members = [m for m in group_data.get('members', []) if m['email'] != user_email]
        
        group_ref.update({
            'members': members,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': 'Left group successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/send-group-invite', methods=['POST'])
@login_required
def send_group_invite():
    try:
        data  = request.get_json(silent=True) or {}
        email = data.get('email', '')
        return jsonify({'success': True, 'message': f'Invitation sent to {email}.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# SAVINGS GOALS & ALERTS APIs
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/user-settings', methods=['GET'])
@login_required
def get_user_settings():
    """Get user's savings goals and alert settings"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get or create user settings
        settings_ref = user_settings_collection.document(user_email)
        settings_doc = settings_ref.get()
        
        if settings_doc.exists:
            settings = settings_doc.to_dict()
        else:
            # Create default settings
            settings = {
                'savings_goal': {
                    'monthly_target': 0,
                    'enabled': False
                },
                'spending_alerts': [],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            settings_ref.set(settings)
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/user-settings/savings-goal', methods=['PUT'])
@login_required
def update_savings_goal():
    """Update user's monthly savings goal"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        monthly_target = float(data.get('monthly_target', 0))
        enabled = data.get('enabled', True)
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        settings_ref = user_settings_collection.document(user_email)
        settings_ref.set({
            'savings_goal': {
                'monthly_target': monthly_target,
                'enabled': enabled,
                'updated_at': datetime.now()
            },
            'updated_at': datetime.now()
        }, merge=True)
        
        return jsonify({'success': True, 'message': 'Savings goal updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/user-settings/spending-alerts', methods=['POST'])
@login_required
def add_spending_alert():
    """Add a new spending alert"""
    try:
        user_email = session.get('user_email')
        data = request.get_json(silent=True) or {}
        
        alert = {
            'id': secrets.token_hex(8),
            'name': data.get('name', 'Alert'),
            'type': data.get('type', 'monthly'),  # daily, weekly, monthly
            'limit': float(data.get('limit', 0)),
            'category': data.get('category', 'all'),  # all or specific category
            'enabled': True,
            'created_at': datetime.now()
        }
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        settings_ref = user_settings_collection.document(user_email)
        settings_doc = settings_ref.get()
        
        if settings_doc.exists:
            settings = settings_doc.to_dict()
            alerts = settings.get('spending_alerts', [])
        else:
            alerts = []
        
        alerts.append(alert)
        
        settings_ref.set({
            'spending_alerts': alerts,
            'updated_at': datetime.now()
        }, merge=True)
        
        return jsonify({'success': True, 'message': 'Alert added', 'alert': alert})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/user-settings/spending-alerts/<alert_id>', methods=['DELETE'])
@login_required
def delete_spending_alert(alert_id):
    """Delete a spending alert"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        settings_ref = user_settings_collection.document(user_email)
        settings_doc = settings_ref.get()
        
        if not settings_doc.exists:
            return jsonify({'success': False, 'message': 'Settings not found'})
        
        settings = settings_doc.to_dict()
        alerts = settings.get('spending_alerts', [])
        
        # Remove alert with matching ID
        alerts = [a for a in alerts if a.get('id') != alert_id]
        
        settings_ref.update({
            'spending_alerts': alerts,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': 'Alert deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/user-settings/spending-alerts/<alert_id>/toggle', methods=['PUT'])
@login_required
def toggle_spending_alert(alert_id):
    """Enable/disable a spending alert"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        settings_ref = user_settings_collection.document(user_email)
        settings_doc = settings_ref.get()
        
        if not settings_doc.exists:
            return jsonify({'success': False, 'message': 'Settings not found'})
        
        settings = settings_doc.to_dict()
        alerts = settings.get('spending_alerts', [])
        
        # Toggle alert
        for alert in alerts:
            if alert.get('id') == alert_id:
                alert['enabled'] = not alert.get('enabled', True)
                break
        
        settings_ref.update({
            'spending_alerts': alerts,
            'updated_at': datetime.now()
        })
        
        return jsonify({'success': True, 'message': 'Alert toggled'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/dashboard-alerts', methods=['GET'])
@login_required
def get_dashboard_alerts():
    """Get active alerts and savings progress for dashboard"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get user settings
        settings_ref = user_settings_collection.document(user_email)
        settings_doc = settings_ref.get()
        
        if not settings_doc.exists:
            return jsonify({
                'success': True,
                'savings_progress': None,
                'triggered_alerts': [],
                'has_income': False
            })
        
        settings = settings_doc.to_dict()
        
        # Get current date ranges
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        
        # Month start
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Week start (Monday)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Day start
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Year start
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get transactions
        credit_docs = credit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        debit_docs = debit_collection.where(filter=FieldFilter('submitted_by', '==', user_email)).get()
        
        # Calculate totals for different periods
        month_income = 0
        month_expenses = 0
        week_income = 0
        week_expenses = 0
        day_income = 0
        day_expenses = 0
        year_income = 0
        year_expenses = 0
        
        month_category_expenses = {}
        week_category_expenses = {}
        day_category_expenses = {}
        year_category_expenses = {}
        
        month_category_income = {}
        week_category_income = {}
        day_category_income = {}
        year_category_income = {}
        
        # Process credits (income)
        for doc in credit_docs:
            t = doc.to_dict()
            t_date = t.get('date')
            if isinstance(t_date, datetime):
                amount = float(t.get('amount', 0))
                category = t.get('payee_type', 'Other')
                
                if t_date >= month_start:
                    month_income += amount
                    month_category_income[category] = month_category_income.get(category, 0) + amount
                if t_date >= week_start:
                    week_income += amount
                    week_category_income[category] = week_category_income.get(category, 0) + amount
                if t_date >= day_start:
                    day_income += amount
                    day_category_income[category] = day_category_income.get(category, 0) + amount
                if t_date >= year_start:
                    year_income += amount
                    year_category_income[category] = year_category_income.get(category, 0) + amount
        
        # Process debits (expenses)
        for doc in debit_docs:
            t = doc.to_dict()
            t_date = t.get('date')
            if isinstance(t_date, datetime):
                amount = float(t.get('amount', 0))
                category = t.get('payee_type', 'Other')
                
                # Monthly
                if t_date >= month_start:
                    month_expenses += amount
                    month_category_expenses[category] = month_category_expenses.get(category, 0) + amount
                
                # Weekly
                if t_date >= week_start:
                    week_expenses += amount
                    week_category_expenses[category] = week_category_expenses.get(category, 0) + amount
                
                # Daily
                if t_date >= day_start:
                    day_expenses += amount
                    day_category_expenses[category] = day_category_expenses.get(category, 0) + amount
                
                # Yearly
                if t_date >= year_start:
                    year_expenses += amount
                    year_category_expenses[category] = year_category_expenses.get(category, 0) + amount
        
        # Calculate savings progress (only if user has income)
        savings_progress = None
        has_income = month_income > 0
        
        savings_goal = settings.get('savings_goal', {})
        if savings_goal.get('enabled') and has_income:
            target = savings_goal.get('monthly_target', 0)
            current_savings = month_income - month_expenses
            percentage = (current_savings / target * 100) if target > 0 else 0
            
            savings_progress = {
                'target': target,
                'current': current_savings,
                'income': month_income,
                'expenses': month_expenses,
                'percentage': percentage,
                'remaining': max(target - current_savings, 0),
                'status': 'achieved' if current_savings >= target else ('negative' if current_savings < 0 else 'in_progress')
            }
        
        # Check spending alerts (debit only)
        triggered_alerts = []
        spending_alerts = settings.get('spending_alerts', [])
        
        # Track seen alerts by unique combination to prevent duplicates
        seen_alerts = set()
        
        for alert in spending_alerts:
            if not alert.get('enabled', True):
                continue
            
            alert_type = alert.get('type', 'monthly')
            limit = alert.get('limit', 0)
            category = alert.get('category', 'all')
            transaction_type = alert.get('transaction_type', 'debit')
            alert_name = alert.get('name', 'Alert')
            
            # Only process debit (spending) alerts
            if transaction_type != 'debit':
                continue
            
            # Create unique key to detect duplicates
            alert_key = f"{alert_name}|{alert_type}|{category}|{limit}"
            if alert_key in seen_alerts:
                continue
            
            # Calculate spending for alert period
            amount = 0
            if alert_type == 'daily':
                amount = day_expenses if category == 'all' else day_category_expenses.get(category, 0)
            elif alert_type == 'weekly':
                amount = week_expenses if category == 'all' else week_category_expenses.get(category, 0)
            elif alert_type == 'monthly':
                amount = month_expenses if category == 'all' else month_category_expenses.get(category, 0)
            elif alert_type == 'yearly':
                amount = year_expenses if category == 'all' else year_category_expenses.get(category, 0)
            
            # Trigger if spending >= limit
            if amount >= limit:
                seen_alerts.add(alert_key)
                triggered_alerts.append({
                    'id': alert.get('id'),
                    'name': alert_name,
                    'type': alert_type,
                    'limit': limit,
                    'current': amount,
                    'category': category,
                    'transaction_type': 'debit',
                    'percentage': (amount / limit * 100) if limit > 0 else 0
                })
        
        return jsonify({
            'success': True,
            'savings_progress': savings_progress,
            'triggered_alerts': triggered_alerts,
            'has_income': has_income
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/send-savings-email', methods=['POST'])
@login_required
def send_savings_email():
    """Manually send savings report email"""
    try:
        user_email = session.get('user_email')
        
        # Get current savings data
        response = get_dashboard_alerts()
        data = response.get_json()
        
        if not data.get('success') or not data.get('savings_progress'):
            return jsonify({'success': False, 'message': 'No savings data available'})
        
        savings_data = data['savings_progress']
        
        # Send email
        if send_savings_report_email(user_email, savings_data):
            return jsonify({'success': True, 'message': 'Savings report sent to your email'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send email'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/send-alert-email/<alert_id>', methods=['POST'])
@login_required
def send_alert_email(alert_id):
    """Manually send alert email"""
    try:
        user_email = session.get('user_email')
        
        # Get triggered alerts
        response = get_dashboard_alerts()
        data = response.get_json()
        
        if not data.get('success'):
            return jsonify({'success': False, 'message': 'Failed to get alert data'})
        
        # Find the specific alert
        alert_data = None
        for alert in data.get('triggered_alerts', []):
            if alert.get('id') == alert_id:
                alert_data = alert
                break
        
        if not alert_data:
            return jsonify({'success': False, 'message': 'Alert not found'})
        
        # Send email
        if send_alert_triggered_email(user_email, alert_data):
            return jsonify({'success': True, 'message': 'Alert email sent'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send email'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# GROUP ANALYTICS & REPORTS APIs
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/group-analytics/summary', methods=['GET'])
@login_required
def group_analytics_summary():
    """Get summary of all user's groups with basic stats"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get all groups where user is a member
        all_groups = groups_collection.get()
        user_groups = []
        
        for group_doc in all_groups:
            group_data = group_doc.to_dict()
            group_data['id'] = group_doc.id
            
            # Check if user is member
            if any(m.get('email') == user_email for m in group_data.get('members', [])):
                # Get all member emails
                member_emails = [m.get('email') for m in group_data.get('members', [])]
                
                # Get transactions from all group members
                group_transactions = []
                
                for member_email in member_emails:
                    # Get credit transactions
                    credits = credit_collection.where(filter=FieldFilter('submitted_by', '==', member_email)).get()
                    for t in credits:
                        t_data = t.to_dict()
                        t_data['payment_type'] = 'credit'
                        group_transactions.append(t_data)
                    
                    # Get debit transactions
                    debits = debit_collection.where(filter=FieldFilter('submitted_by', '==', member_email)).get()
                    for t in debits:
                        t_data = t.to_dict()
                        t_data['payment_type'] = 'debit'
                        group_transactions.append(t_data)
                
                # Calculate stats
                total_spending = sum(float(t.get('amount', 0)) for t in group_transactions if t['payment_type'] == 'debit')
                total_income = sum(float(t.get('amount', 0)) for t in group_transactions if t['payment_type'] == 'credit')
                transaction_count = len(group_transactions)
                member_count = len(group_data.get('members', []))
                
                user_groups.append({
                    'id': group_doc.id,
                    'name': group_data.get('name'),
                    'type': group_data.get('type'),
                    'color': group_data.get('color'),
                    'member_count': member_count,
                    'total_spending': total_spending,
                    'total_income': total_income,
                    'transaction_count': transaction_count,
                    'is_admin': group_data.get('admin_email') == user_email
                })
        
        return jsonify({'success': True, 'groups': user_groups})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/group-analytics/<group_id>', methods=['GET'])
@login_required
def group_analytics_detail(group_id):
    """Get detailed analytics for a specific group"""
    try:
        user_email = session.get('user_email')
        
        if not db:
            return jsonify({'success': False, 'message': 'Database not available'})
        
        # Get group
        group_ref = groups_collection.document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'success': False, 'message': 'Group not found'})
        
        group_data = group.to_dict()
        
        # Check if user is member
        if not any(m.get('email') == user_email for m in group_data.get('members', [])):
            return jsonify({'success': False, 'message': 'Not a member of this group'})
        
        # Get all member emails
        member_emails = [m.get('email') for m in group_data.get('members', [])]
        
        # Get all transactions from all group members
        group_transactions = []
        
        for member_email in member_emails:
            # Get credit transactions for this member
            credits = credit_collection.where(filter=FieldFilter('submitted_by', '==', member_email)).get()
            for t in credits:
                t_data = t.to_dict()
                t_data['payment_type'] = 'credit'
                t_data['id'] = t.id
                # Convert datetime to string
                if 'date' in t_data and isinstance(t_data['date'], datetime):
                    t_data['date'] = t_data['date'].strftime('%Y-%m-%d')
                group_transactions.append(t_data)
            
            # Get debit transactions for this member
            debits = debit_collection.where(filter=FieldFilter('submitted_by', '==', member_email)).get()
            for t in debits:
                t_data = t.to_dict()
                t_data['payment_type'] = 'debit'
                t_data['id'] = t.id
                # Convert datetime to string
                if 'date' in t_data and isinstance(t_data['date'], datetime):
                    t_data['date'] = t_data['date'].strftime('%Y-%m-%d')
                group_transactions.append(t_data)
        
        # Calculate analytics
        total_spending = sum(float(t.get('amount', 0)) for t in group_transactions if t['payment_type'] == 'debit')
        total_income = sum(float(t.get('amount', 0)) for t in group_transactions if t['payment_type'] == 'credit')
        
        # Member spending
        member_spending = {}
        for t in group_transactions:
            submitted_by = t.get('submitted_by', 'Unknown')
            if submitted_by not in member_spending:
                member_spending[submitted_by] = {'debit': 0, 'credit': 0, 'count': 0}
            
            if t['payment_type'] == 'debit':
                member_spending[submitted_by]['debit'] += float(t.get('amount', 0))
            else:
                member_spending[submitted_by]['credit'] += float(t.get('amount', 0))
            member_spending[submitted_by]['count'] += 1
        
        # Category breakdown
        category_spending = {}
        for t in group_transactions:
            if t['payment_type'] == 'debit':
                category = t.get('payee_type', 'Other')
                category_spending[category] = category_spending.get(category, 0) + float(t.get('amount', 0))
        
        # Monthly trends
        monthly_spending = {}
        for t in group_transactions:
            if t['payment_type'] == 'debit':
                date_str = t.get('date', '')
                if date_str:
                    try:
                        if isinstance(date_str, str):
                            month_key = date_str[:7]  # YYYY-MM
                        else:
                            month_key = date_str.strftime('%Y-%m')
                        monthly_spending[month_key] = monthly_spending.get(month_key, 0) + float(t.get('amount', 0))
                    except:
                        pass
        
        # Top spenders
        top_spenders = sorted(
            [{'email': k, 'amount': v['debit'], 'count': v['count']} for k, v in member_spending.items()],
            key=lambda x: x['amount'],
            reverse=True
        )[:5]
        
        # Most expensive categories
        top_categories = sorted(
            [{'category': k, 'amount': v} for k, v in category_spending.items()],
            key=lambda x: x['amount'],
            reverse=True
        )[:5]
        
        return jsonify({
            'success': True,
            'group': {
                'id': group_id,
                'name': group_data.get('name'),
                'type': group_data.get('type'),
                'member_count': len(group_data.get('members', []))
            },
            'analytics': {
                'total_spending': total_spending,
                'total_income': total_income,
                'net_balance': total_income - total_spending,
                'transaction_count': len(group_transactions),
                'member_spending': member_spending,
                'category_spending': category_spending,
                'monthly_spending': monthly_spending,
                'top_spenders': top_spenders,
                'top_categories': top_categories
            },
            'transactions': group_transactions
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)