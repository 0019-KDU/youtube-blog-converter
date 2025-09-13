import json
from unittest.mock import Mock, patch

from bson import ObjectId


class TestBlogRoutes:
    """Test cases for blog routes"""

    def test_index_page(self, client):
        """Test main landing page"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'index.html' in response.data or response.status_code == 200

    def test_generate_page_authenticated(self, client, authenticated_user):
        """Test generate page access for authenticated user"""
        with patch('app.services.auth_service.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = authenticated_user
            response = client.get('/generate-page')
            assert response.status_code == 200

    def test_generate_page_unauthenticated(self, client):
        """Test generate page redirect for unauthenticated user"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = None
            response = client.get('/generate-page')
            assert response.status_code == 302  # Redirect to login

    def test_generate_blog_success(self, client, authenticated_user):
        """Test successful blog generation"""
        with patch('app.services.blog_service.generate_blog_from_youtube') as mock_generate, \
                patch('app.routes.blog.BlogPost') as mock_blog_class, \
                patch('app.utils.security.store_large_data') as mock_store, \
                patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.validate_youtube_url') as mock_validate, \
                patch('app.routes.blog.extract_video_id') as mock_extract:

            mock_generate.return_value = '# Test Blog\n\nThis is a test blog post with sufficient content for testing purposes.'
            mock_auth.return_value = authenticated_user
            mock_validate.return_value = True
            mock_extract.return_value = 'test123'

            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': str(ObjectId()),
                'title': 'Test Blog',
                'content': '# Test Blog\n\nContent...',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog
            mock_store.return_value = 'storage_key'

            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=test123',
                'language': 'en'
            })

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'blog_content' in data

    def test_generate_blog_invalid_url(self, client, authenticated_user):
        """Test blog generation with invalid URL"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = authenticated_user
            response = client.post('/generate', data={
                'youtube_url': 'https://invalid-url.com',
                'language': 'en'
            })
            assert response.status_code == 400

    def test_generate_blog_empty_url(self, client, authenticated_user):
        """Test blog generation with empty URL"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = authenticated_user
            response = client.post('/generate', data={
                'youtube_url': '',
                'language': 'en'
            })

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False

    def test_generate_blog_unauthenticated(self, client):
        """Test blog generation without authentication"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = None
            response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=test123',
                'language': 'en'
            })

            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False

    def test_dashboard_authenticated(self, client, authenticated_user):
        """Test dashboard access for authenticated user"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = []
            mock_blog_class.return_value = mock_blog

            response = client.get('/dashboard')
            assert response.status_code == 200

    def test_dashboard_unauthenticated(self, client):
        """Test dashboard redirect for unauthenticated user"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = None
            response = client.get('/dashboard')
            assert response.status_code == 302  # Redirect to login

    def test_download_pdf_success(self, client, authenticated_user):
        """Test PDF download"""
        blog_data = {
            'blog_content': '# Test Blog\n\nContent',
            'title': 'Test Blog',
            'youtube_url': 'https://www.youtube.com/watch?v=test123'
        }

        # Use a more direct approach by mocking all the dependencies properly
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
                patch('app.routes.blog.retrieve_large_data') as mock_retrieve, \
                patch('app.routes.blog.PDFGeneratorTool') as mock_pdf_class, \
                patch('app.routes.blog.sanitize_filename') as mock_sanitize, \
                patch('app.routes.blog.session') as mock_session:

            # Configure AuthService mock
            mock_auth_service.get_current_user.return_value = authenticated_user

            # Configure session mock
            mock_session.get.return_value = 'test_key'

            # Configure retrieve_large_data mock
            mock_retrieve.return_value = blog_data

            # Configure filename sanitization
            mock_sanitize.return_value = 'Test_Blog'

            # Configure PDF generator
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'PDF content'
            mock_pdf_class.return_value = mock_pdf

            response = client.get('/download')

            assert response.status_code == 200
            assert response.content_type == 'application/pdf'

    def test_download_pdf_no_data(self, client, authenticated_user):
        """Test PDF download with no blog data"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.utils.security.retrieve_large_data') as mock_retrieve:

            mock_auth.return_value = authenticated_user
            mock_retrieve.return_value = None

            response = client.get('/download')

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False

    def test_download_pdf_unauthenticated(self, client):
        """Test PDF download without authentication"""
        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth:
            mock_auth.return_value = None
            response = client.get('/download')
            assert response.status_code == 302  # Redirect to login

    def test_get_post_success(self, client, authenticated_user):
        """Test getting specific blog post"""
        post_id = str(ObjectId())

        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = {
                '_id': post_id,
                'title': 'Test Post',
                'content': 'Content',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog

            response = client.get(f'/get-post/{post_id}')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'post' in data

    def test_get_post_not_found(self, client, authenticated_user):
        """Test getting non-existent post"""
        post_id = str(ObjectId())

        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = None
            mock_blog_class.return_value = mock_blog

            response = client.get(f'/get-post/{post_id}')

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False

    def test_delete_post_success(self, client, authenticated_user):
        """Test successful post deletion"""
        post_id = str(ObjectId())

        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.delete_post.return_value = True
            mock_blog_class.return_value = mock_blog

            response = client.delete(f'/delete-post/{post_id}')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_delete_post_not_found(self, client, authenticated_user):
        """Test deleting non-existent post"""
        post_id = str(ObjectId())

        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.delete_post.return_value = False
            mock_blog_class.return_value = mock_blog

            response = client.delete(f'/delete-post/{post_id}')

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False

    def test_download_post_pdf_success(self, client, authenticated_user):
        """Test downloading PDF for specific post"""
        post_id = str(ObjectId())

        with patch('app.routes.blog.AuthService.get_current_user') as mock_auth, \
                patch('app.routes.blog.BlogPost') as mock_blog_class, \
                patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:

            mock_auth.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = {
                '_id': post_id,
                'title': 'Test Post',
                'content': '# Test Post\n\nContent',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog

            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'PDF content'
            mock_pdf_class.return_value = mock_pdf

            response = client.get(f'/download-post/{post_id}')

            assert response.status_code == 200
            assert response.content_type == 'application/pdf'

    def test_contact_page(self, client):
        """Test contact page"""
        response = client.get('/contact')
        assert response.status_code == 200
