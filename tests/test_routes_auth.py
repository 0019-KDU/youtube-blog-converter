import pytest
import json
from unittest.mock import patch, MagicMock

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