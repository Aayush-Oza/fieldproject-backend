# backend/routes/auth.py

from flask import Blueprint, request
from services.auth_service import AuthService
from utils.response import success, error
from utils.validators import validate_register, validate_login

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data:
        return error("No data provided")

    # Validate
    errors = validate_register(data)
    if errors:
        return error(errors[0])

    # Register
    user, err = AuthService.register(data)
    if err:
        return error(err)

    return success(
        message = "Registration successful",
        data    = user.to_dict(),
        status  = 201
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data:
        return error("No data provided")

    # Validate
    errors = validate_login(data)
    if errors:
        return error(errors[0])

    # Login
    user, token, err = AuthService.login(data)
    if err:
        return error(err, 401)

    return success(
        message = "Login successful",
        data    = {
            "token": token,
            "user":  user.to_dict()
        }
    )


@auth_bp.route("/me", methods=["GET"])
def me():
    from middleware.auth_middleware import get_current_user
    from flask_jwt_extended import verify_jwt_in_request
    
    verify_jwt_in_request()
    user = get_current_user()
    
    if not user:
        return error("User not found", 404)

    return success(data=user.to_dict())
