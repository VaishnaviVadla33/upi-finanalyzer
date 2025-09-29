from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from PIL import Image
import pytesseract
import re
import random
import string
from datetime import datetime
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
from functools import wraps
import pandas as pd
import smtplib
from email.mime.text import MIMEText

from dashboard_helpers import (
    get_savings_suggestions,
    compare_spending,
    cash_flow_analysis,
    spending_alerts,
    get_top_time_intervals
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'my_sowmya_2106'

# Initialize Firebase
load_dotenv()

# Check if Firebase credentials are in environment variable (for deployment)
firebase_credentials_env = os.getenv('FIREBASE_CREDENTIALS')
if firebase_credentials_env:
    # Production: credentials from environment variable
    import json
    import tempfile
    
    # Create temporary file with credentials
    creds_dict = json.loads(firebase_credentials_env)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(creds_dict, f)
        firebase_key_path = f.name
else:
    # Development: credentials from file
    firebase_key_path = os.getenv('FIREBASE_KEY_PATH')
    if not firebase_key_path or not os.path.exists(firebase_key_path):
        raise ValueError("Firebase credentials not found. Set FIREBASE_CREDENTIALS environment variable or check FIREBASE_KEY_PATH.")

cred = credentials.Certificate(firebase_key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

# No more global collections - we'll use user-specific subcollections
family_collection = db.collection('families')
user_collection = db.collection('users')

# Helper function to get user-specific collections
def get_user_collections(user_id):
    """Get user-specific credit and debit collections"""
    user_doc = db.collection('users').document(user_id)
    credit_collection = user_doc.collection('credit_transactions')
    debit_collection = user_doc.collection('debit_transactions')
    return credit_collection, debit_collection

# Middleware to protect routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Session login with Firebase ID token
@app.route('/sessionLogin', methods=['POST'])
def session_login():
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        user_data = data.get('userData', {})
        
        if not id_token:
            return jsonify({'error': 'Missing ID token'}), 400

        decoded_token = auth.verify_id_token(id_token)
        user_email = decoded_token.get('email')
        user_name = decoded_token.get('name', '') or user_data.get('name', '')
        user_id = decoded_token.get('uid')
        photo_url = user_data.get('photoURL', '')

        session['user_email'] = user_email
        session['user_id'] = user_id
        session['user_name'] = user_name

        # Store/update user information in Firestore
        user_doc_data = {
            "email": user_email,
            "name": user_name,
            "photoURL": photo_url,
            "created_at": firestore.SERVER_TIMESTAMP,
            "last_login": firestore.SERVER_TIMESTAMP
        }
        
        db.collection("users").document(user_id).set(user_doc_data, merge=True)

        return jsonify({'message': 'Session set', 'user_name': user_name}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/tpg')
@login_required
def home():
    return render_template('tpg.html')

@app.route('/generate_invite', methods=['POST'])
@login_required
def generate_invite():
    user_id = session.get('user_id')
    user_email = session.get('user_email')

    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    db.collection('family_invites').document(user_id).set({'invite_code': invite_code})
     # ✅ Store invite code in user profile
    db.collection('users').document(user_id).update({'family_code': invite_code})
    send_email(user_email, invite_code)
    return render_template('tpg.html', show_modal=True)

@app.route('/verify_invite', methods=['POST'])
@login_required
def verify_invite():
    user_email = session.get('user_email')
    user_id = session.get('user_id')
    entered_code = request.form.get('invite_code', '').strip().upper()

    family_ref = db.collection('families').document(entered_code)
    family_doc = family_ref.get()

    if family_doc.exists:
        # ✅ Update family members and user profile
        family_ref.update({'members': firestore.ArrayUnion([user_email])})
        db.collection('users').document(user_id).update({'family_code': entered_code})
        return redirect('/family_dashboard')
    else:
        return "Invalid Invite Code. Please try again."


@app.route('/family_dashboard')
@login_required
def family_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user_doc = db.collection('users').document(user_id).get()
    user_data = user_doc.to_dict()
    family_code = user_data.get('family_code', '')

    members = []
    if family_code:
        family_doc = db.collection('families').document(family_code).get()
        if family_doc.exists:
            family_data = family_doc.to_dict()
            members = family_data['members'] if family_data and 'members' in family_data else []

    return render_template('family_dashboard.html', family_code=family_code, members=members)

@app.route('/family', methods=['GET', 'POST'])
def family_page():
    if request.method == 'POST':
        # Handle form submission (optional)
        pass
    return render_template('family.html')
@app.route('/check-family-status')
@login_required
def check_family_status():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'joined': False})

    user_doc = db.collection('users').document(user_id).get()
    user_data = user_doc.to_dict()

    joined = user_data and 'family_code' in user_data
    return jsonify({'joined': joined})




@app.route('/create-family', methods=['POST'])
@login_required
def create_family():
    user_email = session.get('user_email')
    user_id = session.get('user_id')

    # Generate invite code
    family_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Create family in Firestore
    db.collection('families').document(family_code).set({
        'created_by': user_email,
        'members': [user_email],
        'created_at': datetime.utcnow()
    })

    # Update user document
    db.collection('users').document(user_id).update({
        'family_code': family_code
    })

    # Send invite code to user's email
    send_email(user_email, family_code)

    return jsonify({'family_code': family_code}), 200



@app.route('/join-family', methods=['POST'])
@login_required
def join_family():
    user_email = session.get('user_email')
    user_id = session.get('user_id')
    family_code = request.form.get('family_code').strip().upper()

    family_ref = db.collection('families').document(family_code)
    family_doc = family_ref.get()

    if not family_doc.exists:
        return "Invalid Family Code. Please try again.", 400

    # Update the family's member list
    family_ref.update({
        'members': firestore.ArrayUnion([user_email])
    })

    # Update user document with this family code
    db.collection('users').document(user_id).update({
        'family_code': family_code
    })

    return redirect('/family_dashboard')

def send_email(to_email, invite_code):
    msg = MIMEText(f"Your Family Invite Code: {invite_code}")
    msg['Subject'] = 'Family Invite Code'
    msg['From'] = 'sowmyamakam2@gmail.com'
    msg['To'] = to_email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('sowmyamakam2@gmail.com', 'hwkl xdrd doow thaj')
        server.send_message(msg)



#####################################
# === OCR + Dashboard Integration ===
#####################################

# Configure Tesseract path for different environments
def configure_tesseract():
    """Configure Tesseract OCR path based on environment"""
    import platform
    
    if platform.system() == "Windows":
        # Windows local development
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Users\*\AppData\Local\Tesseract-OCR\tesseract.exe",
            "tesseract"  # If in PATH
        ]
        
        for path in tesseract_paths:
            if os.path.exists(path.replace('*', os.environ.get('USERNAME', ''))):
                pytesseract.pytesseract.tesseract_cmd = path.replace('*', os.environ.get('USERNAME', ''))
                break
            elif path == "tesseract":
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
                except:
                    continue
    else:
        # Linux/Unix (production deployment)
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Configure OCR on app startup
configure_tesseract()

