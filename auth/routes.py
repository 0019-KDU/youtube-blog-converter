from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_jwt_extended import create_access_token, decode_token
from .models import User, BlogPost
import re
import datetime
import sys
from pathlib import Path
import logging

# Import metrics from main app
from prometheus_client import Counter

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

# Metrics for authentication
user_registrations = Counter(
    'user_registrations_total',
    'Total user registrations',
    ['status']
)

user_logins = Counter(
    'user_logins_total',
    'Total user login attempts',
    ['status']
)

authentication_errors = Counter(
    'authentication_errors_total',
    'Total authentication errors',
    ['error_type']
)

# Helper function to get current user (local to auth module)
def get_current_user():
    """Get current user from various authentication sources"""
    try:
        token = None
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Check session
        if not token:
            token = session.get('access_token')
        
        # Check user_id directly in session as fallback
        if not token:
            user_id = session.get('user_id')
            if user_id:
                user_model = User()
                current_user = user_model.get_user_by_id(user_id)
                if current_user:
                    return current_user
        
        if token:
            try:
                decoded_token = decode_token(token)
                current_user_id = decoded_token.get('sub')
                
                if current_user_id:
                    user_model = User()
                    current_user = user_model.get_user_by_id(current_user_id)
                    return current_user
            except Exception:
                # Clear invalid token
                session.pop('access_token', None)
        
        return None
        
    except Exception as e:
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Error getting current user: {e}")
        return None

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    """Validate password strength"""
    return len(password) >= 8

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration with metrics tracking"""
    if request.method == 'GET':
        # Check if user is already logged in
        current_user = get_current_user()
        if current_user:
            return redirect(url_for('dashboard'))
        return render_template('register.html')
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
        
        # Clean and validate input
        username = username.strip() if username else ''
        email = email.strip().lower() if email else ''
        
        # Validation
        if not all([username, email, password]):
            error_msg = 'All fields are required'
            user_registrations.labels(status='failed_validation').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('register.html', error=error_msg)
        
        if not is_valid_email(email):
            error_msg = 'Invalid email format'
            user_registrations.labels(status='failed_validation').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('register.html', error=error_msg)
        
        if not is_valid_password(password):
            error_msg = 'Password must be at least 8 characters long'
            user_registrations.labels(status='failed_validation').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('register.html', error=error_msg)
        
        if len(username) < 3:
            error_msg = 'Username must be at least 3 characters long'
            user_registrations.labels(status='failed_validation').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('register.html', error=error_msg)
        
        # Password confirmation check (for JSON requests)
        if request.is_json and confirm_password and password != confirm_password:
            error_msg = 'Passwords do not match'
            user_registrations.labels(status='failed_validation').inc()
            return jsonify({'success': False, 'message': error_msg}), 400
        
        # Create user
        user_model = User()
        result = user_model.create_user(username, email, password)
        
        if not result.get('success'):
            error_msg = result.get('message', 'Registration failed')
            user_registrations.labels(status='failed_exists').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 409
            return render_template('register.html', error=error_msg)
        
        user = result['user']
        
        # Create JWT token
        access_token = create_access_token(
            identity=str(user['_id']),
            expires_delta=datetime.timedelta(days=1)
        )
        
        # Store in session
        session['access_token'] = access_token
        session['user_id'] = str(user['_id'])
        
        # Track successful registration
        user_registrations.labels(status='success').inc()
        logger.info(f"User registered successfully: {user['username']}")
        
        if request.is_json:
            return jsonify({
                'success': True,
                'access_token': access_token,
                'user': {
                    'id': str(user['_id']),
                    'username': user['username'],
                    'email': user['email']
                },
                'redirect_url': url_for('dashboard')
            })
        else:
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        user_registrations.labels(status='failed_error').inc()
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Registration error: {str(e)}")
        error_msg = 'Registration failed. Please try again.'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 500
        return render_template('register.html', error=error_msg)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with metrics tracking"""
    if request.method == 'GET':
        # Check if user is already logged in
        current_user = get_current_user()
        if current_user:
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        # Clean input
        email = email.strip().lower() if email else ''
        
        if not email or not password:
            error_msg = 'Email and password are required'
            user_logins.labels(status='failed_validation').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 400
            return render_template('login.html', error=error_msg)
        
        # Authenticate user
        user_model = User()
        user = user_model.authenticate_user(email, password)
        
        if user:
            # Create JWT token
            access_token = create_access_token(
                identity=str(user['_id']),
                expires_delta=datetime.timedelta(days=1)
            )
            
            # Store in session
            session['access_token'] = access_token
            session['user_id'] = str(user['_id'])
            
            # Track successful login
            user_logins.labels(status='success').inc()
            logger.info(f"User logged in successfully: {user['username']}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'access_token': access_token,
                    'user': {
                        'id': str(user['_id']),
                        'username': user['username'],
                        'email': user['email']
                    },
                    'redirect_url': url_for('dashboard')
                })
            else:
                return redirect(url_for('dashboard'))
        else:
            error_msg = 'Invalid email or password'
            user_logins.labels(status='failed_credentials').inc()
            if request.is_json:
                return jsonify({'success': False, 'message': error_msg}), 401
            return render_template('login.html', error=error_msg)
            
    except Exception as e:
        user_logins.labels(status='failed_error').inc()
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Login error: {str(e)}")
        error_msg = 'Login failed. Please try again.'
        if request.is_json:
            return jsonify({'success': False, 'message': error_msg}), 500
        return render_template('login.html', error=error_msg)

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    try:
        user_id = session.get('user_id')
        if user_id:
            logger.info(f"User logged out: {user_id}")
        
        # Clear session
        session.clear()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Logged out successfully'})
        else:
            return redirect(url_for('index'))
            
    except Exception as e:
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Logout error: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'message': 'Logout failed'}), 500
        else:
            return redirect(url_for('index'))

@auth_bp.route('/set-session-token', methods=['POST'])
def set_session_token():
    """Set JWT token in server session"""
    try:
        data = request.get_json()
        token = data.get('access_token')
        
        if token:
            # Store token in server session
            session['access_token'] = token
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'No token provided'}), 400
            
    except Exception as e:
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Set session token error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify if current token is valid"""
    try:
        current_user = get_current_user()
        if current_user:
            return jsonify({
                'success': True,
                'user': {
                    'id': str(current_user['_id']),
                    'username': current_user['username'],
                    'email': current_user['email']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid token'}), 401
            
    except Exception as e:
        authentication_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Token verification error: {str(e)}")
        return jsonify({'success': False, 'message': 'Token verification failed'}), 500
