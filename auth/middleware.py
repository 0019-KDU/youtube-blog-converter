from functools import wraps
from flask import request, jsonify, redirect, url_for
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from .models import User

def token_required(f):
    """Decorator to require JWT token for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user_id = get_jwt_identity()
            
            if not current_user_id:
                return jsonify({
                    'success': False,
                    'message': 'Token is invalid'
                }), 401
            
            # Verify user exists
            user_model = User()
            current_user = user_model.get_user_by_id(current_user_id)
            
            if not current_user:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 404
            
            return f(current_user, *args, **kwargs)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Token is invalid or expired'
            }), 401
    
    return decorated_function

def web_auth_required(f):
    """Decorator for web routes that need authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except:
            return redirect(url_for('auth.login'))
    
    return decorated_function
