import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ================================
    # DATABASE
    # ================================
    # Build database URL
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # Switch to PostgreSQL in production
    # Just set DATABASE_URL in .env and it overrides MySQL
    if os.getenv("DATABASE_URL"):
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================================
    # FLASK
    # ================================
    SECRET_KEY  = os.getenv("SECRET_KEY", "fallback-secret-key")
    FLASK_ENV   = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True") == "True"
    FLASK_PORT  = int(os.getenv("FLASK_PORT", 5000))

    # ================================
    # JWT
    # ================================
    JWT_SECRET_KEY    = os.getenv("JWT_SECRET_KEY", "fallback-jwt-key")
    JWT_EXPIRY_HOURS  = int(os.getenv("JWT_EXPIRY_HOURS", 24))

    # ================================
    # CORS
    # ================================
    #FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://eventops-fieldproject.netlify.app")

    # ================================
    # AI
    # ================================
    MODEL_PATH = os.getenv("MODEL_PATH", "ai/model.pkl")