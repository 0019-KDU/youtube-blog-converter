import pytest
import json
from unittest.mock import patch, MagicMock
import io

class TestBlogRoutes:
    
    def test_index(self, client):
        """Test index page"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'BlogGen Pro' in response.data
    
    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_page_authenticated(self, mock_get_user, client):
        """Test generate page with authenticated user"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        
        response = client.get('/generate-page')
        assert response.status_code == 200
        assert b'Generate' in response.data
    
    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_page_unauthenticated(self, mock_get_user, client):
        """Test generate page without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/generate-page')
        assert response.status_code == 302  # Redirect to login
    
    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.generate_blog_from_youtube')
    @patch('app.routes.blog.BlogPost')
    def test_generate_blog_success(self, mock_blog_post_class, mock_generate, mock_get_user, client):
        """Test successful blog generation"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_generate.return_value = '# Test Blog\n\nThis is a comprehensive test content for the blog post that contains enough characters to pass the validation requirements. It includes detailed information about the topic and provides valuable insights to readers.'
        
        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.create_post.return_value = {
            '_id': '456',
            'title': 'Test Blog',
            'content': '# Test Blog\n\nThis is a comprehensive test content for the blog post that contains enough characters to pass the validation requirements. It includes detailed information about the topic and provides valuable insights to readers.'
        }
        
        response = client.post('/generate', json={
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'language': 'en'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'blog_content' in data
    
    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_unauthenticated(self, mock_get_user, client):
        """Test blog generation without authentication"""
        mock_get_user.return_value = None
        
        response = client.post('/generate', json={
            'youtube_url': 'https://www.youtube.com/watch?v=test'
        })
        
        assert response.status_code == 401
    
    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_dashboard(self, mock_blog_post_class, mock_get_user, client):
        """Test dashboard page"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        
        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_user_posts.return_value = [
            {'_id': '1', 'title': 'Post 1', 'word_count': 100, 'created_at': '2024-01-01T00:00:00Z', 'youtube_url': 'https://youtube.com/watch?v=1', 'video_id': '1'},
            {'_id': '2', 'title': 'Post 2', 'word_count': 150, 'created_at': '2024-01-02T00:00:00Z', 'youtube_url': 'https://youtube.com/watch?v=2', 'video_id': '2'}
        ]
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data or b'testuser' in response.data
    
    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.retrieve_large_data')
    @patch('app.routes.blog.PDFGeneratorTool')
    def test_download_pdf(self, mock_pdf_tool_class, mock_retrieve, mock_get_user, client):
        """Test PDF download"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_retrieve.return_value = {
            'blog_content': '# Test Blog\nContent',
            'title': 'Test Blog'
        }
        
        mock_pdf_tool = mock_pdf_tool_class.return_value
        mock_pdf_tool.generate_pdf_bytes.return_value = b'PDF content'
        
        with client.session_transaction() as session:
            session['blog_storage_key'] = 'test_key'
        
        response = client.get('/download')
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
    
    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_delete_post(self, mock_blog_post_class, mock_get_user, client):
        """Test post deletion"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        
        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.delete_post.return_value = True
        
        response = client.delete('/delete-post/456')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
