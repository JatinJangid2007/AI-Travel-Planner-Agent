import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime
import json

class FirebaseHelper:
    def __init__(self):
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            cred_dict = {
                "type": "service_account",
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL')}"
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
    
    def verify_token(self, id_token):
        """Verify Firebase ID token and return decoded token"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def get_or_create_user(self, uid, display_name=None):
        """Get or create user document"""
        user_ref = self.db.collection('users').document(uid)
        user = user_ref.get()
        
        if not user.exists:
            user_data = {
                'uid': uid,
                'displayName': display_name,
                'createdAt': datetime.utcnow(),
                'lastActiveAt': datetime.utcnow()
            }
            user_ref.set(user_data)
            return user_data
        else:
            # Update last active
            user_ref.update({'lastActiveAt': datetime.utcnow()})
            return user.to_dict()
    
    def save_plan(self, uid, query, plan, steps):
        """Save travel plan to Firestore"""
        try:
            plan_ref = self.db.collection('plans').document(uid).collection('queries').document()
            plan_data = {
                'query': query,
                'plan': plan,
                'steps': steps,
                'createdAt': datetime.utcnow()
            }
            plan_ref.set(plan_data)
            return plan_ref.id
        except Exception as e:
            print(f"Error saving plan: {e}")
            return None
    
    def get_user_history(self, uid, limit=10):
        """Get user's query history"""
        try:
            queries_ref = self.db.collection('plans').document(uid).collection('queries')
            queries = queries_ref.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            history = []
            for query in queries:
                data = query.to_dict()
                data['id'] = query.id
                # Convert datetime to string for JSON serialization
                if 'createdAt' in data:
                    data['createdAt'] = data['createdAt'].isoformat()
                history.append(data)
            
            return history
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []