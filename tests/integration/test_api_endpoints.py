import json
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId


class TestAPIEndpoints:
    """Integration tests for API endpoints"""
    
    def test_registration_api_endpoint(self, client):
        """Test registration API endpoint"""
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': str(ObjectId()),
                    'username': 'testuser',
                    'email': 'test@example.com'
                }
            }
            mock_user_class.return_value = mock_user
            
            response = client.post('/auth/register',
                json={
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'password123',
                    'confirm_password': 'password123'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'access_token' in data
            assert 'user' in data
    
    def test_login_api_endpoint(self, client):
        """Test login API endpoint"""
        user_data = {
            '_id': ObjectId(),
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.authenticate_user.return_value = user_data
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
            assert 'access_token' in data
    
    def test_verify_token_endpoint(self, client, authenticated_user):
        """Test token verification endpoint"""
        with patch('app.utils.security.get_current_user') as mock_get_user:
            mock_get_user.return_value = authenticated_user
            
            response = client.post('/auth/verify-token')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'user' in data
    
    def test_get_post_endpoint(self, client, authenticated_user):
        """Test get post API endpoint"""
        post_id = str(ObjectId())
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = {
                '_id': post_id,
                'title': 'Test Post',
                'content': '# Test\n\nContent',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog
            
            response = client.get(f'/get-post/{post_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'post' in data
    
    def test_delete_post_endpoint(self, client, authenticated_user):
        """Test delete post API endpoint"""
        post_id = str(ObjectId())
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            mock_blog = Mock()
            mock_blog.delete_post.return_value = True
            mock_blog_class.return_value = mock_blog
            
            response = client.delete(f'/delete-post/{post_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    def test_dashboard_endpoint(self, client, authenticated_user):
        """Test dashboard endpoint"""
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = [
                {
                    '_id': str(ObjectId()),
                    'title': 'Test Post 1',
                    'created_at': '2024-01-01T00:00:00',
                    'word_count': 150
                },
                {
                    '_id': str(ObjectId()),
                    'title': 'Test Post 2',
                    'created_at': '2024-01-02T00:00:00',
                    'word_count': 200
                }
            ]
            mock_blog_class.return_value = mock_blog
            
            response = client.get('/dashboard')
            
            assert response.status_code == 200
            assert b'Test Post 1' in response.data
            assert b'Test Post 2' in response.data