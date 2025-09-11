import json
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId


class TestCompleteWorkflow:
    """Test complete application workflows"""
    
    def test_multi_language_blog_generation(self, client, authenticated_user):
        """Test blog generation in multiple languages"""
        languages = ['en', 'es', 'fr']
        
        for lang in languages:
            with patch('app.routes.blog.AuthService') as mock_auth_service, \
                 patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
                 patch('app.routes.blog.BlogPost') as mock_blog_class, \
                 patch('app.utils.security.store_large_data') as mock_store:
                
                mock_auth_service.get_current_user.return_value = authenticated_user
                mock_generate.return_value = f'# Blog in {lang.upper()}\n\nThis is content in {lang} language with sufficient length to pass validation checks and meet the minimum 100 character requirement for blog generation.'
                
                mock_blog = Mock()
                mock_blog.create_post.return_value = {
                    '_id': str(ObjectId()),
                    'title': f'Blog in {lang.upper()}',
                    'content': f'# Blog in {lang.upper()}\n\nContent...',
                    'user_id': str(authenticated_user['_id'])
                }
                mock_blog_class.return_value = mock_blog
                
                mock_store.return_value = f'{lang}_storage_key'
                
                # Use valid 11-character video IDs
                video_ids = {'en': 'dQw4w9WgXcQ', 'es': 'kJQP7kiw5Fk', 'fr': 'tR-qQcNT_fY'}
                response = client.post('/generate', data={
                    'youtube_url': f'https://www.youtube.com/watch?v={video_ids[lang]}',
                    'language': lang
                })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert f'Blog in {lang.upper()}' in data['blog_content']
                
                # Verify language was passed to service
                mock_generate.assert_called_with(
                    f'https://www.youtube.com/watch?v={video_ids[lang]}', lang)
    
    def test_bulk_operations_workflow(self, client, authenticated_user):
        """Test workflow with multiple blog posts and operations"""
        post_ids = []
        
        # Generate multiple blog posts
        for i in range(3):
            with patch('app.routes.blog.AuthService') as mock_auth_service, \
                 patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
                 patch('app.routes.blog.BlogPost') as mock_blog_class, \
                 patch('app.utils.security.store_large_data') as mock_store:
                
                mock_auth_service.get_current_user.return_value = authenticated_user
                
                post_id = str(ObjectId())
                post_ids.append(post_id)
                
                mock_generate.return_value = f'# Blog Post {i+1}\n\nThis is content for blog post {i+1} with sufficient length to pass validation checks and meet the minimum 100 character requirement for blog generation.'
                
                mock_blog = Mock()
                mock_blog.create_post.return_value = {
                    '_id': post_id,
                    'title': f'Blog Post {i+1}',
                    'content': f'# Blog Post {i+1}\n\nContent...',
                    'user_id': str(authenticated_user['_id'])
                }
                mock_blog_class.return_value = mock_blog
                
                mock_store.return_value = f'storage_key_{i}'
                
                # Use valid video IDs for bulk operations
                bulk_video_ids = ['dQw4w9WgXcQ', 'kJQP7kiw5Fk', 'tR-qQcNT_fY']
                response = client.post('/generate', data={
                    'youtube_url': f'https://www.youtube.com/watch?v={bulk_video_ids[i]}',
                    'language': 'en'
                })
                
                assert response.status_code == 200
        
        # View all posts on dashboard
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = [
                {
                    '_id': post_ids[i],
                    'title': f'Blog Post {i+1}',
                    'created_at': f'2024-01-0{i+1}T00:00:00',
                    'word_count': 100 + i*50
                }
                for i in range(3)
            ]
            mock_blog_class.return_value = mock_blog
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            for i in range(3):
                assert f'Blog Post {i+1}'.encode() in response.data
        
        # Delete one post
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.models.user.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.delete_post.return_value = True
            mock_blog_class.return_value = mock_blog
            
            delete_response = client.delete(f'/delete-post/{post_ids[0]}')
            assert delete_response.status_code == 200
            
            delete_data = json.loads(delete_response.data)
            assert delete_data['success'] is True
    
    def test_complete_user_journey(self, client, authenticated_user):
        """Test complete user journey from login to blog generation to PDF download"""
        # Step 1: Generate blog post
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate, \
             patch('app.routes.blog.BlogPost') as mock_blog_class, \
             patch('app.utils.security.store_large_data') as mock_store:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            blog_content = "# Complete Journey Blog\n\nThis is a comprehensive test of the complete user journey including all main features with sufficient length to pass validation checks and meet the minimum requirement."
            mock_generate.return_value = blog_content
            
            post_id = str(ObjectId())
            mock_blog = Mock()
            mock_blog.create_post.return_value = {
                '_id': post_id,
                'title': 'Complete Journey Blog',
                'content': blog_content,
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog
            mock_store.return_value = 'journey_storage_key'
            
            # Generate blog
            generate_response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'en'
            })
            
            assert generate_response.status_code == 200
            generate_data = json.loads(generate_response.data)
            assert generate_data['success'] is True
        
        # Step 2: View the generated blog
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.BlogPost') as mock_blog_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = {
                '_id': post_id,
                'title': 'Complete Journey Blog',
                'content': blog_content,
                'created_at': '2024-01-01T00:00:00',
                'word_count': 150
            }
            mock_blog_class.return_value = mock_blog
            
            view_response = client.get(f'/get-post/{post_id}')
            assert view_response.status_code == 200
            view_data = json.loads(view_response.data)
            assert view_data['success'] is True
            assert 'Complete Journey Blog' in view_data['post']['title']
        
        # Step 3: Download as PDF
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.retrieve_large_data') as mock_retrieve, \
             patch('app.routes.blog.PDFGeneratorTool') as mock_pdf_class, \
             patch('app.routes.blog.sanitize_filename') as mock_sanitize, \
             patch('app.routes.blog.session') as mock_session:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_session.get.return_value = 'journey_storage_key'
            mock_retrieve.return_value = {
                'blog_content': blog_content,
                'title': 'Complete Journey Blog',
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            }
            mock_sanitize.return_value = 'Complete_Journey_Blog'
            
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'PDF content'
            mock_pdf_class.return_value = mock_pdf
            
            pdf_response = client.get('/download')
            assert pdf_response.status_code == 200
            assert pdf_response.content_type == 'application/pdf'
    
    def test_error_handling_workflow(self, client, authenticated_user):
        """Test error handling throughout the workflow"""
        # Test invalid YouTube URL with authentication
        with patch('app.routes.blog.AuthService') as mock_auth_service:
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            invalid_response = client.post('/generate', data={
                'youtube_url': 'https://invalid-url.com/video',
                'language': 'en'
            })
            # Invalid URL should return 400 status code
            assert invalid_response.status_code == 400
        
        # Test service failure
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.generate_blog_from_youtube') as mock_generate:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            # Mock a short content that will fail validation (< 100 chars)
            mock_generate.return_value = "Short content"
            
            error_response = client.post('/generate', data={
                'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'language': 'en'
            })
            
            # Should return 500 due to content too short
            assert error_response.status_code == 500
            error_data = json.loads(error_response.data)
            assert error_data['success'] is False