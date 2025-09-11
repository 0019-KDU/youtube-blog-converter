import json
from unittest.mock import Mock, patch

from bson import ObjectId


class TestBlogGenerationFlow:
    """Integration tests for blog generation flow"""

    def test_complete_blog_generation_flow(self, client, authenticated_user):
        """Test complete blog generation from URL to saved post"""
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        # Setup authentication
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'

        with patch('app.routes.blog.AuthService') as mock_auth_service, \
                patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
                patch('app.routes.blog.BlogPost') as mock_blog_class, \
                patch('app.utils.security.store_large_data') as mock_store:

            # Mock authentication
            mock_auth_service.get_current_user.return_value = authenticated_user

            # Mock blog generation
            mock_generate.return_value = '# Test Blog\n\nThis is a test blog post with sufficient content that meets the minimum character requirement for the blog generation validation. It contains more than 100 characters as required by the system validation rules.'

            # Mock blog post creation
            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': str(ObjectId()),
                'title': 'Test Blog',
                'content': '# Test Blog\n\nThis is a test blog post.',
                'youtube_url': youtube_url,
                'video_id': 'dQw4w9WgXcQ'
            }
            mock_blog_class.return_value = mock_blog

            # Mock storage
            mock_store.return_value = 'storage_key_123'

            response = client.post(
                '/generate',
                json={
                    'youtube_url': youtube_url,
                    'language': 'en'},
                headers={
                    'Authorization': f'Bearer test_token'})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'blog_content' in data
            assert 'Test Blog' in data['blog_content']

            # Verify services were called
            mock_generate.assert_called_once_with(youtube_url, 'en')
            mock_blog.create_post.assert_called_once()

    def test_blog_generation_with_invalid_url(
            self, client, authenticated_user):
        """Test blog generation with invalid YouTube URL"""
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'

        with patch('app.routes.blog.AuthService') as mock_auth_service:
            mock_auth_service.get_current_user.return_value = authenticated_user

            response = client.post(
                '/generate',
                json={
                    'youtube_url': 'https://www.example.com/video',
                    'language': 'en'},
                headers={
                    'Authorization': f'Bearer test_token'})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'valid YouTube URL' in data['message']

    def test_blog_generation_without_authentication(self, client):
        """Test blog generation without authentication"""
        response = client.post(
            '/generate',
            json={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'en'})

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Authentication required' in data['message']

    def test_blog_generation_service_error(self, client, authenticated_user):
        """Test blog generation when service throws error"""
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'

        with patch('app.routes.blog.AuthService') as mock_auth_service, \
                patch('app.routes.blog.generate_blog_from_youtube') as mock_generate:

            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_generate.side_effect = Exception("Service error")

            response = client.post(
                '/generate',
                json={
                    'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'language': 'en'},
                headers={
                    'Authorization': f'Bearer test_token'})

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Failed to generate blog' in data['message']

        def test_pdf_download_flow(self, client, authenticated_user):
            """Test PDF download flow"""
            blog_data = {
                'blog_content': '# Test Blog\n\nThis is test content.',
                'title': 'Test Blog',
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }

            with client.session_transaction() as sess:
                sess['user_id'] = str(authenticated_user['_id'])
                sess['access_token'] = 'test_token'
                sess['blog_storage_key'] = 'test_key'

            with patch('app.routes.blog.AuthService') as mock_auth_service, \
                    patch('app.utils.security.retrieve_large_data') as mock_retrieve, \
                    patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:

                mock_auth_service.get_current_user.return_value = authenticated_user
                mock_retrieve.return_value = blog_data

                mock_pdf = Mock()
                mock_pdf.generate_pdf_bytes.return_value = b'PDF content'
                mock_pdf_class.return_value = mock_pdf

                response = client.get(
                    '/download',
                    headers={
                        'Authorization': f'Bearer test_token'})

                assert response.status_code == 200
                assert response.content_type == 'application/pdf'
                assert b'PDF content' in response.data

                mock_pdf.generate_pdf_bytes.assert_called_once()

    def test_pdf_download_without_blog_data(self, client, authenticated_user):
        """Test PDF download without blog data"""
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'
            sess['blog_storage_key'] = 'test_key'

        with patch('app.routes.blog.AuthService') as mock_auth_service, \
                patch('app.utils.security.retrieve_large_data') as mock_retrieve:

            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_retrieve.return_value = None

            response = client.get(
                '/download',
                headers={
                    'Authorization': f'Bearer test_token'})

            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'No blog data found' in data['message']
