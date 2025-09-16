import io
import json
from unittest.mock import MagicMock, patch

import pytest

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

    # Additional comprehensive tests for better coverage

    def test_index_exception(self, client):
        """Test index page with exception during rendering"""
        with patch('app.routes.blog.render_template', side_effect=Exception("Template error")):
            response = client.get('/')
            assert response.status_code == 500
            assert b'Error loading page' in response.data

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_page_exception(self, mock_get_user, client):
        """Test generate page with exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        with patch('app.routes.blog.render_template', side_effect=Exception("Template error")) as mock_render:
            # The route calls render_template twice - once for generate.html (which fails)
            # and then for error.html. We need to handle both calls.
            def side_effect(*args, **kwargs):
                if 'generate.html' in args:
                    raise Exception("Template error")
                return f"Error: {args[0]}"  # Return simple response for error.html

            mock_render.side_effect = side_effect
            response = client.get('/generate-page')
            assert response.status_code == 500
            # Check that error template was called
            assert any('error.html' in str(call) for call in mock_render.call_args_list)

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_empty_url(self, mock_get_user, client):
        """Test blog generation with empty URL"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        response = client.post('/generate', json={
            'youtube_url': '',
            'language': 'en'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'YouTube URL is required' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_invalid_url_format(self, mock_get_user, client):
        """Test blog generation with invalid URL format"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        response = client.post('/generate', json={
            'youtube_url': 'https://invalid-site.com/video'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'valid YouTube URL' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    def test_generate_blog_invalid_video_id(self, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with invalid video ID"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = None

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=invalid'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid YouTube URL' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    @patch('app.routes.blog.generate_blog_from_youtube')
    def test_generate_blog_generation_exception(self, mock_generate, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with exception during generation"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = 'dQw4w9WgXcQ'
        mock_generate.side_effect = Exception("Generation failed")

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to generate blog' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    @patch('app.routes.blog.generate_blog_from_youtube')
    def test_generate_blog_short_content(self, mock_generate, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with too short content"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = 'dQw4w9WgXcQ'
        mock_generate.return_value = 'Short content'  # Less than 100 chars

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Failed to generate blog content' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    @patch('app.routes.blog.generate_blog_from_youtube')
    def test_generate_blog_error_response(self, mock_generate, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with error response from generator"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = 'dQw4w9WgXcQ'
        mock_generate.return_value = 'ERROR: API key not found'

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        # The actual error message in the route is generic
        assert 'API key not found' in data['message'] or 'Failed to generate blog content' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    @patch('app.routes.blog.generate_blog_from_youtube')
    @patch('app.routes.blog.BlogPost')
    def test_generate_blog_db_save_failure(self, mock_blog_post_class, mock_generate, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with database save failure"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = 'dQw4w9WgXcQ'
        mock_generate.return_value = '# Test Blog\n\n' + 'A' * 100  # Long enough content

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.create_post.return_value = None  # Simulate save failure

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        # The actual error will be about NoneType since the code tries to access blog_post["_id"]
        assert 'Error generating blog' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.validate_youtube_url')
    @patch('app.routes.blog.extract_video_id')
    @patch('app.routes.blog.generate_blog_from_youtube')
    @patch('app.routes.blog.BlogPost')
    def test_generate_blog_db_exception(self, mock_blog_post_class, mock_generate, mock_extract_id, mock_validate, mock_get_user, client):
        """Test blog generation with database exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_validate.return_value = True
        mock_extract_id.return_value = 'dQw4w9WgXcQ'
        mock_generate.return_value = '# Test Blog\n\n' + 'A' * 100

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.create_post.side_effect = Exception("Database error")

        response = client.post('/generate', json={
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
        })

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Error generating blog' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_form_data(self, mock_get_user, client):
        """Test blog generation with form data instead of JSON"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        with patch('app.routes.blog.validate_youtube_url') as mock_validate, \
             patch('app.routes.blog.extract_video_id') as mock_extract_id, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_post_class:

            mock_validate.return_value = True
            mock_extract_id.return_value = 'dQw4w9WgXcQ'
            mock_generate.return_value = '# Test Blog\n\n' + 'A' * 100

            mock_blog_post = mock_blog_post_class.return_value
            mock_blog_post.create_post.return_value = {
                '_id': '456',
                'title': 'Test Blog',
                'content': '# Test Blog\n\n' + 'A' * 100
            }

            response = client.post('/generate', data={
                'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'es'
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_generate_blog_no_title_extracted(self, mock_get_user, client):
        """Test blog generation when no title can be extracted"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        with patch('app.routes.blog.validate_youtube_url') as mock_validate, \
             patch('app.routes.blog.extract_video_id') as mock_extract_id, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_post_class:

            mock_validate.return_value = True
            mock_extract_id.return_value = 'dQw4w9WgXcQ'
            mock_generate.return_value = 'Content without title heading\n\n' + 'A' * 100

            mock_blog_post = mock_blog_post_class.return_value
            mock_blog_post.create_post.return_value = {
                '_id': '456',
                'title': 'YouTube Blog Post',  # Default title
                'content': 'Content without title heading\n\n' + 'A' * 100
            }

            response = client.post('/generate', json={
                'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ'
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['title'] == 'YouTube Blog Post'

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_dashboard_unauthenticated(self, mock_get_user, client):
        """Test dashboard without authentication"""
        mock_get_user.return_value = None

        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_dashboard_db_exception(self, mock_blog_post_class, mock_get_user, client):
        """Test dashboard with database exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_user_posts.side_effect = Exception("Database error")

        response = client.get('/dashboard')
        assert response.status_code == 200  # Should still render with empty posts

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_dashboard_exception(self, mock_get_user, client):
        """Test dashboard with general exception"""
        mock_get_user.side_effect = Exception("Auth error")

        response = client.get('/dashboard')
        assert response.status_code == 302  # Redirect to login

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_download_pdf_unauthenticated(self, mock_get_user, client):
        """Test PDF download without authentication"""
        mock_get_user.return_value = None

        response = client.get('/download')
        assert response.status_code == 302  # Redirect to login

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.retrieve_large_data')
    def test_download_pdf_no_data(self, mock_retrieve, mock_get_user, client):
        """Test PDF download when no blog data found"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_retrieve.return_value = None

        with client.session_transaction() as session:
            session['blog_storage_key'] = 'test_key'

        response = client.get('/download')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No blog data found' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_download_pdf_no_session_key(self, mock_get_user, client):
        """Test PDF download without session key"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        response = client.get('/download')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No blog data found' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.retrieve_large_data')
    @patch('app.routes.blog.PDFGeneratorTool')
    def test_download_pdf_generation_exception(self, mock_pdf_tool_class, mock_retrieve, mock_get_user, client):
        """Test PDF download with generation exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}
        mock_retrieve.return_value = {
            'blog_content': '# Test Blog\nContent',
            'title': 'Test Blog'
        }

        mock_pdf_tool = mock_pdf_tool_class.return_value
        mock_pdf_tool.generate_pdf_bytes.side_effect = Exception("PDF generation failed")

        with client.session_transaction() as session:
            session['blog_storage_key'] = 'test_key'

        response = client.get('/download')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'PDF generation failed' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_delete_post_unauthenticated(self, mock_get_user, client):
        """Test post deletion without authentication"""
        mock_get_user.return_value = None

        response = client.delete('/delete-post/456')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Authentication required' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_delete_post_not_found(self, mock_blog_post_class, mock_get_user, client):
        """Test deletion of non-existent post"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.delete_post.return_value = False

        response = client.delete('/delete-post/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Post not found' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_delete_post_db_exception(self, mock_blog_post_class, mock_get_user, client):
        """Test post deletion with database exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.delete_post.side_effect = Exception("Database error")

        response = client.delete('/delete-post/456')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_get_post_unauthenticated(self, mock_get_user, client):
        """Test getting post without authentication"""
        mock_get_user.return_value = None

        response = client.get('/get-post/456')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Authentication required' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_get_post_success(self, mock_blog_post_class, mock_get_user, client):
        """Test successful post retrieval"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_post = {
            '_id': '456',
            'title': 'Test Post',
            'content': 'Test content',
            'created_at': '2024-01-01'
        }

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.return_value = mock_post

        response = client.get('/get-post/456')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['post']['title'] == 'Test Post'

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_get_post_not_found(self, mock_blog_post_class, mock_get_user, client):
        """Test getting non-existent post"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.return_value = None

        response = client.get('/get-post/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Post not found' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_get_post_db_exception(self, mock_blog_post_class, mock_get_user, client):
        """Test get post with database exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.side_effect = Exception("Database error")

        response = client.get('/get-post/456')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.blog.AuthService.get_current_user')
    def test_download_post_pdf_unauthenticated(self, mock_get_user, client):
        """Test post PDF download without authentication"""
        mock_get_user.return_value = None

        response = client.get('/download-post/456')
        assert response.status_code == 302  # Redirect to login

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_download_post_pdf_not_found(self, mock_blog_post_class, mock_get_user, client):
        """Test PDF download for non-existent post"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.return_value = None

        response = client.get('/download-post/nonexistent')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Post not found' in data['message']

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    @patch('app.routes.blog.PDFGeneratorTool')
    def test_download_post_pdf_success(self, mock_pdf_tool_class, mock_blog_post_class, mock_get_user, client):
        """Test successful post PDF download"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_post = {
            '_id': '456',
            'title': 'Test Post',
            'content': '# Test Post\nContent for PDF'
        }

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.return_value = mock_post

        mock_pdf_tool = mock_pdf_tool_class.return_value
        mock_pdf_tool.generate_pdf_bytes.return_value = b'PDF content'

        response = client.get('/download-post/456')
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    def test_download_post_pdf_db_exception(self, mock_blog_post_class, mock_get_user, client):
        """Test post PDF download with database exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.side_effect = Exception("Database error")

        response = client.get('/download-post/456')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False

    @patch('app.routes.blog.AuthService.get_current_user')
    @patch('app.routes.blog.BlogPost')
    @patch('app.routes.blog.PDFGeneratorTool')
    def test_download_post_pdf_generation_exception(self, mock_pdf_tool_class, mock_blog_post_class, mock_get_user, client):
        """Test post PDF download with generation exception"""
        mock_get_user.return_value = {'_id': '123', 'username': 'testuser'}

        mock_post = {
            '_id': '456',
            'title': 'Test Post',
            'content': '# Test Post\nContent for PDF'
        }

        mock_blog_post = mock_blog_post_class.return_value
        mock_blog_post.get_post_by_id.return_value = mock_post

        mock_pdf_tool = mock_pdf_tool_class.return_value
        mock_pdf_tool.generate_pdf_bytes.side_effect = Exception("PDF generation failed")

        response = client.get('/download-post/456')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'PDF generation failed' in data['message']

    def test_contact_page(self, client):
        """Test contact page"""
        response = client.get('/contact')
        assert response.status_code == 200

    def test_contact_page_exception(self, client):
        """Test contact page with exception"""
        with patch('app.routes.blog.render_template') as mock_render:
            def side_effect(*args, **kwargs):
                if 'contact.html' in args:
                    raise Exception("Template error")
                return f"Error: {args[0]}"  # Return simple response for error.html

            mock_render.side_effect = side_effect
            response = client.get('/contact')
            assert response.status_code == 500
            # Check that error template was called
            assert any('error.html' in str(call) for call in mock_render.call_args_list)
