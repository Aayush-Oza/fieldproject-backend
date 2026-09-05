# backend/services/auth_service.py

from models.user import User
from extensions import db, bcrypt
from flask_jwt_extended import create_access_token
from datetime import timedelta
from config import Config

class AuthService:

    @staticmethod
    def register(data):
        # Check if email already exists
        existing = User.query.filter_by(email=data["email"]).first()
        if existing:
            return None, "Email already registered"

        # Hash password
        hashed = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

        # Create user
        user = User(
            name     = data["name"],
            email    = data["email"],
            phone    = data.get("phone", None),
            password = hashed,
            role     = "participant"
        )

        db.session.add(user)
        db.session.commit()

        return user, None

    @staticmethod
    def login(data):
        # Find user by email
        user = User.query.filter_by(email=data["email"]).first()

        if not user:
            return None, None, "Email not found"

        if not user.is_active:
            return None, None, "Account is disabled"

        # Check password
        if not bcrypt.check_password_hash(user.password, data["password"]):
            return None, None, "Incorrect password"

        # Generate JWT token
        token = create_access_token(
            identity  = str(user.id),
            additional_claims = {"role": user.role},
            expires_delta = timedelta(hours=Config.JWT_EXPIRY_HOURS)
        )

        return user, token, None

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)