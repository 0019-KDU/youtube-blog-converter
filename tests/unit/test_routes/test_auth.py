import json
from unittest.mock import Mock, patch

from bson import ObjectId


class TestAuthRoutes:
    """Test cases for authentication routes"""

    def test_register_get_request(self, client):
        """Test GET request to registration page"""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Sign Up' in response.data or b'Register' in response.data

    def test_register_get_request_authenticated_user_redirects(
            self, client, authenticated_user):
        """Test authenticated user is redirected from register page"""
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            response = client.get('/auth/register')
            assert response.status_code == 302  # Should now redirect

    def test_register_post_success(self, client):
        """Test successful user registration"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': str(ObjectId()),
                    'username': 'newuser',
                    'email': 'newuser@example.com'
                }
            }
            mock_user_class.return_value = mock_user

            response = client.post('/auth/register', data={
                'username': 'newuser',
                'email': 'newuser@example.com',
                'password': 'password123'
            })

            assert response.status_code == 302  # Redirect after success

    def test_register_post_json_success(self, client):
        """Test successful JSON registration"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': str(ObjectId()),
                    'username': 'newuser',
                    'email': 'newuser@example.com'
                }
            }
            mock_user_class.return_value = mock_user

            response = client.post('/auth/register',
                                   json={
                                       'username': 'newuser',
                                       'email': 'newuser@example.com',
                                       'password': 'password123',
                                       'confirm_password': 'password123'
                                   },
                                   content_type='application/json'
                                   )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'access_token' in data

    def test_register_post_validation_errors(self, client):
        """Test registration with validation errors"""
        # Test missing fields
        response = client.post('/auth/register', data={
            'username': '',
            'email': 'invalid-email',
            'password': 'short'
        })

        assert response.status_code == 200  # Stays on form
        # Check for error messages in response

    def test_register_post_duplicate_user(self, client):
        """Test registration with duplicate user"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.create_user.return_value = {
                'success': False,
                'message': 'User with this email already exists'
            }
            mock_user_class.return_value = mock_user

            response = client.post('/auth/register', data={
                'username': 'testuser',
                'email': 'existing@example.com',
                'password': 'password123'
            })

            assert response.status_code == 200

    def test_login_get_request(self, client):
        """Test GET request to login page"""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login.html' in response.data or b'Login' in response.data

    def test_login_post_success(self, client):
        """Test successful login"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.authenticate_user.return_value = {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user

            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            })

            assert response.status_code == 302  # Redirect after success

    def test_login_post_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.authenticate_user.return_value = None
            mock_user_class.return_value = mock_user

            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'wrongpassword'
            }, follow_redirects=False)

            assert response.status_code == 200
            # Check response data contains error message
            response_data = response.get_data(as_text=True)
            assert 'Invalid email or password' in response_data or 'error' in response_data.lower()

    def test_login_json_success(self, client):
        """Test successful JSON login"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.authenticate_user.return_value = {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user

            response = client.post('/auth/login',
                                   json={
                                       'email': 'test@example.com',
                                       'password': 'password123'
                                   },
                                   content_type='application/json'
                                   )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_logout(self, client, authenticated_user):
        """Test user logout"""
        response = client.post('/auth/logout')
        assert response.status_code == 302  # Redirect

        # Check session is cleared
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'access_token' not in sess

    def test_logout_json(self, client, authenticated_user):
        """Test JSON logout"""
        response = client.post('/auth/logout',
                               content_type='application/json',
                               data=json.dumps({})
                               )

        data = json.loads(response.data)
        assert data['success'] is True

    def test_set_session_token(self, client):
        """Test setting session token"""
        response = client.post('/auth/set-session-token',
                               json={'access_token': 'test-token'},
                               content_type='application/json'
                               )

        data = json.loads(response.data)
        assert data['success'] is True

        with client.session_transaction() as sess:
            assert sess['access_token'] == 'test-token'

    def test_verify_token_valid(self, client, authenticated_user):
        """Test token verification with valid token"""
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_get_user.return_value = authenticated_user

            response = client.post('/auth/verify-token')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_verify_token_invalid(self, client):
        """Test token verification with invalid token"""
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_get_user.return_value = None

            response = client.post('/auth/verify-token')

            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