# OCR: Image Preprocessing
def preprocess_image(image_path):
    image = Image.open(image_path)
    image = image.convert('L')
    image = image.point(lambda x: 0 if x < 150 else 255)
    return image

# Time Format Conversion Helper
def convert_to_12_hour_format(time_str):
    try:
        if ':' in time_str and len(time_str.split(':')[0]) == 2:
            time_obj = datetime.strptime(time_str, '%H:%M')
            return time_obj.strftime('%I:%M %p')
    except ValueError:
        return time_str

# OCR: Extract Transaction Details
def extract_transaction_details(image_path):
    try:
        image = preprocess_image(image_path)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)

        corrected_text = re.sub(r'[^\w\s₹.,:am|pm]', '', text)
        corrected_text = re.sub(r'(?<=\d)3(?=\d)', '₹', corrected_text)
        corrected_text = re.sub(r'%', '₹', corrected_text)

        transaction_status = "Unknown"
        if "credited" in corrected_text.lower():
            transaction_status = "Credited"
        elif "debited" in corrected_text.lower():
            transaction_status = "Debited"

        details = {'Status': transaction_status}

        date_time = re.search(r'(\d{1,2}:\d{2}\s*[APap][Mm])\s*on\s*(\d{1,2}\s\w+\s\d{4})', corrected_text)
        if date_time:
            time_str = date_time.group(1).strip()
            date_str = date_time.group(2).strip()
            try:
                datetime_obj = datetime.strptime(f"{date_str} {time_str}", '%d %b %Y %I:%M %p')
                details['date'] = datetime_obj
                details['Date'] = datetime_obj.strftime('%Y-%m-%d')
                details['Time'] = datetime_obj.strftime('%H:%M')
            except ValueError:
                pass

        if transaction_status == "Credited":
            sender_match = re.search(r'Received from\s*\n*([^\d\n]+)', corrected_text)
            if sender_match:
                details['Sender'] = sender_match.group(1).strip()
        elif transaction_status == "Debited":
            receiver_match = re.search(r'Paid to\s*\n*([^\d\n]+)', corrected_text)
            if receiver_match:
                details['Receiver'] = receiver_match.group(1).strip()

        amount_match = re.search(r'(?:₹|Rs\.?)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', corrected_text)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            details['Amount'] = float(amount_str)

        return details
    except Exception as e:
        return {'error': str(e)}

# === OCR Upload Route ===
@app.route('/upload', methods=['POST'])
@login_required
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        image_path = os.path.join('uploads', image_file.filename)
        image_file.save(image_path)

        details = extract_transaction_details(image_path)

        try:
            os.remove(image_path)
        except Exception as e:
            print(f"Error removing temporary file: {e}")

        return jsonify(details)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === Manual Transaction Submission Route ===
@app.route('/submit', methods=['POST'])
@login_required
def submit_transaction():
    try:
        user_id = session.get('user_id')
        user_email = session.get('user_email')
        
        # Get user-specific collections
        credit_collection, debit_collection = get_user_collections(user_id)

        # Get the family_code from the user document
        user_doc = db.collection('users').document(user_id).get()
        family_code = user_doc.to_dict().get('family_code', '') if user_doc.exists else ''

        data = {
            'name': request.form.get('name'),
            'transaction_id': request.form.get('transaction_id'),
            'amount': float(request.form.get('amount', 0)),
            'payee_type': request.form.get('payee_type'),
            'personal_reference': request.form.get('personal_reference'),
            'transaction_rating': request.form.get('transaction_rating'),
            'submitted_by': user_email,
            'user_id': user_id,  # Add user_id for easier querying
            'family_code': family_code,
            'created_at': firestore.SERVER_TIMESTAMP
        }

        date_str = request.form.get('date')
        time_str = request.form.get('time')
        if date_str and time_str:
            data['date'] = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')

        payment_type = request.form.get('payment_type')
        if payment_type == 'Credited':
            credit_collection.add(data)
        else:
            debit_collection.add(data)

        return jsonify({'message': 'Transaction data stored successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === Dashboard Rendering Route ===
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    
    # Get user-specific collections
    credit_collection, debit_collection = get_user_collections(user_id)
    
    # Fetch Credit Transactions
    credit_docs = credit_collection.stream()
    credit_data = [doc.to_dict() for doc in credit_docs]
    
    # Fetch Debit Transactions
    debit_docs = debit_collection.stream()
    debit_data = [doc.to_dict() for doc in debit_docs]

    return render_template('financial_dashboard.html',
                           credit_data=credit_data,
                           debit_data=debit_data)

# === Dashboard Data API ===
@app.route('/dashboard-data')
@login_required  # ✅ Ensure the user is logged in
def dashboard_data():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID not found in session'}), 401

        # Get user-specific collections
        credit_collection, debit_collection = get_user_collections(user_id)

        # Fetch all user transactions (no need for submitted_by filter since collections are user-specific)
        credit_docs = credit_collection.stream()
        credit_transactions = [doc.to_dict() for doc in credit_docs]

        debit_docs = debit_collection.stream()
        debit_transactions = [doc.to_dict() for doc in debit_docs]

        credit_df = pd.DataFrame(credit_transactions)
        debit_df = pd.DataFrame(debit_transactions)

        if 'date' in credit_df.columns:
            credit_df['date'] = pd.to_datetime(credit_df['date'], errors='coerce')
        if 'date' in debit_df.columns:
            debit_df['date'] = pd.to_datetime(debit_df['date'], errors='coerce')

        all_transactions = pd.concat([credit_df, debit_df], ignore_index=True)
        if 'date' in all_transactions.columns:
            all_transactions['date'] = pd.to_datetime(all_transactions['date'], errors='coerce')

        savings_suggestions = get_savings_suggestions(all_transactions)
        monthly_comparison = compare_spending(all_transactions)
        alerts = spending_alerts(all_transactions)
        inflows, outflows = cash_flow_analysis(credit_df, debit_df)
        top_time_intervals = get_top_time_intervals(credit_df, debit_df)

        credit_chart_data = {
            'dates': credit_df['date'].dt.strftime('%Y-%m-%d').tolist() if 'date' in credit_df.columns and not credit_df.empty else [],
            'amounts': credit_df['amount'].tolist() if 'amount' in credit_df.columns and not credit_df.empty else []
        }
        debit_chart_data = {
            'dates': debit_df['date'].dt.strftime('%Y-%m-%d').tolist() if 'date' in debit_df.columns and not debit_df.empty else [],
            'amounts': debit_df['amount'].tolist() if 'amount' in debit_df.columns and not debit_df.empty else []
        }

        dashboard_data = {
            'monthly_comparison': monthly_comparison,
            'savings_suggestions': savings_suggestions,
            'inflows': inflows,
            'outflows': outflows,
            'alerts': alerts,
            'credit_chart_data': credit_chart_data,
            'debit_chart_data': debit_chart_data,
            'top_time_intervals': top_time_intervals.to_dict(orient='records') if top_time_intervals is not None else []
        }

        return jsonify(dashboard_data)

    except Exception as e:
        import traceback
        print("Error in /dashboard-data:", traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# === Transaction History Page ===
@app.route('/history')
@login_required
def history():
    try:
        user_id = session.get('user_id')
        
        # Get user-specific collections
        credit_collection, debit_collection = get_user_collections(user_id)
        
        credit_docs = credit_collection.stream()
        debit_docs = debit_collection.stream()

        credit_transactions = [doc.to_dict() for doc in credit_docs]
        debit_transactions = [doc.to_dict() for doc in debit_docs]

        def parse_date_and_time(transactions):
            processed = []
            for txn in transactions:
                try:
                    if 'date' in txn:
                        if isinstance(txn['date'], datetime):
                            dt = txn['date']
                        elif isinstance(txn['date'], str):
                            dt = datetime.strptime(txn['date'], '%Y-%m-%d %H:%M:%S')
                        else:
                            dt = txn['date'].to_pydatetime()
                        txn['date'] = dt.strftime('%Y-%m-%d')
                        txn['time'] = dt.strftime('%H:%M:%S')
                    processed.append(txn)
                except Exception as e:
                    print("Date Parse Error:", e)
            return processed

        credit_transactions = parse_date_and_time(credit_transactions)
        debit_transactions = parse_date_and_time(debit_transactions)

        return render_template('financial_history.html',
                               credit_transactions=credit_transactions,
                               debit_transactions=debit_transactions)
    except Exception as e:
        return f"Error: {str(e)}", 500

# === Data Migration Route (for existing data) ===
@app.route('/migrate-data/<user_email>')
def migrate_user_data(user_email):
    """Migration utility to move old global collection data to user-specific collections"""
    try:
        # Find user by email
        users_query = db.collection('users').where('email', '==', user_email).limit(1).stream()
        user_doc = None
        for doc in users_query:
            user_doc = doc
            break
        
        if not user_doc:
            return jsonify({'error': 'User not found'}), 404
            
        user_id = user_doc.id
        
        # Get user-specific collections
        credit_collection, debit_collection = get_user_collections(user_id)
        
        # Get old global collections (if they still exist)
        old_credit_collection = db.collection('credit_transactions')
        old_debit_collection = db.collection('debit_transactions')
        
        migrated_credits = 0
        migrated_debits = 0
        
        # Migrate credit transactions
        old_credits = old_credit_collection.where('submitted_by', '==', user_email).stream()
        for doc in old_credits:
            data = doc.to_dict()
            data['migrated_from'] = doc.id  # Keep track of original ID
            credit_collection.add(data)
            migrated_credits += 1
            
        # Migrate debit transactions
        old_debits = old_debit_collection.where('submitted_by', '==', user_email).stream()
        for doc in old_debits:
            data = doc.to_dict()
            data['migrated_from'] = doc.id  # Keep track of original ID
            debit_collection.add(data)
            migrated_debits += 1
            
        return jsonify({
            'success': True,
            'user_id': user_id,
            'migrated_credits': migrated_credits,
            'migrated_debits': migrated_debits,
            'message': f'Successfully migrated {migrated_credits + migrated_debits} transactions for {user_email}'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# === Start App (Final) ===
if __name__ == '__main__':
    print("Current working directory:", os.getcwd())
    
    # Get port from environment variable (for deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Check if running in production
    is_production = os.environ.get('FLASK_ENV') != 'development'
    
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    if is_production:
        # Production configuration
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development configuration  
        app.run(host='127.0.0.1', port=port, debug=True)
