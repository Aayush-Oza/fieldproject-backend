import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ================================
    # DATABASE (MySQL/RDS only)
    # ================================
    DB_USER     = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST     = os.getenv("DB_HOST")
    DB_PORT     = os.getenv("DB_PORT", "3306")
    DB_NAME     = os.getenv("DB_NAME")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ================================
    # FLASK
    # ================================
    SECRET_KEY  = os.getenv("SECRET_KEY", "fallback-secret-key")
    FLASK_ENV   = os.getenv("FLASK_ENV", "production")
    FLASK_DEBUG = False
    FLASK_PORT  = int(os.getenv("FLASK_PORT", 5000))

    # ================================
    # JWT
    # ================================
    JWT_SECRET_KEY   = os.getenv("JWT_SECRET_KEY", "fallback-jwt-key")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 24))

    # ================================
    # CORS
    # ================================
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

    # ================================
    # AI
    # ================================
    MODEL_PATH = os.getenv("MODEL_PATH", "ai/model_artifacts/forecast_model.pkl")