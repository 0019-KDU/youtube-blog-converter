import io
from unittest.mock import Mock, patch

import pytest
from flask import json
from mongomock import ObjectId


class TestPDFGeneration:
    """Integration tests for PDF generation"""
    
    def test_pdf_generation_from_current_blog(self, client, authenticated_user):
        """Test PDF generation from current blog"""
        blog_data = {
            'blog_content': '# Test Blog\n\n## Introduction\n\nThis is a test blog post...',
            'title': 'Test Blog Post',
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        }
        
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'
            sess['blog_storage_key'] = 'test_key'
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
            patch('app.routes.blog.retrieve_large_data') as mock_retrieve, \
            patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_retrieve.return_value = blog_data
            
            # Mock PDF generation
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'%PDF-1.4 mock pdf content'
            mock_pdf_class.return_value = mock_pdf
            
            response = client.get('/download')
            
            assert response.status_code == 200
            assert response.content_type == 'application/pdf'


    
    def test_pdf_generation_from_saved_post(self, client, authenticated_user):
        """Test PDF generation from saved blog post"""
        post_id = str(ObjectId())
        
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
            patch('app.routes.blog.BlogPost') as mock_blog_class, \
            patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            
            # Mock blog post retrieval
            mock_blog = Mock()
            mock_blog.get_post_by_id.return_value = {
                '_id': post_id,
                'title': 'Saved Blog Post',
                'content': '# Saved Blog Post\n\nThis is saved content.',
                'user_id': str(authenticated_user['_id'])
            }
            mock_blog_class.return_value = mock_blog
            
            # Mock PDF generation
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'%PDF-1.4 saved post pdf'
            mock_pdf_class.return_value = mock_pdf
            
            response = client.get(f'/download-post/{post_id}')
            
            assert response.status_code == 200
            assert response.content_type == 'application/pdf'
            
            # Verify correct post was retrieved
            mock_blog.get_post_by_id.assert_called_once_with(
                post_id, authenticated_user['_id']
            )
    
    def test_pdf_generation_with_special_characters(self, client, authenticated_user):
        """Test PDF generation with special characters and formatting"""
        blog_data = {
            'blog_content': '# Test Blog with Special Characters\n\nThis content contains unicode characters that need cleaning.',
            'title': 'Special Characters Test',
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        }
        
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'
            sess['blog_storage_key'] = 'test_key'
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.retrieve_large_data') as mock_retrieve, \
             patch('app.routes.blog.PDFGeneratorTool') as mock_pdf_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_retrieve.return_value = blog_data
            
            # Mock PDF generation
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.return_value = b'%PDF-1.4 special chars pdf'
            mock_pdf_class.return_value = mock_pdf
            
            response = client.get('/download')
            
            assert response.status_code == 200
            assert response.content_type == 'application/pdf'
    
    def test_pdf_generation_error_handling(self, client, authenticated_user):
        """Test PDF generation error handling"""
        blog_data = {
            'blog_content': '# Test Blog\n\nContent',
            'title': 'Test Blog',
            'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        }
        
        with client.session_transaction() as sess:
            sess['user_id'] = str(authenticated_user['_id'])
            sess['access_token'] = 'test_token'
            sess['blog_storage_key'] = 'test_key'
        
        with patch('app.routes.blog.AuthService') as mock_auth_service, \
             patch('app.routes.blog.retrieve_large_data') as mock_retrieve, \
             patch('app.routes.blog.PDFGeneratorTool') as mock_pdf_class:
            
            mock_auth_service.get_current_user.return_value = authenticated_user
            mock_retrieve.return_value = blog_data
            
            # Mock PDF generation failure
            mock_pdf = Mock()
            mock_pdf.generate_pdf_bytes.side_effect = Exception("PDF generation failed")
            mock_pdf_class.return_value = mock_pdf
            
            response = client.get('/download')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'PDF generation failed' in data['message']