import pytest
from unittest.mock import Mock, patch
import json
from io import BytesIO

class TestAppRoutes:
    """Test main application routes"""
    
    def test_index_route(self, client):
        """Test index route"""
        response = client.get('/')
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_generate_page_authenticated(self, mock_get_user, client, sample_user_data):
        """Test generate page with authenticated user"""
        mock_get_user.return_value = sample_user_data
        
        response = client.get('/generate-page')
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_generate_page_unauthenticated(self, mock_get_user, client):
        """Test generate page without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/generate-page')
        assert response.status_code == 302  # Redirect to login
    
    @patch('app.get_current_user')
    @patch('app.generate_blog_from_youtube')
    @patch('app.BlogPost')
    def test_generate_blog_success(self, mock_blog_post_class, mock_generate, mock_get_user, 
                                  client, sample_user_data, sample_blog_content):
        """Test successful blog generation"""
        # Setup mocks
        mock_get_user.return_value = sample_user_data
        mock_generate.return_value = sample_blog_content
        
        mock_blog_instance = Mock()
        mock_blog_instance.create_post.return_value = {'_id': 'post123'}
        mock_blog_post_class.return_value = mock_blog_instance
        
        data = {
            'youtube_url': 'https://www.youtube.com/watch?v=test123',
            'language': 'en'
        }
        
        response = client.post('/generate', data=data)
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
        assert 'blog_content' in response_data
    
    @patch('app.get_current_user')
    def test_generate_blog_unauthenticated(self, mock_get_user, client):
        """Test blog generation without authentication"""
        mock_get_user.return_value = None
        
        data = {'youtube_url': 'https://www.youtube.com/watch?v=test123'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 401
        response_data = response.get_json()
        assert response_data['success'] is False
    
    @patch('app.get_current_user')
    def test_generate_blog_missing_url(self, mock_get_user, client, sample_user_data):
        """Test blog generation with missing URL"""
        # Add authentication
        mock_get_user.return_value = sample_user_data
        
        data = {'youtube_url': ''}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'required' in response_data['message']
    
    @patch('app.get_current_user')
    def test_generate_blog_invalid_url(self, mock_get_user, client, sample_user_data):
        """Test blog generation with invalid URL"""
        # Add authentication
        mock_get_user.return_value = sample_user_data
        
        data = {'youtube_url': 'https://invalid.com/video'}
        response = client.post('/generate', data=data)
        
        assert response.status_code == 400
        response_data = response.get_json()
        assert 'valid YouTube URL' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.PDFGeneratorTool')
    def test_download_pdf_success(self, mock_pdf_class, mock_get_user, client, sample_user_data):
        """Test successful PDF download"""
        mock_get_user.return_value = sample_user_data
        
        mock_pdf_instance = Mock()
        mock_pdf_instance.generate_pdf_bytes.return_value = b'mock pdf content'
        mock_pdf_class.return_value = mock_pdf_instance
        
        # Set session data
        with client.session_transaction() as sess:
            sess['current_blog'] = {
                'blog_content': 'Test content',
                'title': 'Test Blog'
            }
        
        response = client.get('/download')
        
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
    
    @patch('app.get_current_user')
    def test_download_pdf_no_data(self, mock_get_user, client, sample_user_data):
        """Test PDF download without blog data"""
        mock_get_user.return_value = sample_user_data
        
        response = client.get('/download')
        
        assert response.status_code == 404
        response_data = response.get_json()
        assert 'No blog data found' in response_data['message']
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_dashboard_success(self, mock_blog_post_class, mock_get_user, client, 
                              sample_user_data, sample_blog_post):
        """Test dashboard with authenticated user"""
        mock_get_user.return_value = sample_user_data
        
        mock_blog_instance = Mock()
        mock_blog_instance.get_user_posts.return_value = [sample_blog_post]
        mock_blog_post_class.return_value = mock_blog_instance
        
        response = client.get('/dashboard')
        
        assert response.status_code == 200
    
    @patch('app.get_current_user')
    def test_dashboard_unauthenticated(self, mock_get_user, client):
        """Test dashboard without authentication"""
        mock_get_user.return_value = None
        
        response = client.get('/dashboard')
        
        assert response.status_code == 302  # Redirect to login
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_delete_post_success(self, mock_blog_post_class, mock_get_user, client, sample_user_data):
        """Test successful post deletion"""
        mock_get_user.return_value = sample_user_data
        
        mock_blog_instance = Mock()
        mock_blog_instance.delete_post.return_value = True
        mock_blog_post_class.return_value = mock_blog_instance
        
        response = client.delete('/delete-post/post123')
        
        assert response.status_code == 200
        response_data = response.get_json()
        assert response_data['success'] is True
    
    @patch('app.get_current_user')
    @patch('app.BlogPost')
    def test_delete_post_not_found(self, mock_blog_post_class, mock_get_user, client, sample_user_data):
        """Test deleting non-existent post"""
        mock_get_user.return_value = sample_user_data
        
        mock_blog_instance = Mock()
        mock_blog_instance.delete_post.return_value = False
        mock_blog_post_class.return_value = mock_blog_instance
        
        response = client.delete('/delete-post/nonexistent')
        
        assert response.status_code == 404
        response_data = response.get_json()
        assert response_data['success'] is False
    
    def test_contact_route(self, client):
        """Test contact route"""
        response = client.get('/contact')
        assert response.status_code == 200

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_extract_video_id_valid_urls(self, valid_youtube_urls):
        """Test video ID extraction from valid URLs"""
        from app import extract_video_id
        
        expected_id = 'dQw4w9WgXcQ'
        for url in valid_youtube_urls:
            video_id = extract_video_id(url)
            assert video_id == expected_id
    
    def test_extract_video_id_invalid_urls(self, invalid_youtube_urls):
        """Test video ID extraction from invalid URLs"""
        from app import extract_video_id
        
        for url in invalid_youtube_urls:
            video_id = extract_video_id(url)
            assert video_id is None
