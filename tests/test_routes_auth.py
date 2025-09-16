import json
from unittest.mock import MagicMock, patch

import pytest


class TestAuthRoutes:
    
    def test_register_get(self, client):
        """Test GET request to register page"""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Sign Up' in response.data
    
    @patch('app.routes.auth.User')
    def test_register_post_success(self, mock_user_class, client):
        """Test successful user registration"""
        mock_user = mock_user_class.return_value
        mock_user.create_user.return_value = {
            'success': True,
            'user': {
                '_id': '507f1f77bcf86cd799439011',
                'username': 'testuser',
                'email': 'test@example.com'
            }
        }
        
        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data
    
    @patch('app.routes.auth.User')
    def test_register_invalid_email(self, mock_user_class, client):
        """Test registration with invalid email"""
        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid email' in data['message']
    
    @patch('app.routes.auth.User')
    def test_login_success(self, mock_user_class, client):
        """Test successful login"""
        mock_user = mock_user_class.return_value
        mock_user.authenticate_user.return_value = {
            '_id': '507f1f77bcf86cd799439011',
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        response = client.post('/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'access_token' in data
    
    @patch('app.routes.auth.User')
    def test_login_invalid_credentials(self, mock_user_class, client):
        """Test login with invalid credentials"""
        mock_user = mock_user_class.return_value
        mock_user.authenticate_user.return_value = None
        
        response = client.post('/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
    
    def test_logout(self, client):
        """Test logout"""
        # Set up session
        with client.session_transaction() as session:
            session['user_id'] = '507f1f77bcf86cd799439011'
            session['access_token'] = 'test-token'
        
        response = client.post('/auth/logout', json={})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify session is cleared
        with client.session_transaction() as session:
            assert 'user_id' not in session
            assert 'access_token' not in session

    # Additional comprehensive tests for better coverage

    def test_is_valid_email_function(self):
        """Test email validation function"""
        from app.routes.auth import is_valid_email

        # Valid emails
        assert is_valid_email('test@example.com') is True
        assert is_valid_email('user.name+tag@domain.co.uk') is True
        assert is_valid_email('test123@test-domain.com') is True

        # Invalid emails
        assert is_valid_email('invalid-email') is False
        assert is_valid_email('@domain.com') is False
        assert is_valid_email('test@') is False
        assert is_valid_email('test@@domain.com') is False
        assert is_valid_email('') is False

    def test_is_valid_password_function(self):
        """Test password validation function"""
        from app.routes.auth import is_valid_password

        # Valid passwords
        assert is_valid_password('password123') is True
        assert is_valid_password('12345678') is True
        assert is_valid_password('a' * 8) is True

        # Invalid passwords
        assert is_valid_password('short') is False
        assert is_valid_password('1234567') is False
        assert is_valid_password('') is False

    @patch('app.utils.security.get_current_user')
    def test_register_get_logged_in_user(self, mock_get_current_user, client):
        """Test GET request to register page when user is already logged in"""
        mock_get_current_user.return_value = {'_id': 'user123', 'username': 'testuser'}

        response = client.get('/auth/register')

        assert response.status_code == 302  # Redirect
        assert '/dashboard' in response.location

    def test_register_post_form_data(self, client):
        """Test registration with form data instead of JSON"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = mock_user_class.return_value
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': '507f1f77bcf86cd799439011',
                    'username': 'testuser',
                    'email': 'test@example.com'
                }
            }

            response = client.post('/auth/register', data={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'password123'
            })

            assert response.status_code == 302  # Redirect to dashboard

    def test_register_missing_fields_json(self, client):
        """Test registration with missing fields (JSON)"""
        response = client.post('/auth/register', json={
            'username': 'testuser',
            # Missing email and password
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'All fields are required' in data['message']

    def test_register_missing_fields_form(self, client):
        """Test registration with missing fields (form data)"""
        response = client.post('/auth/register', data={
            'username': 'testuser',
            # Missing email and password
        })

        assert response.status_code == 200  # Returns form with error
        # Check that response contains error message (may be in different format)
        assert b'All fields are required' in response.data or b'error' in response.data.lower()

    def test_register_short_password_json(self, client):
        """Test registration with short password (JSON)"""
        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'  # Too short
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'at least 8 characters' in data['message']

    def test_register_short_password_form(self, client):
        """Test registration with short password (form data)"""
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'  # Too short
        })

        assert response.status_code == 200
        # Just verify it's an error response by checking it's not a redirect
        assert not response.location

    def test_register_short_username_json(self, client):
        """Test registration with short username (JSON)"""
        response = client.post('/auth/register', json={
            'username': 'ab',  # Too short
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'at least 3 characters' in data['message']

    def test_register_short_username_form(self, client):
        """Test registration with short username (form data)"""
        response = client.post('/auth/register', data={
            'username': 'ab',  # Too short
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 200
        # Just verify it's an error response by checking it's not a redirect
        assert not response.location

    def test_register_password_mismatch_json(self, client):
        """Test registration with password mismatch (JSON)"""
        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'different'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Passwords do not match' in data['message']

    @patch('app.routes.auth.User')
    def test_register_user_creation_fails_json(self, mock_user_class, client):
        """Test registration when user creation fails (JSON)"""
        mock_user = mock_user_class.return_value
        mock_user.create_user.return_value = {
            'success': False,
            'message': 'Email already exists'
        }

        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Email already exists' in data['message']

    @patch('app.routes.auth.User')
    def test_register_user_creation_fails_form(self, mock_user_class, client):
        """Test registration when user creation fails (form data)"""
        mock_user = mock_user_class.return_value
        mock_user.create_user.return_value = {
            'success': False,
            'message': 'Email already exists'
        }

        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 200
        # Just verify it's an error response by checking it's not a redirect
        assert not response.location

    @patch('app.routes.auth.User')
    def test_register_exception_json(self, mock_user_class, client):
        """Test registration with exception (JSON)"""
        mock_user = mock_user_class.return_value
        mock_user.create_user.side_effect = Exception("Database error")

        response = client.post('/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Registration failed' in data['message']

    @patch('app.routes.auth.User')
    def test_register_exception_form(self, mock_user_class, client):
        """Test registration with exception (form data)"""
        mock_user = mock_user_class.return_value
        mock_user.create_user.side_effect = Exception("Database error")

        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 200
        assert b'Registration failed' in response.data

    def test_register_whitespace_handling(self, client):
        """Test registration handles whitespace in input"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = mock_user_class.return_value
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': '507f1f77bcf86cd799439011',
                    'username': 'testuser',
                    'email': 'test@example.com'
                }
            }

            response = client.post('/auth/register', json={
                'username': '  testuser  ',  # With whitespace
                'email': '  TEST@EXAMPLE.COM  ',  # With whitespace and caps
                'password': 'password123'
            })

            assert response.status_code == 200
            # Verify create_user was called with cleaned data
            mock_user.create_user.assert_called_with('testuser', 'test@example.com', 'password123')

    # LOGIN TESTS

    @patch('app.utils.security.get_current_user')
    def test_login_get_logged_in_user(self, mock_get_current_user, client):
        """Test GET request to login page when user is already logged in"""
        mock_get_current_user.return_value = {'_id': 'user123', 'username': 'testuser'}

        response = client.get('/auth/login')

        assert response.status_code == 302  # Redirect
        assert '/dashboard' in response.location

    def test_login_get_not_logged_in(self, client):
        """Test GET request to login page when not logged in"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data

    def test_login_form_data(self, client):
        """Test login with form data instead of JSON"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = mock_user_class.return_value
            mock_user.authenticate_user.return_value = {
                '_id': '507f1f77bcf86cd799439011',
                'username': 'testuser',
                'email': 'test@example.com'
            }

            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            })

            assert response.status_code == 302  # Redirect to dashboard

    def test_login_missing_fields_json(self, client):
        """Test login with missing fields (JSON)"""
        response = client.post('/auth/login', json={
            'email': 'test@example.com'
            # Missing password
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Email and password are required' in data['message']

    def test_login_missing_fields_form(self, client):
        """Test login with missing fields (form data)"""
        response = client.post('/auth/login', data={
            'email': 'test@example.com'
            # Missing password
        })

        assert response.status_code == 200
        # Just verify it's an error response by checking it's not a redirect
        assert not response.location

    @patch('app.routes.auth.User')
    def test_login_invalid_credentials_form(self, mock_user_class, client):
        """Test login with invalid credentials (form data)"""
        mock_user = mock_user_class.return_value
        mock_user.authenticate_user.return_value = None

        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 200
        # Just verify it's an error response by checking it's not a redirect
        assert not response.location

    @patch('app.routes.auth.User')
    def test_login_exception_json(self, mock_user_class, client):
        """Test login with exception (JSON)"""
        mock_user = mock_user_class.return_value
        mock_user.authenticate_user.side_effect = Exception("Database error")

        response = client.post('/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Login failed' in data['message']

    @patch('app.routes.auth.User')
    def test_login_exception_form(self, mock_user_class, client):
        """Test login with exception (form data)"""
        mock_user = mock_user_class.return_value
        mock_user.authenticate_user.side_effect = Exception("Database error")

        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        })

        assert response.status_code == 200
        assert b'Login failed' in response.data

    def test_login_email_cleaning(self, client):
        """Test login handles email cleaning"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = mock_user_class.return_value
            mock_user.authenticate_user.return_value = {
                '_id': '507f1f77bcf86cd799439011',
                'username': 'testuser',
                'email': 'test@example.com'
            }

            response = client.post('/auth/login', json={
                'email': '  TEST@EXAMPLE.COM  ',  # With whitespace and caps
                'password': 'password123'
            })

            assert response.status_code == 200
            # Verify authenticate_user was called with cleaned email
            mock_user.authenticate_user.assert_called_with('test@example.com', 'password123')

    # LOGOUT TESTS

    def test_logout_form_request(self, client):
        """Test logout with form request (non-JSON)"""
        with client.session_transaction() as session:
            session['user_id'] = '507f1f77bcf86cd799439011'
            session['access_token'] = 'test-token'

        response = client.post('/auth/logout')

        assert response.status_code == 302  # Redirect
        assert response.location.endswith('/')

    def test_logout_no_session(self, client):
        """Test logout when no session exists"""
        response = client.post('/auth/logout', json={})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    # SET SESSION TOKEN TESTS

    def test_set_session_token_success(self, client):
        """Test setting session token successfully"""
        response = client.post('/auth/set-session-token', json={
            'access_token': 'test-token-123'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify token is set in session
        with client.session_transaction() as session:
            assert session['access_token'] == 'test-token-123'

    def test_set_session_token_no_token(self, client):
        """Test setting session token without providing token"""
        response = client.post('/auth/set-session-token', json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No token provided' in data['message']

    # VERIFY TOKEN TESTS

    @patch('app.utils.security.get_current_user')
    def test_verify_token_valid(self, mock_get_current_user, client):
        """Test verifying a valid token"""
        mock_get_current_user.return_value = {
            '_id': '507f1f77bcf86cd799439011',
            'username': 'testuser',
            'email': 'test@example.com'
        }

        response = client.post('/auth/verify-token')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['user']['username'] == 'testuser'

    @patch('app.utils.security.get_current_user')
    def test_verify_token_invalid(self, mock_get_current_user, client):
        """Test verifying an invalid token"""
        mock_get_current_user.return_value = None

        response = client.post('/auth/verify-token')

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid token' in data['message']

    @patch('app.utils.security.get_current_user')
    def test_verify_token_exception(self, mock_get_current_user, client):
        """Test verifying token with exception"""
        mock_get_current_user.side_effect = Exception("Token verification error")

        response = client.post('/auth/verify-token')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Token verification failed' in data['message']