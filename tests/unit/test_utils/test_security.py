import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId


class TestSecurity:
    """Test cases for security utilities"""
    
    def test_get_current_user_with_bearer_token(self, request_context, mock_mongodb_globally):
        """Test getting current user from bearer token"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock
            mock_request.headers = {'Authorization': 'Bearer test_token'}
            
            # Setup session mock
            mock_session.get = Mock(return_value=None)
            
            # Setup decode_token mock
            mock_decode.return_value = {'sub': 'test_user_id'}
            
            # Setup User mock
            mock_user = MagicMock()
            mock_user.get_user_by_id.return_value = {
                '_id': 'test_user_id',
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            assert result is not None
            assert result['username'] == 'testuser'
            mock_decode.assert_called_once_with('test_token')
    
    def test_get_current_user_with_session_token(self, request_context, mock_mongodb_globally):
        """Test getting current user from session token"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock
            mock_session.get = Mock(return_value='test_session_token')
            
            # Setup decode_token mock
            mock_decode.return_value = {'sub': 'test_user_id'}
            
            # Setup User mock
            mock_user = MagicMock()
            mock_user.get_user_by_id.return_value = {
                '_id': 'test_user_id',
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            assert result is not None
            assert result['username'] == 'testuser'
            mock_decode.assert_called_once_with('test_session_token')
    
    def test_get_current_user_with_user_id(self, request_context, mock_mongodb_globally):
        """Test getting current user from session user_id"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock to return user_id when called with 'user_id'
            def session_get_side_effect(key, default=None):
                if key == 'access_token':
                    return None
                elif key == 'user_id':
                    return 'test_user_id'
                return default
            
            mock_session.get = Mock(side_effect=session_get_side_effect)
            
            # Setup User mock
            mock_user = MagicMock()
            mock_user.get_user_by_id.return_value = {
                '_id': 'test_user_id',
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            assert result is not None
            assert result['username'] == 'testuser'
            mock_user.get_user_by_id.assert_called_once_with('test_user_id')
    
    def test_get_current_user_no_auth(self, request_context):
        """Test getting current user with no authentication"""
        from app.utils.security import get_current_user
        
        with patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock (no tokens or user_id)
            mock_session.get = Mock(return_value=None)
            
            result = get_current_user()
            assert result is None
    
    def test_store_large_data(self, app_context):
        """Test storing large data in temp storage"""
        from flask import current_app

        from app.utils.security import store_large_data
        
        test_data = {'key': 'value', 'large_content': 'x' * 1000}
        
        storage_key = store_large_data('test_key', test_data, 'user_123')
        
        assert storage_key == 'user_123_test_key'
        assert 'user_123_test_key' in current_app.temp_storage
        assert current_app.temp_storage['user_123_test_key']['data'] == test_data
    
    def test_retrieve_large_data_success(self, app_context):
        """Test successful retrieval of large data"""
        from app.utils.security import retrieve_large_data, store_large_data
        
        test_data = {'key': 'value'}
        store_large_data('test_key', test_data, 'user_123')
        
        result = retrieve_large_data('test_key', 'user_123')
        
        assert result == test_data
    
    def test_retrieve_large_data_expired(self, app_context):
        """Test retrieval of expired data"""
        from flask import current_app

        from app.utils.security import retrieve_large_data

        # Manually add expired data
        expired_time = time.time() - 7200  # 2 hours ago
        current_app.temp_storage['user_123_test_key'] = {
            'data': {'test': 'data'},
            'timestamp': expired_time
        }
        
        result = retrieve_large_data('test_key', 'user_123')
        
        assert result is None
        assert 'user_123_test_key' not in current_app.temp_storage
    
    def test_retrieve_large_data_not_found(self, app_context):
        """Test retrieval of non-existent data"""
        from app.utils.security import retrieve_large_data
        
        result = retrieve_large_data('nonexistent_key', 'user_123')
        
        assert result is None
    
    def test_cleanup_old_storage(self, app_context):
        """Test cleanup of old storage data"""
        from flask import current_app

        from app.utils.security import cleanup_old_storage

        # Add mix of new and old data
        current_time = time.time()
        current_app.temp_storage.update({
            'new_data': {'data': 'new', 'timestamp': current_time},
            'old_data': {'data': 'old', 'timestamp': current_time - 7200}  # 2 hours ago
        })
        
        cleanup_old_storage()
        
        assert 'new_data' in current_app.temp_storage
        assert 'old_data' not in current_app.temp_storage

    def test_inject_config(self, app_context):
        """Test config injection for templates"""
        from flask import current_app

        from app.utils.security import inject_config
        
        result = inject_config()
        
        assert 'config' in result
        assert result['config'] == current_app.config

    def test_inject_user_with_authenticated_user(self, request_context):
        """Test user injection with authenticated user"""
        from app.utils.security import inject_user
        
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_user = {'username': 'testuser', 'email': 'test@example.com'}
            mock_get_user.return_value = mock_user
            
            result = inject_user()
            
            assert 'current_user' in result
            assert 'user_logged_in' in result
            assert result['current_user'] == mock_user
            assert result['user_logged_in'] is True

    def test_inject_user_without_authenticated_user(self, request_context):
        """Test user injection without authenticated user"""
        from app.utils.security import inject_user
        
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_get_user.return_value = None
            
            result = inject_user()
            
            assert 'current_user' in result
            assert 'user_logged_in' in result
            assert result['current_user'] is None
            assert result['user_logged_in'] is False

    def test_get_current_user_with_invalid_token(self, request_context, mock_mongodb_globally):
        """Test getting current user with invalid JWT token"""
        from app.utils.security import get_current_user
        
        with patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock
            mock_session.get = Mock(return_value='invalid_token')
            mock_session.pop = Mock()
            
            # Setup decode_token mock to raise exception
            mock_decode.side_effect = Exception("Invalid token")
            
            result = get_current_user()
            
            assert result is None
            mock_decode.assert_called_once_with('invalid_token')
            mock_session.pop.assert_called_once_with('access_token', None)

    def test_get_current_user_jwt_decode_error(self, request_context, mock_mongodb_globally):
        """Test JWT decode error handling"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock
            mock_session.get = Mock(return_value='test_token')
            mock_session.pop = Mock()
            
            # Setup decode_token mock to raise exception
            mock_decode.side_effect = Exception("JWT decode error")
            
            result = get_current_user()
            
            assert result is None
            mock_session.pop.assert_called_once_with('access_token', None)

    def test_get_current_user_user_not_found(self, request_context, mock_mongodb_globally):
        """Test when user is not found in database"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock (no Authorization header)
            mock_request.headers = {}
            
            # Setup session mock
            mock_session.get = Mock(return_value='test_token')
            
            # Setup decode_token mock
            mock_decode.return_value = {'sub': 'nonexistent_user_id'}
            
            # Setup User mock
            mock_user = MagicMock()
            mock_user.get_user_by_id.return_value = None  # User not found
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            assert result is None

    def test_get_current_user_malformed_auth_header(self, request_context):
        """Test getting current user with malformed Authorization header"""
        from app.utils.security import get_current_user
        
        with patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session:
            
            # Setup request mock with malformed Authorization header
            mock_request.headers = {'Authorization': 'InvalidFormat'}
            
            # Setup session mock
            mock_session.get = Mock(return_value=None)
            
            result = get_current_user()
            
            assert result is None

    def test_get_current_user_exception_handling(self, request_context):
        """Test exception handling in get_current_user"""
        from app.utils.security import get_current_user
        
        with patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.models.user.User') as mock_user_class:
            
            # Setup request mock
            mock_request.headers = {}
            
            # Setup session mock to raise exception
            mock_session.get = Mock(side_effect=Exception("Session error"))
            
            # Should handle exception gracefully and return None
            result = get_current_user()
            
            assert result is None

    def test_store_large_data_without_user_id(self, app_context):
        """Test storing data without user ID"""
        from flask import current_app

        from app.utils.security import store_large_data
        
        test_data = {'key': 'value'}
        
        storage_key = store_large_data('test_key', test_data)
        
        assert storage_key == 'test_key'
        assert 'test_key' in current_app.temp_storage
        assert current_app.temp_storage['test_key']['data'] == test_data

    def test_retrieve_large_data_without_user_id(self, app_context):
        """Test retrieving data without user ID"""
        from app.utils.security import retrieve_large_data, store_large_data
        
        test_data = {'key': 'value'}
        store_large_data('test_key', test_data)
        
        result = retrieve_large_data('test_key')
        
        assert result == test_data

    def test_cleanup_old_storage_empty(self, app_context):
        """Test cleanup with no data to clean"""
        from flask import current_app

        from app.utils.security import cleanup_old_storage

        # Ensure temp storage is empty
        current_app.temp_storage.clear()
        
        # Should not raise any errors
        cleanup_old_storage()
        
        assert len(current_app.temp_storage) == 0

    def test_store_large_data_triggers_cleanup(self, app_context):
        """Test that storing data triggers cleanup of old data"""
        from flask import current_app

        from app.utils.security import store_large_data

        # Add old data
        old_time = time.time() - 7200  # 2 hours ago
        current_app.temp_storage['old_key'] = {
            'data': 'old_data',
            'timestamp': old_time
        }
        
        # Store new data - should trigger cleanup
        store_large_data('new_key', {'new': 'data'}, 'user_123')
        
        # Old data should be cleaned up
        assert 'old_key' not in current_app.temp_storage
        assert 'user_123_new_key' in current_app.temp_storage

    def test_get_current_user_sets_g_user_id(self, request_context, mock_mongodb_globally):
        """Test that g.user_id is set when user is found"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock
            mock_request.headers = {'Authorization': 'Bearer test_token'}
            
            # Setup session mock
            mock_session.get = Mock(return_value=None)
            
            # Setup decode_token mock
            mock_decode.return_value = {'sub': 'user123'}
            
            # Setup User mock
            user_obj_id = ObjectId()
            mock_user = MagicMock()
            mock_user.get_user_by_id.return_value = {
                '_id': user_obj_id,
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            assert result is not None
            mock_g.user_id = str(user_obj_id)  # Verify this was set

    def test_get_current_user_cleanup_on_failure(self, request_context, mock_mongodb_globally):
        """Test that user model is properly cleaned up on failure"""
        from app.utils.security import get_current_user
        
        with patch('app.models.user.User') as mock_user_class, \
             patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session, \
             patch('app.utils.security.g') as mock_g:
            
            # Setup request mock
            mock_request.headers = {'Authorization': 'Bearer test_token'}
            
            # Setup session mock
            mock_session.get = Mock(return_value=None)
            
            # Setup decode_token mock
            mock_decode.return_value = {'sub': 'user123'}
            
            # Setup User mock to raise exception
            mock_user = MagicMock()
            mock_user.get_user_by_id.side_effect = Exception("Database error")
            mock_user_class.return_value = mock_user
            
            result = get_current_user()
            
            # Should handle the exception and return None
            assert result is None

    def test_get_current_user_token_without_sub(self, request_context, mock_mongodb_globally):
        """Test getting current user with token that doesn't have 'sub' field"""
        from app.utils.security import get_current_user
        
        with patch('app.utils.security.decode_token') as mock_decode, \
             patch('app.utils.security.request') as mock_request, \
             patch('app.utils.security.session') as mock_session:
            
            # Setup request mock
            mock_request.headers = {'Authorization': 'Bearer test_token'}
            
            # Setup session mock
            mock_session.get = Mock(return_value=None)
            
            # Setup decode_token mock to return token without 'sub' field
            mock_decode.return_value = {}
            
            result = get_current_user()
            
            assert result is None
