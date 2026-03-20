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
from dotenv import load_dotenv
from functools import wraps
import pandas as pd
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

try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

from dashboard_helpers import (
    get_savings_suggestions,
    compare_spending,
    cash_flow_analysis,
    spending_alerts,
    get_top_time_intervals,
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'finanalyzer_secret_key_2024'

# ── Firebase ──────────────────────────────────────────────────────────────────
load_dotenv()
firebase_key_path = os.getenv('FIREBASE_KEY_PATH', 'FIREBASE_CREDENTIALS.json')

print("🔄 Initializing Firebase...")
try:
    if os.path.exists(firebase_key_path):
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase ready")
    else:
        print(f"❌ Credentials not found: {firebase_key_path}")
        db = None
except Exception as e:
    print(f"❌ Firebase init failed: {e}")
    db = None

if db:
    credit_collection = db.collection('credit_transactions')
    debit_collection  = db.collection('debit_transactions')
    groups_collection = db.collection('groups')
    users_collection  = db.collection('users')
else:
    credit_collection = debit_collection = groups_collection = users_collection = None

# ── Firebase client config loader ─────────────────────────────────────────────
def load_firebase_config():
    """
    Load Firebase CLIENT config from environment variables.
    ALWAYS returns a dict (never None) so the API endpoint never errors.
    """
    try:
        print(f"🔄 Loading Firebase config from environment variables...")
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
            print(f"❌ Missing Firebase config fields: {missing_fields}")
            print("   Please configure these environment variables in your .env file")
            # Return empty config to prevent errors
            return {}
            
        print(f"✅ Firebase config loaded successfully. Project: {config.get('projectId')}")
        return config
    except Exception as e:
        print(f"❌ Error loading Firebase config: {e}")
        return {}

# Load once at startup so we can see any errors in the console immediately
FIREBASE_CLIENT_CONFIG = load_firebase_config()

# ── Tesseract ─────────────────────────────────────────────────────────────────
def configure_tesseract():
    paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
        'tesseract',
    ]
    for p in paths:
        if os.path.exists(p) or p == 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = p
            print(f"✓ Tesseract: {p}")
            return
    print("⚠ Tesseract not found")

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

# ── Auth decorator ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated

# ═════════════════════════════ PAGE ROUTES ════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth_page():
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    # Pass firebase_config so {{ firebase_config | tojson }} works in auth.html
    return render_template('auth.html')

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

