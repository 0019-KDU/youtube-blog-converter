import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, jsonify, request, url_for
from functools import wraps
import json

# Import the decorators from middleware.py
from auth.middleware import token_required, web_auth_required


class TestTokenRequired:
    """Test token_required decorator"""
    
    @pytest.fixture
    def test_app(self):
        """Create a test Flask app with decorated routes"""
        app = Flask(__name__)
        app.config['JWT_SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        
        # Create a route that uses the decorator
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify({'user_id': current_user['_id'], 'username': current_user['username']})
        
        @app.route('/protected-error')
        @token_required
        def protected_error_route(current_user):
            # Simulate an error in the decorated function
            raise Exception("Test error in decorated function")
        
        return app
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_success(self, mock_user_class, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required with valid token and existing user"""
        # Setup mocks
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {
            '_id': 'user123', 
            'username': 'testuser',
            'email': 'test@example.com'
        }
        mock_user_class.return_value = mock_user_instance
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['user_id'] == 'user123'
            assert data['username'] == 'testuser'
            
            # Verify mocks were called
            mock_verify_jwt.assert_called_once()
            mock_get_jwt.assert_called_once()
            mock_user_instance.get_user_by_id.assert_called_once_with('user123')
    
    @patch('auth.middleware.verify_jwt_in_request')
    def test_token_required_verify_jwt_exception(self, mock_verify_jwt, test_app):
        """Test token_required when verify_jwt_in_request raises exception"""
        mock_verify_jwt.side_effect = Exception("Invalid token")
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
            assert 'invalid or expired' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    def test_token_required_no_user_identity(self, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required when get_jwt_identity returns None"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = None
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
            assert 'invalid' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    def test_token_required_empty_user_identity(self, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required when get_jwt_identity returns empty string"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = ''
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
            assert 'invalid' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_user_not_found(self, mock_user_class, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required when user doesn't exist in database"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = None
        mock_user_class.return_value = mock_user_instance
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['success'] is False
            assert 'not found' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_user_model_exception(self, mock_user_class, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required when User model raises exception"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_class.side_effect = Exception("Database error")
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
            assert 'invalid or expired' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_get_user_by_id_exception(self, mock_user_class, mock_get_jwt, mock_verify_jwt, test_app):
        """Test token_required when get_user_by_id raises exception"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.side_effect = Exception("Database connection error")
        mock_user_class.return_value = mock_user_instance
        
        with test_app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['success'] is False
            assert 'invalid or expired' in data['message']
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_decorated_function_args_kwargs(self, mock_user_class, mock_get_jwt, mock_verify_jwt):
        """Test token_required passes args and kwargs correctly"""
        # Setup mocks
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {'_id': 'user123', 'username': 'testuser'}
        mock_user_class.return_value = mock_user_instance
        
        # Create a function with args and kwargs
        @token_required
        def test_function(current_user, arg1, arg2, kwarg1=None, kwarg2=None):
            return {
                'user': current_user,
                'arg1': arg1,
                'arg2': arg2,
                'kwarg1': kwarg1,
                'kwarg2': kwarg2
            }
        
        # Call the decorated function
        result = test_function('test_arg1', 'test_arg2', kwarg1='test_kwarg1', kwarg2='test_kwarg2')
        
        # Verify the function received correct parameters
        assert result['user']['_id'] == 'user123'
        assert result['arg1'] == 'test_arg1'
        assert result['arg2'] == 'test_arg2'
        assert result['kwarg1'] == 'test_kwarg1'
        assert result['kwarg2'] == 'test_kwarg2'
    
    def test_token_required_preserves_function_metadata(self):
        """Test that token_required preserves original function metadata"""
        @token_required
        def test_function(current_user):
            """Test function docstring"""
            return "test"
        
        # Check that @wraps preserved the function name and docstring
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == "Test function docstring"


class TestWebAuthRequired:
    """Test web_auth_required decorator"""
    
    @pytest.fixture
    def test_app(self):
        """Create a test Flask app with web auth decorated routes"""
        app = Flask(__name__)
        app.config['JWT_SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        
        # Create routes that use the decorator
        @app.route('/web-protected')
        @web_auth_required
        def web_protected_route():
            return jsonify({'message': 'success', 'protected': True})
        
        @app.route('/web-protected-with-args/<item_id>')
        @web_auth_required
        def web_protected_with_args(item_id):
            return jsonify({'item_id': item_id, 'message': 'success'})
        
        # Mock auth.login route for redirects
        @app.route('/auth/login')
        def login():
            return jsonify({'message': 'login page'})
        
        return app
    
    @patch('auth.middleware.verify_jwt_in_request')
    def test_web_auth_required_success(self, mock_verify_jwt, test_app):
        """Test web_auth_required with valid JWT"""
        mock_verify_jwt.return_value = None
        
        with test_app.test_client() as client:
            response = client.get('/web-protected')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == 'success'
            assert data['protected'] is True
            
            mock_verify_jwt.assert_called_once()
    
    def test_web_auth_required_invalid_jwt(self, test_app):
        """Test web auth required decorator with invalid JWT"""
        with test_app.test_client() as client:
            with patch('auth.middleware.verify_jwt_in_request') as mock_verify:
                with patch('auth.middleware.url_for') as mock_url_for:
                    mock_verify.side_effect = Exception("Invalid token")
                    mock_url_for.return_value = '/auth/login'
                    
                    response = client.get('/web-protected')
                    
                    # Should redirect to login
                    assert response.status_code == 302
                    assert '/auth/login' in response.location
                    mock_url_for.assert_called_once_with('auth.login')


    
    @patch('auth.middleware.verify_jwt_in_request')
    def test_web_auth_required_with_args(self, mock_verify_jwt, test_app):
        """Test web_auth_required with route arguments"""
        mock_verify_jwt.return_value = None
        
        with test_app.test_client() as client:
            response = client.get('/web-protected-with-args/123')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['item_id'] == '123'
            assert data['message'] == 'success'
    
    @patch('auth.middleware.verify_jwt_in_request')
    def test_web_auth_required_with_kwargs(self, mock_verify_jwt):
        """Test web_auth_required passes kwargs correctly"""
        mock_verify_jwt.return_value = None
        
        @web_auth_required
        def test_function(arg1, kwarg1=None, kwarg2=None):
            return {
                'arg1': arg1,
                'kwarg1': kwarg1,
                'kwarg2': kwarg2
            }
        
        result = test_function('test_arg', kwarg1='test_kwarg1', kwarg2='test_kwarg2')
        
        assert result['arg1'] == 'test_arg'
        assert result['kwarg1'] == 'test_kwarg1'
        assert result['kwarg2'] == 'test_kwarg2'
    
    def test_web_auth_required_exception_in_verify(self, test_app):
        """Test web auth required decorator when verify_jwt_in_request raises exception"""
        with test_app.test_client() as client:
            with patch('auth.middleware.verify_jwt_in_request') as mock_verify:
                with patch('auth.middleware.url_for') as mock_url_for:
                    mock_verify.side_effect = Exception("Token verification failed")
                    mock_url_for.return_value = '/auth/login'
                    
                    response = client.get('/web-protected')
                    
                    # Should redirect to login
                    assert response.status_code == 302
                    assert '/auth/login' in response.location
                    mock_url_for.assert_called_once_with('auth.login')


    
    def test_web_auth_required_preserves_function_metadata(self):
        """Test that web_auth_required preserves original function metadata"""
        @web_auth_required
        def test_function():
            """Test web function docstring"""
            return "test"
        
        # Check that @wraps preserved the function name and docstring
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == "Test web function docstring"
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.url_for')
    def test_web_auth_required_url_for_called(self, mock_url_for, mock_verify_jwt, test_app):
        """Test that url_for is called correctly for redirect"""
        mock_verify_jwt.side_effect = Exception("Invalid token")
        mock_url_for.return_value = '/auth/login'
        
        with test_app.test_client() as client:
            response = client.get('/web-protected')
            
            assert response.status_code == 302
            mock_url_for.assert_called_once_with('auth.login')


class TestDecoratorIntegration:
    """Integration tests for decorators"""
    
    @pytest.fixture
    def test_app(self):
        """Create a comprehensive test app"""
        app = Flask(__name__)
        app.config['JWT_SECRET_KEY'] = 'test-secret'
        app.config['TESTING'] = True
        
        @app.route('/api/protected')
        @token_required
        def api_protected(current_user):
            return jsonify({'api': True, 'user': current_user['username']})
        
        @app.route('/web/protected')
        @web_auth_required
        def web_protected():
            return jsonify({'web': True, 'protected': True})
        
        @app.route('/auth/login')
        def login():
            return jsonify({'login': True})
        
        return app
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_both_decorators_success(self, mock_user_class, mock_get_jwt, mock_verify_jwt, test_app):
        """Test both decorators working correctly"""
        # Setup for token_required
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {'_id': 'user123', 'username': 'testuser'}
        mock_user_class.return_value = mock_user_instance
        
        with test_app.test_client() as client:
            # Test API route with token_required
            api_response = client.get('/api/protected')
            assert api_response.status_code == 200
            api_data = api_response.get_json()
            assert api_data['api'] is True
            assert api_data['user'] == 'testuser'
            
            # Reset mocks for web route test
            mock_verify_jwt.reset_mock()
            
            # Test web route with web_auth_required
            web_response = client.get('/web/protected')
            assert web_response.status_code == 200
            web_data = web_response.get_json()
            assert web_data['web'] is True
            assert web_data['protected'] is True
    
    @patch('auth.middleware.verify_jwt_in_request')
    def test_both_decorators_failure(self, mock_verify_jwt, test_app):
        """Test both decorators when authentication fails"""
        mock_verify_jwt.side_effect = Exception("Authentication failed")
        
        with test_app.test_client() as client:
            # Test API route
            api_response = client.get('/api/protected')
            assert api_response.status_code == 401
            api_data = api_response.get_json()
            assert api_data['success'] is False
            assert 'invalid or expired' in api_data['message'].lower()
            
            # Test web route with mocked url_for
            with patch('auth.middleware.url_for') as mock_url_for:
                mock_url_for.return_value = '/auth/login'
                
                web_response = client.get('/web/protected')
                assert web_response.status_code == 302
                assert '/auth/login' in web_response.location
                mock_url_for.assert_called_with('auth.login')




class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_token_required_no_args(self):
        """Test token_required decorator with no arguments function"""
        @token_required
        def no_args_function(current_user):
            return current_user
        
        # Function should be properly wrapped
        assert callable(no_args_function)
        assert no_args_function.__name__ == 'no_args_function'
    
    def test_web_auth_required_no_args(self):
        """Test web_auth_required decorator with no arguments function"""
        @web_auth_required
        def no_args_function():
            return "success"
        
        # Function should be properly wrapped
        assert callable(no_args_function)
        assert no_args_function.__name__ == 'no_args_function'
    
    @patch('auth.middleware.verify_jwt_in_request')
    @patch('auth.middleware.get_jwt_identity')
    @patch('auth.middleware.User')
    def test_token_required_complex_return_types(self, mock_user_class, mock_get_jwt, mock_verify_jwt):
        """Test token_required with different return types"""
        mock_verify_jwt.return_value = None
        mock_get_jwt.return_value = 'user123'
        
        mock_user_instance = Mock()
        mock_user_instance.get_user_by_id.return_value = {'_id': 'user123', 'username': 'testuser'}
        mock_user_class.return_value = mock_user_instance
        
        # Test function returning different types
        @token_required
        def return_dict(current_user):
            return {'user': current_user}
        
        @token_required
        def return_string(current_user):
            return "success"
        
        @token_required
        def return_tuple(current_user):
            return current_user, 200
        
        # All should work correctly
        dict_result = return_dict()
        assert isinstance(dict_result, dict)
        
        string_result = return_string()
        assert string_result == "success"
        
        tuple_result = return_tuple()
        assert isinstance(tuple_result, tuple)


# Additional fixtures for comprehensive testing
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        '_id': 'user123',
        'username': 'testuser',
        'email': 'test@example.com',
        'is_active': True
    }


@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    return app
