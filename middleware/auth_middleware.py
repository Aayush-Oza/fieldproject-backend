# backend/middleware/auth_middleware.py

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from models.user import User

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

def volunteer_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        # Admin can access volunteer routes (e.g. for testing)
        if claims.get("role") not in ["volunteer", "admin"]:
            return jsonify({"success": False, "message": "Volunteer access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

def participant_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        # Admin can access participant routes (e.g. for testing/support)
        # Volunteers cannot - they have their own dashboard
        if claims.get("role") not in ["participant", "admin"]:
            return jsonify({"success": False, "message": "Participant access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.filter_by(id=int(user_id)).first()