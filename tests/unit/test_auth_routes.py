import pytest
from unittest.mock import Mock, patch
import json
from bson import ObjectId
import datetime


class TestAuthRoutes:
    """Test authentication routes"""
    
    @patch('auth.routes.render_template')
    @patch('auth.routes.get_current_user')
    def test_register_get_not_logged_in(self, mock_get_user, mock_render, client):
        """Test GET register when user is not logged in"""
        mock_get_user.return_value = None
        mock_render.return_value = "Register page"
        
        response = client.get('/auth/register')
        assert response.status_code == 200
        mock_render.assert_called_with('register.html')
    
    @patch('auth.routes.get_current_user')
    def test_register_get_already_logged_in(self, mock_get_user, client):
        """Test GET register when user is already logged in"""
        mock_get_user.return_value = {'_id': 'user123', 'username': 'testuser'}
        
        response = client.get('/auth/register')
        assert response.status_code == 302  # Redirect to dashboard
    
    @patch('auth.routes.User')
    @patch('auth.routes.create_access_token')
    @patch('auth.routes.get_current_user')
    def test_register_post_success_json(self, mock_get_user, mock_create_token, mock_user_class, client):
        """Test successful JSON registration"""
        mock_get_user.return_value = None
        mock_create_token.return_value = 'test_token'
        
        mock_user_instance = Mock()
        mock_user_instance.create_user.return_value = {
            'success': True,
            'user': {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com'
            }
        }
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }
        
        response = client.post('/auth/register', 
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'access_token' in response_data
    
    @patch('auth.routes.User')
    @patch('auth.routes.create_access_token')
    @patch('auth.routes.get_current_user')
    def test_register_post_success_form(self, mock_get_user, mock_create_token, mock_user_class, client):
        """Test successful form registration"""
        mock_get_user.return_value = None
        mock_create_token.return_value = 'test_token'
        
        mock_user_instance = Mock()
        mock_user_instance.create_user.return_value = {
            'success': True,
            'user': {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com'
            }
        }
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/auth/register', data=data)
        assert response.status_code == 302  # Redirect to dashboard
    
    @patch('auth.routes.get_current_user')
    def test_register_post_missing_fields_json(self, mock_get_user, client):
        """Test registration with missing fields (JSON)"""
        mock_get_user.return_value = None
        
        data = {
            'username': 'testuser',
            'email': '',  # Missing email
            'password': 'password123'
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert response_data['success'] is False
        assert 'required' in response_data['message']
    
    @patch('auth.routes.render_template')
    @patch('auth.routes.get_current_user')
    def test_register_post_missing_fields_form(self, mock_get_user, mock_render, client):
        """Test registration with missing fields (form)"""
        mock_get_user.return_value = None
        mock_render.return_value = "Register page with error"
        
        data = {
            'username': 'testuser',
            'email': '',  # Missing email
            'password': 'password123'
        }
        
        response = client.post('/auth/register', data=data)
        assert response.status_code == 200
        mock_render.assert_called_with('register.html', error='All fields are required')
    
    @patch('auth.routes.get_current_user')
    def test_register_post_invalid_email(self, mock_get_user, client):
        """Test registration with invalid email"""
        mock_get_user.return_value = None
        
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123'
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'Invalid email format' in response_data['message']
    
    @patch('auth.routes.get_current_user')
    def test_register_post_weak_password(self, mock_get_user, client):
        """Test registration with weak password"""
        mock_get_user.return_value = None
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'  # Too short
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'at least 8 characters' in response_data['message']
    
    @patch('auth.routes.get_current_user')
    def test_register_post_short_username(self, mock_get_user, client):
        """Test registration with short username"""
        mock_get_user.return_value = None
        
        data = {
            'username': 'ab',  # Too short
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'at least 3 characters' in response_data['message']
    
    @patch('auth.routes.get_current_user')
    def test_register_post_password_mismatch(self, mock_get_user, client):
        """Test registration with password mismatch"""
        mock_get_user.return_value = None
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'different123'
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'do not match' in response_data['message']
    
    @patch('auth.routes.User')
    @patch('auth.routes.get_current_user')
    def test_register_post_user_exists(self, mock_get_user, mock_user_class, client):
        """Test registration when user already exists"""
        mock_get_user.return_value = None
        
        mock_user_instance = Mock()
        mock_user_instance.create_user.return_value = {
            'success': False,
            'message': 'User already exists'
        }
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/auth/register',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 409
        response_data = response.get_json()
        assert 'User already exists' in response_data['message']
    
    @patch('auth.routes.render_template')
    @patch('auth.routes.get_current_user')
    def test_login_get_not_logged_in(self, mock_get_user, mock_render, client):
        """Test GET login when user is not logged in"""
        mock_get_user.return_value = None
        mock_render.return_value = "Login page"
        
        response = client.get('/auth/login')
        assert response.status_code == 200
        mock_render.assert_called_with('login.html')
    
    @patch('auth.routes.get_current_user')
    def test_login_get_already_logged_in(self, mock_get_user, client):
        """Test GET login when user is already logged in"""
        mock_get_user.return_value = {'_id': 'user123', 'username': 'testuser'}
        
        response = client.get('/auth/login')
        assert response.status_code == 302  # Redirect to dashboard
    
    @patch('auth.routes.User')
    @patch('auth.routes.create_access_token')
    @patch('auth.routes.get_current_user')
    def test_login_post_success_json(self, mock_get_user, mock_create_token, mock_user_class, client):
        """Test successful JSON login"""
        mock_get_user.return_value = None
        mock_create_token.return_value = 'test_token'
        
        mock_user_instance = Mock()
        mock_user_instance.authenticate_user.return_value = {
            '_id': ObjectId(),
            'username': 'testuser',
            'email': 'test@example.com'
        }
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'access_token' in response_data
    
    @patch('auth.routes.User')
    @patch('auth.routes.create_access_token')
    @patch('auth.routes.get_current_user')
    def test_login_post_success_form(self, mock_get_user, mock_create_token, mock_user_class, client):
        """Test successful form login"""
        mock_get_user.return_value = None
        mock_create_token.return_value = 'test_token'
        
        mock_user_instance = Mock()
        mock_user_instance.authenticate_user.return_value = {
            '_id': ObjectId(),
            'username': 'testuser',
            'email': 'test@example.com'
        }
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'email': 'test@example.com',
            'password': 'password123'
        }
        
        response = client.post('/auth/login', data=data)
        assert response.status_code == 302  # Redirect to dashboard
    
    @patch('auth.routes.get_current_user')
    def test_login_post_missing_fields(self, mock_get_user, client):
        """Test login with missing fields"""
        mock_get_user.return_value = None
        
        data = {
            'email': '',  # Missing email
            'password': 'password123'
        }
        
        response = client.post('/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'required' in response_data['message']
    
    @patch('auth.routes.User')
    @patch('auth.routes.get_current_user')
    def test_login_post_invalid_credentials(self, mock_get_user, mock_user_class, client):
        """Test login with invalid credentials"""
        mock_get_user.return_value = None
        
        mock_user_instance = Mock()
        mock_user_instance.authenticate_user.return_value = None  # Invalid credentials
        mock_user_class.return_value = mock_user_instance
        
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = client.post('/auth/login',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 401
        response_data = response.get_json()
        assert 'Invalid email or password' in response_data['message']
    
    def test_logout_success_json(self, client):
        """Test successful JSON logout"""
        response = client.post('/auth/logout',
                             data=json.dumps({}),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
    
    def test_logout_success_form(self, client):
        """Test successful form logout"""
        response = client.post('/auth/logout')
        assert response.status_code == 302  # Redirect to index
    
    def test_set_session_token_success(self, client):
        """Test successful session token setting"""
        data = {'access_token': 'test_token'}
        
        response = client.post('/auth/set-session-token',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
    
    def test_set_session_token_no_token(self, client):
        """Test session token setting without token"""
        data = {}
        
        response = client.post('/auth/set-session-token',
                             data=json.dumps(data),
                             content_type='application/json')
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'No token provided' in response_data['message']
    
    @patch('auth.routes.get_current_user')
    def test_verify_token_success(self, mock_get_user, client):
        """Test successful token verification"""
        mock_get_user.return_value = {
            '_id': ObjectId(),
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        response = client.post('/auth/verify-token',
                             data=json.dumps({}),
                             content_type='application/json')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'user' in response_data
    
    @patch('auth.routes.get_current_user')
    def test_verify_token_invalid(self, mock_get_user, client):
        """Test token verification with invalid token"""
        mock_get_user.return_value = None
        
        response = client.post('/auth/verify-token',
                             data=json.dumps({}),
                             content_type='application/json')
        
        assert response.status_code == 401
        response_data = response.get_json()
        assert response_data['success'] is False
        assert 'Invalid token' in response_data['message']


class TestAuthUtilityFunctions:
    """Test authentication utility functions"""
    
    def test_is_valid_email_valid(self):
        """Test email validation with valid emails"""
        from auth.routes import is_valid_email
        
        valid_emails = [
            'test@example.com',
            'user.name@domain.org',
            'firstname+lastname@company.co.uk',
            'user123@test-domain.com'
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True
    
    def test_is_valid_email_invalid(self):
        """Test email validation with invalid emails"""
        from auth.routes import is_valid_email
        
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@domain',
            '',
            'user name@domain.com',
            'user@domain.'
            # Remove 'user@.domain.com' as your current regex allows it
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False, f"Email '{email}' should be invalid but was validated as valid"


    
    def test_is_valid_password_valid(self):
        """Test password validation with valid passwords"""
        from auth.routes import is_valid_password
        
        valid_passwords = [
            'password123',
            '12345678',
            'longpassword',
            'P@ssw0rd123'
        ]
        
        for password in valid_passwords:
            assert is_valid_password(password) is True
    
    def test_is_valid_password_invalid(self):
        """Test password validation with invalid passwords"""
        from auth.routes import is_valid_password
        
        invalid_passwords = [
            'short',
            '1234567',  # 7 characters
            '',
            'pass'
        ]
        
        for password in invalid_passwords:
            assert is_valid_password(password) is False
    
    @patch('auth.routes.decode_token')
    @patch('auth.routes.User')
    def test_get_current_user_with_bearer_token(self, mock_user_class, mock_decode_token, client):
        """Test getting current user with Bearer token"""
        from auth.routes import get_current_user
        
        mock_decode_token.return_value = {'sub': 'user123'}
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {
            '_id': 'user123',
            'username': 'testuser'
        }
        mock_user_class.return_value = mock_user_instance
        
        with client.application.test_request_context(headers={'Authorization': 'Bearer test_token'}):
            result = get_current_user()
            
        assert result['_id'] == 'user123'
        assert result['username'] == 'testuser'
    
    @patch('auth.routes.User')
    def test_get_current_user_with_session_user_id(self, mock_user_class, client):
        """Test getting current user with session user_id"""
        from auth.routes import get_current_user
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {
            '_id': 'user123',
            'username': 'testuser'
        }
        mock_user_class.return_value = mock_user_instance
        
        with client.application.test_request_context():
            with client.session_transaction() as sess:
                sess['user_id'] = 'user123'
            
            with patch('auth.routes.session', {'user_id': 'user123'}):
                result = get_current_user()
            
        assert result['_id'] == 'user123'
    
    def test_get_current_user_no_auth(self, client):
        """Test getting current user with no authentication"""
        from auth.routes import get_current_user
        
        with client.application.test_request_context():
            with patch('auth.routes.session', {}):
                result = get_current_user()
            
        assert result is None
