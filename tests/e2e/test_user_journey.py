import pytest
import json
from unittest.mock import Mock, patch
from bson import ObjectId
import time

class TestUserJourney:
    """End-to-end tests for complete user journeys"""
    
    def test_complete_new_user_journey(self, client):
        """Test complete journey: register -> login -> generate blog -> download PDF"""
        user_id = str(ObjectId())
        
        # Step 1: User Registration
        with patch('app.routes.auth.User') as mock_user_class:
            mock_user = Mock()
            mock_user.create_user.return_value = {
                'success': True,
                'user': {
                    '_id': user_id,
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
            
            assert response.status_code == 302  # Redirect after registration
        
        # Step 2: Access Dashboard
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = {
                '_id': user_id,
                'username': 'newuser',
                'email': 'newuser@example.com'
            }
            
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = []
            mock_blog_class.return_value = mock_blog
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'newuser' in response.data
        
        # Step 3: Generate Blog
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_class, \
             patch('app.utils.security.store_large_data') as mock_store:
            
            mock_auth_service.get_current_user.return_value = {
                '_id': user_id,
                'username': 'newuser',
                'email': 'newuser@example.com'
            }
            
            mock_generate.return_value = '# AI Technology Trends\n\nThis is a comprehensive blog post about AI technology trends with sufficient content for testing.'
            
            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': str(ObjectId()),
                'title': 'AI Technology Trends',
                'content': '# AI Technology Trends\n\nContent...',
                'user_id': user_id
            }
            mock_blog_class.return_value = mock_blog
            
            mock_store.return_value = 'storage_key_123'
            
            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'en'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'AI Technology Trends' in data['blog_content']
        
        # Step 4: Download PDF
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.utils.security.retrieve_large_data') as mock_retrieve, \
             patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:
            
            mock_auth_service.get_current_user.return_value = {
                '_id': user_id,
                'username': 'newuser',
                'email': 'newuser@example.com'
            }
            
            mock_retrieve.return_value = {
                'blog_content': '# AI Technology Trends\n\nContent...',
                'title': 'AI Technology Trends',
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }
            
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'%PDF-1.4 mock content'
            mock_pdf_class.return_value = mock_pdf
            
            with client.session_transaction() as sess:
                sess['blog_storage_key'] = 'storage_key_123'
            
            response = client.get('/download')
            assert response.status_code == 200
            assert response.content_type == 'application/pdf'
    
    def test_returning_user_journey(self, client, authenticated_user):
        """Test returning user journey: login -> view posts -> generate new blog"""
        user_id = str(authenticated_user['_id'])
        
        # Step 1: View existing posts on dashboard
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = [
                {
                    '_id': str(ObjectId()),
                    'title': 'Previous Blog Post',
                    'created_at': '2024-01-01T00:00:00',
                    'word_count': 500
                }
            ]
            mock_blog_class.return_value = mock_blog
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'Previous Blog Post' in response.data
        
        # Step 2: Generate new blog
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_class, \
             patch('app.utils.security.store_large_data') as mock_store:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            mock_generate.return_value = '# New Technology Review\n\nThis is a new blog post about technology reviews with comprehensive content.'
            
            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': str(ObjectId()),
                'title': 'New Technology Review',
                'content': '# New Technology Review\n\nContent...',
                'user_id': user_id
            }
            mock_blog_class.return_value = mock_blog
            
            mock_store.return_value = 'new_storage_key'
            
            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=kJQP7kiw5Fk',
                'language': 'en'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'New Technology Review' in data['blog_content']
        
        # Step 3: View updated dashboard
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = [
                {
                    '_id': str(ObjectId()),
                    'title': 'New Technology Review',
                    'created_at': '2024-01-02T00:00:00',
                    'word_count': 600
                },
                {
                    '_id': str(ObjectId()),
                    'title': 'Previous Blog Post',
                    'created_at': '2024-01-01T00:00:00',
                    'word_count': 500
                }
            ]
            mock_blog_class.return_value = mock_blog
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            assert b'New Technology Review' in response.data
            assert b'Previous Blog Post' in response.data
    
    def test_error_recovery_journey(self, client, authenticated_user):
        """Test user journey with error recovery scenarios"""
        # Step 1: Attempt blog generation with invalid URL
        with patch('app.routes.blog.AuthService') as mock_auth_service:
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            response = client.post('/generate', data={
                'youtube_url': 'https://invalid-url.com/video',
                'language': 'en'
            })
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
        
        # Step 2: Retry with valid URL but service error
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_generate.return_value = 'ERROR: YouTube API error'
            
            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'en'
            })
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
        
        # Step 3: Successful retry
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_class, \
             patch('app.utils.security.store_large_data') as mock_store:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            mock_generate.return_value = '# Successful Blog Generation\n\nThis blog was generated successfully after previous errors. This content is now long enough to pass the minimum length validation check that requires at least 100 characters for a valid blog post generation.'
            
            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': str(ObjectId()),
                'title': 'Successful Blog Generation',
                'content': '# Successful Blog Generation\n\nContent...',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog
            
            mock_store.return_value = 'success_storage_key'
            
            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=tR-qQcNT_fY',
                'language': 'en'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'Successful Blog Generation' in data['blog_content']
