import datetime
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId


class TestAuthService:
    """Test cases for AuthService"""
    
    def test_get_current_user_from_session(self, flask_contexts):
        """Test getting current user from session token"""
        from flask import session

        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.User') as mock_user_class, \
            patch('app.services.auth_service.decode_token') as mock_decode:
            
            session['access_token'] = 'test_session_token'
            # Use a valid ObjectId format for the user ID
            user_obj_id = ObjectId()
            mock_decode.return_value = {'sub': str(user_obj_id)}
            
            # Create a proper mock user instance
            mock_user = Mock()
            user_data = {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user.get_user_by_id.return_value = user_data
            mock_user_class.return_value = mock_user
            
            result = AuthService.get_current_user()
            
            assert result is not None
            assert result['username'] == 'testuser'
            mock_decode.assert_called_once_with('test_session_token')

    
    def test_get_current_user_from_session_user_id(self, flask_contexts):
        """Test getting current user from session user_id"""
        from flask import session

        from app.services.auth_service import AuthService
        
        user_id = str(ObjectId())
        
        with patch('app.services.auth_service.User') as mock_user_class:
            
            session['user_id'] = user_id
            
            mock_user = Mock()
            mock_user.get_user_by_id.return_value = {
                '_id': ObjectId(user_id),
                'username': 'testuser',
                'email': 'test@example.com'
            }
            mock_user_class.return_value = mock_user
            
            result = AuthService.get_current_user()
            
            assert result is not None
            assert result['username'] == 'testuser'
            mock_user.get_user_by_id.assert_called_once_with(user_id)
    
    def test_get_current_user_invalid_token(self, flask_contexts):
        """Test getting current user with invalid token"""
        from flask import request, session

        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.decode_token') as mock_decode:
            
            # Use flask_contexts to access the real Flask request object
            with flask_contexts.test_request_context(headers={'Authorization': 'Bearer invalid-token'}):
                mock_decode.side_effect = Exception("Invalid token")
                
                result = AuthService.get_current_user()
                
                assert result is None
                mock_decode.assert_called_once_with('invalid-token')
    
    def test_get_current_user_no_token(self, flask_contexts):
        """Test getting current user with no authentication"""
        from app.services.auth_service import AuthService
        
        result = AuthService.get_current_user()
        
        assert result is None
    
    def test_get_current_user_user_not_found(self, flask_contexts):
        """Test getting current user when user not found in database"""
        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.decode_token') as mock_decode, \
             patch('app.services.auth_service.User') as mock_user_class:
            
            with flask_contexts.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                mock_decode.return_value = {'sub': 'nonexistent-user'}
                
                mock_user = Mock()
                mock_user.get_user_by_id.return_value = None  # User not found
                mock_user_class.return_value = mock_user
                
                result = AuthService.get_current_user()
                
                assert result is None
    
    def test_get_current_user_malformed_auth_header(self, flask_contexts):
        """Test getting current user with malformed Authorization header"""
        from app.services.auth_service import AuthService
        
        with flask_contexts.test_request_context(headers={'Authorization': 'InvalidFormat'}):
            
            result = AuthService.get_current_user()
            
            assert result is None
    
    def test_get_current_user_exception_handling(self, flask_contexts):
        """Test exception handling in get_current_user"""
        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.User') as mock_user_class:
            
            mock_user_class.side_effect = Exception("Database error")
            
            # Should handle exception gracefully and return None
            result = AuthService.get_current_user()
            
            assert result is None
    
    def test_is_authenticated_true(self):
        """Test is_authenticated returns True for authenticated user"""
        from app.services.auth_service import AuthService
        
        with patch.object(AuthService, 'get_current_user') as mock_get_user:
            mock_get_user.return_value = {'_id': ObjectId(), 'username': 'testuser'}
            
            result = AuthService.is_authenticated()
            
            assert result is True
            mock_get_user.assert_called_once()
    
    def test_is_authenticated_false(self):
        """Test is_authenticated returns False for non-authenticated user"""
        from app.services.auth_service import AuthService
        
        with patch.object(AuthService, 'get_current_user') as mock_get_user:
            mock_get_user.return_value = None
            
            result = AuthService.is_authenticated()
            
            assert result is False
            mock_get_user.assert_called_once()
    
    def test_clear_session(self, flask_contexts):
        """Test clearing user session"""
        from flask import session

        from app.services.auth_service import AuthService

        # Set some session data
        session['test_key'] = 'test_value'
        session['user_id'] = 'test_user_id'
        
        # Clear the session
        AuthService.clear_session()
        
        # Verify session is empty
        assert len(session) == 0
    
    def test_get_current_user_token_without_sub(self, flask_contexts):
        """Test getting current user with token that doesn't have 'sub' field"""
        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.decode_token') as mock_decode:
            
            with flask_contexts.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                mock_decode.return_value = {}  # Token without 'sub' field
                
                result = AuthService.get_current_user()
                
                assert result is None
    
    def test_get_current_user_cleanup_on_failure(self, flask_contexts):
        """Test that user model is properly cleaned up on failure"""
        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.decode_token') as mock_decode, \
             patch('app.services.auth_service.User') as mock_user_class:
            
            with flask_contexts.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                mock_decode.return_value = {'sub': 'user123'}
                
                mock_user = Mock()
                mock_user.get_user_by_id.side_effect = Exception("Database error")
                mock_user_class.return_value = mock_user
                
                result = AuthService.get_current_user()
                
                # Should handle the exception and return None
                assert result is None
    
    def test_get_current_user_session_fallback_with_invalid_user_id(self, flask_contexts):
        """Test session user_id fallback with invalid ObjectId format"""
        from flask import session

        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.User') as mock_user_class:
            
            session['user_id'] = 'invalid-object-id'
            
            mock_user = Mock()
            mock_user.get_user_by_id.return_value = None  # User not found
            mock_user_class.return_value = mock_user
            
            result = AuthService.get_current_user()
            
            assert result is None
    
    def test_get_current_user_sets_g_user_id(self, flask_contexts):
        """Test that g.user_id is set when user is found"""
        from flask import g

        from app.services.auth_service import AuthService
        
        with patch('app.services.auth_service.decode_token') as mock_decode, \
             patch('app.services.auth_service.User') as mock_user_class:
            
            with flask_contexts.test_request_context(headers={'Authorization': 'Bearer test-token'}):
                mock_decode.return_value = {'sub': 'user123'}
                
                user_obj_id = ObjectId()
                mock_user = Mock()
                mock_user.get_user_by_id.return_value = {
                    '_id': user_obj_id,
                    'username': 'testuser',
                    'email': 'test@example.com'
                }
                mock_user_class.return_value = mock_user
                
                result = AuthService.get_current_user()
                
                assert result is not None
                assert g.user_id == str(user_obj_id)
