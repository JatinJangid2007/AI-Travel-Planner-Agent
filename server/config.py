import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 8080))
    
    # Firebase settings
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    FIREBASE_PRIVATE_KEY_ID = os.getenv('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.getenv('FIREBASE_CLIENT_ID')
    
    # API Keys
    AMADEUS_CLIENT_ID = os.getenv('AMADEUS_CLIENT_ID')
    AMADEUS_CLIENT_SECRET = os.getenv('AMADEUS_CLIENT_SECRET')
    
    # Rate limiting
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', 100))
    
    # Cache settings
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', 3600))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        # Check required Firebase settings
        if not cls.FIREBASE_PROJECT_ID:
            errors.append("FIREBASE_PROJECT_ID is required")
        if not cls.FIREBASE_CLIENT_EMAIL:
            errors.append("FIREBASE_CLIENT_EMAIL is required")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def get_firebase_config(cls):
        """Get Firebase configuration dictionary"""
        return {
            "type": "service_account",
            "project_id": cls.FIREBASE_PROJECT_ID,
            "private_key_id": cls.FIREBASE_PRIVATE_KEY_ID or "",
            "private_key": (cls.FIREBASE_PRIVATE_KEY or "").replace('\\n', '\n'),
            "client_email": cls.FIREBASE_CLIENT_EMAIL,
            "client_id": cls.FIREBASE_CLIENT_ID or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{cls.FIREBASE_CLIENT_EMAIL}"
        }
    
    @classmethod
    def is_production(cls):
        """Check if running in production"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    @classmethod
    def get_cors_origins(cls):
        """Get allowed CORS origins"""
        origins = os.getenv('CORS_ORIGINS', '*')
        if origins == '*':
            return origins
        return origins.split(',')


# Validate configuration on import
try:
    if os.getenv('SKIP_CONFIG_VALIDATION') != 'true':
        Config.validate()
except ValueError as e:
    print(f"Warning: {e}")
    print("Some features may not work properly without proper configuration.")