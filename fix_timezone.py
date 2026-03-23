"""
Fix timezone for existing transactions - convert UTC to IST
"""
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'FIREBASE_CREDENTIALS.json')
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# IST timezone (UTC+5:30)
ist = timezone(timedelta(hours=5, minutes=30))

def fix_collection(collection_name):
    """Fix timezone for all documents in a collection"""
    collection = db.collection(collection_name)
    docs = collection.stream()
    
    count = 0
    for doc in docs:
        data = doc.to_dict()
        date_field = data.get('date')
        
        if date_field:
            # If it's already a datetime object
            if isinstance(date_field, datetime):
                # If it's naive (no timezone), assume it's IST
                if date_field.tzinfo is None:
                    new_date = date_field.replace(tzinfo=ist)
                    collection.document(doc.id).update({'date': new_date})
                    count += 1
                    print(f"Fixed {collection_name}/{doc.id}: {date_field} -> {new_date}")
    
    print(f"Fixed {count} documents in {collection_name}")
    return count

if __name__ == '__main__':
    print("Fixing timezone for existing transactions...")
    print("=" * 50)
    
    credit_count = fix_collection('credit_transactions')
    debit_count = fix_collection('debit_transactions')
    
    print("=" * 50)
    print(f"Total fixed: {credit_count + debit_count} transactions")
    print("Done!")
