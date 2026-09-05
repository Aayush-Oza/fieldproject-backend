# backend/utils/validators.py

import re

def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    return re.match(pattern, email) is not None

def validate_phone(phone):
    pattern = r"^\d{10}$"
    return re.match(pattern, phone) is not None

def validate_password(password):
    # Min 6 characters
    return len(password) >= 6

def validate_register(data):
    errors = []

    if not data.get("name") or len(data["name"].strip()) < 2:
        errors.append("Name must be at least 2 characters")

    if not data.get("email") or not validate_email(data["email"]):
        errors.append("Invalid email address")

    if not data.get("password") or not validate_password(data["password"]):
        errors.append("Password must be at least 6 characters")

    if data.get("phone") and not validate_phone(data["phone"]):
        errors.append("Phone must be 10 digits")

    return errors

def validate_login(data):
    errors = []

    if not data.get("email") or not validate_email(data["email"]):
        errors.append("Invalid email address")

    if not data.get("password"):
        errors.append("Password is required")

    return errors