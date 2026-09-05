# backend/utils/response.py

from flask import jsonify

def success(message="Success", data=None, status=200):
    return jsonify({
        "success": True,
        "message": message,
        "data":    data
    }), status

def error(message="Something went wrong", status=400):
    return jsonify({
        "success": False,
        "message": message,
        "data":    None
    }), status