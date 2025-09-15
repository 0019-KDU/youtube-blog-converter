import pytest
from unittest.mock import patch, MagicMock
import json

class TestIntegrationFlows:
    
    @patch('app.routes.auth.User')
    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.generate_blog_from_youtube')
    @patch('app.routes.blog.BlogPost')
    def test_full_user_flow(self, mock_blog_post_class, mock_generate, mock_get_user, mock_user_class, client):
        """Test complete user flow: register -> login -> generate blog -> view dashboard"""
        
        # 1. Register user
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
        
        # 2. Login (extract token from registration response)
        registration_data = json.loads(response.data)
        token = registration_data['access_token']
        
        # 3. Generate blog
        mock_get_user.return_value = {
            '_id': '507f1f77bcf86cd799439011',
            'username': 'testuser'
        }
        mock_generate.return_value = '# Test Blog\n\nThis is a comprehensive generated blog content with enough text to pass validation requirements. It contains detailed information about the topic discussed in the YouTube video and provides valuable insights to readers.'
        
        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.create_post.return_value = {
            '_id': '507f1f77bcf86cd799439012',
            'title': 'Test Blog',
            'content': '# Test Blog\n\nThis is a comprehensive generated blog content with enough text to pass validation requirements. It contains detailed information about the topic discussed in the YouTube video and provides valuable insights to readers.'
        }
        
        response = client.post('/generate', 
            headers={'Authorization': f'Bearer {token}'},
            json={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }
        )
        assert response.status_code == 200
        
        # 4. View dashboard
        mock_blog_post.get_user_posts.return_value = [
            {
                '_id': '507f1f77bcf86cd799439012',
                'title': 'Test Blog',
                'created_at': '2024-01-01T00:00:00Z',
                'word_count': 150,
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'video_id': 'dQw4w9WgXcQ'
            }
        ]
        
        response = client.get('/dashboard',
            headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200