@app.route('/upload')
@login_required
def upload_page():
    return render_template('upload.html',
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
            print(f"DB error (login): {e}")
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
        print(f"Login error: {e}")
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
            print(f"DB error (register check): {e}")
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
            print(f"DB error (register create): {e}")
            return jsonify({'success': False, 'message': 'Registration failed. Please try again.'})

        session['user_email'] = email
        session['user_name']  = name

        return jsonify({
            'success': True,
            'message': f'Welcome to FinAnalyzer, {name}! Account created.',
            'user'   : {'email': email, 'name': name}
        })

    except Exception as e:
        print(f"Register error: {e}")
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
            print(f"DB error (forgot-password): {e}")
            return jsonify({'success': False, 'message': 'Something went wrong. Please try again.'})

        if not doc.exists:
            # Always return success to avoid email enumeration
            return jsonify({'success': True, 'message': 'ok'})

        user_data = doc.to_dict()

        # Ensure user exists in Firebase Auth so reset email can be sent
        try:
            auth.get_user_by_email(email)
            print(f"✅ Firebase Auth user exists: {email}")
        except auth.UserNotFoundError:
            print(f"⚙ Creating Firebase Auth user: {email}")
            auth.create_user(
                email=email,
                display_name=user_data.get('name', ''),
                email_verified=False
            )
            print(f"✅ Firebase Auth user created: {email}")
        except Exception as e:
            print(f"⚠ Firebase Auth check failed (non-fatal): {e}")

        return jsonify({'success': True, 'message': 'ok'})

    except Exception as e:
        print(f"Forgot-password error: {e}")
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
        print(f"Reset-password POST error: {e}")
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
        print(f"Upload error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/save-transaction', methods=['POST'])
@login_required
def save_transaction():
    try:
        data       = request.get_json(silent=True) or {}
        user_email = session.get('user_email')
        tx = {
            'submitted_by': user_email,
            'name'        : data.get('name', ''),
            'amount'      : float(data.get('amount', 0)),
            'payment_type': data.get('payment_type', 'debit'),
            'payee_type'  : data.get('payee_type', 'Other'),
            'date'        : data.get('date', datetime.now().strftime('%Y-%m-%d')),
            'time'        : data.get('time', datetime.now().strftime('%H:%M')),
            'created_at'  : datetime.now(),
        }
        if db:
            (credit_collection if tx['payment_type'] == 'credit' else debit_collection).add(tx)
        return jsonify({'success': True, 'message': 'Transaction saved.'})
    except Exception as e:
        print(f"Save tx error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/dashboard-data')
@login_required
def dashboard_data():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})

        credit_docs = credit_collection.where('submitted_by', '==', user_email).get()
        debit_docs  = debit_collection.where('submitted_by', '==', user_email).get()

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
                    t.setdefault('name', 'Unknown')
                    t.setdefault('amount', 0)
                    t.setdefault('payment_type', 'debit')
                    t.setdefault('payee_type', 'Other')
                    t.setdefault('date', datetime.now().strftime('%Y-%m-%d'))
                    recent.append(t)
            except Exception as err:
                print(f"Recent tx error: {err}")

        return jsonify({'success': True, 'data': {
            'total_income'       : total_income,
            'total_expenses'     : total_expenses,
            'balance'            : balance,
            'recent_transactions': recent,
        }})
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/spending-categories')
@login_required
def spending_categories():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        debit_docs = debit_collection.where('submitted_by', '==', user_email).get()
        debit_df   = pd.DataFrame([d.to_dict() for d in debit_docs])
        categories = {}
        if not debit_df.empty:
            cats = debit_df.groupby('payee_type')['amount'].sum()
            categories = {str(k): float(v) for k, v in cats.items()}
        return jsonify({'success': True, 'data': categories})
    except Exception as e:
        print(f"Spending categories error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/analytics-data')
@login_required
def analytics_data():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})

        credit_docs = credit_collection.where('submitted_by', '==', user_email).get()
        debit_docs  = debit_collection.where('submitted_by', '==', user_email).get()

        credit_df = pd.DataFrame([d.to_dict() for d in credit_docs])
        debit_df  = pd.DataFrame([d.to_dict() for d in debit_docs])
        all_tx    = pd.concat([credit_df, debit_df], ignore_index=True) \
            if not credit_df.empty or not debit_df.empty else pd.DataFrame()

        if all_tx.empty:
            return jsonify({'success': True, 'data': {
                'savings_suggestions': [], 'spending_comparison': {},
                'cash_flow': {'inflows': 0, 'outflows': 0},
                'alerts': [], 'peak_times': [],
            }, 'message': 'No transactions yet.'})

        inflows, outflows = cash_flow_analysis(credit_df, debit_df)
        return jsonify({'success': True, 'data': {
            'savings_suggestions': get_savings_suggestions(debit_df),
            'spending_comparison': compare_spending(all_tx),
            'cash_flow'          : {'inflows': inflows, 'outflows': outflows},
            'alerts'             : spending_alerts(all_tx),
            'peak_times'         : get_top_time_intervals(credit_df, debit_df),
        }})
    except Exception as e:
        print(f"Analytics error: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ═════════════════════════════ OCR HELPERS ════════════════════════════════════

def extract_transaction_details(file):
    try:
        image = Image.open(file.stream)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        image = image.convert('L').point(lambda x: 0 if x < 150 else 255)
        text  = pytesseract.image_to_string(image, config=r'--oem 3 --psm 6')
        text  = re.sub(r'[^\w\s₹.,:am|pm]', '', text)
        text  = re.sub(r'(?<=\d)3(?=\d)', '₹', text)
        text  = re.sub(r'%', '₹', text)
        return parse_transaction_text(text)
    except Exception as e:
        print(f"OCR error: {e}")
        return _empty_tx()


def parse_transaction_text(text):
    details = _empty_tx()
    tl = text.lower()

    if re.search(r'credited|received', tl):
        details['payment_type'] = 'credit'
    elif re.search(r'debited|paid', tl):
        details['payment_type'] = 'debit'

    for pat in [
        r'(?:₹|Rs\.?)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'Amount[:\s]*₹?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
    ]:
        m = re.search(pat, text, re.I)
        if m:
            try:
                amt = float(m.group(1).replace(',', ''))
                if 1 <= amt <= 1_000_000:
                    details['amount'] = str(amt)
                    break
            except ValueError:
                pass

    name_pats = (
        [r'Received from\s*\n*([^\d\n]+)', r'From\s+([A-Za-z\s]+)']
        if details['payment_type'] == 'credit'
        else [r'Paid to\s*\n*([^\d\n]+)', r'To\s+([A-Za-z\s]+)']
    )
    for pat in name_pats:
        m = re.search(pat, text, re.I)
        if m and len(m.group(1).strip()) > 2:
            details['name'] = m.group(1).strip()
            break

    categories = {
        'Food'         : ['restaurant','food','zomato','swiggy','cafe','hotel','dining'],
        'Transport'    : ['uber','ola','metro','bus','taxi','petrol','fuel'],
        'Entertainment': ['movie','cinema','netflix','spotify','game'],
        'Utilities'    : ['electricity','water','gas','internet','mobile','recharge','bill'],
        'Shopping'     : ['amazon','flipkart','mall','store','shop','purchase'],
    }
    for cat, kws in categories.items():
        if any(k in tl for k in kws):
            details['payee_type'] = cat
            break

    return details


def _empty_tx():
    return {
        'name': '', 'amount': '', 'payment_type': 'debit',
        'payee_type': 'Other',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
    }

# ═════════════════════════════ GROUP API ══════════════════════════════════════

@app.route('/api/create-group', methods=['POST'])
@login_required
def create_group():
    try:
        data        = request.get_json(silent=True) or {}
        user_email  = session.get('user_email')
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        group = {
            'name'              : data.get('name'),
            'description'       : data.get('description', ''),
            'type'              : data.get('type', 'other'),
            'invite_code'       : invite_code,
            'admin_email'       : user_email,
            'members'           : [{'email': user_email, 'name': session.get('user_name'),
                                    'is_admin': True, 'joined_at': datetime.now(),
                                    'total_spending': 0, 'transaction_count': 0}],
            'created_at'        : datetime.now(),
            'total_transactions': 0,
            'total_spending'    : 0,
        }
        if db:
            groups_collection.add(group)
        return jsonify({'success': True, 'group': group})
    except Exception as e:
        print(f"Create group error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/join-group', methods=['POST'])
@login_required
def join_group():
    try:
        data        = request.get_json(silent=True) or {}
        invite_code = data.get('invite_code')
        user_email  = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        groups = groups_collection.where('invite_code', '==', invite_code).get()
        if not groups:
            return jsonify({'success': False, 'message': 'Invalid invite code.'})
        group_doc  = groups[0]
        group_data = group_doc.to_dict()
        if any(m['email'] == user_email for m in group_data.get('members', [])):
            return jsonify({'success': False, 'message': 'You are already a member of this group.'})
        group_data['members'].append({'email': user_email, 'name': session.get('user_name'),
                                      'is_admin': False, 'joined_at': datetime.now(),
                                      'total_spending': 0, 'transaction_count': 0})
        group_doc.reference.update({'members': group_data['members']})
        return jsonify({'success': True, 'group': group_data})
    except Exception as e:
        print(f"Join group error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/leave-group', methods=['POST'])
@login_required
def leave_group():
    try:
        user_email = session.get('user_email')
        if not db:
            return jsonify({'success': False, 'message': 'Database not available.'})
        groups = groups_collection.where('members', 'array_contains', {'email': user_email}).get()
        if not groups:
            return jsonify({'success': False, 'message': 'You are not in any group.'})
        group_doc  = groups[0]
        group_data = group_doc.to_dict()
        group_data['members'] = [m for m in group_data['members'] if m['email'] != user_email]
        if not group_data['members']:
            group_doc.reference.delete()
        else:
            group_doc.reference.update({'members': group_data['members']})
        return jsonify({'success': True, 'message': 'Left group successfully.'})
    except Exception as e:
        print(f"Leave group error: {e}")
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)