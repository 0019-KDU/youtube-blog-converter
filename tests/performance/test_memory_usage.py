import gc
import os
import sys
from unittest.mock import Mock, patch

import psutil
import pytest


class TestMemoryUsage:
    """Performance tests for memory usage"""
    
    def test_blog_generation_memory_usage(self, client, authenticated_user):
        """Test memory usage during blog generation"""
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate multiple blogs to test memory
        for i in range(5):
            with patch('app.services.blog_service.generate_blog_from_youtube') as mock_generate, \
                 patch('app.models.user.BlogPost') as mock_blog_class, \
                 patch('app.utils.security.store_large_data') as mock_store:
                
                # Generate large content to test memory handling
                large_content = '# Large Blog Post\n\n' + 'Content paragraph. ' * 1000
                mock_generate.return_value = large_content
                
                mock_blog = Mock()
                mock_blog.create_post.return_value = {
                    '_id': f'post_{i}',
                    'title': f'Large Blog Post {i}',
                    'content': large_content,
                    'user_id': str(authenticated_user['_id'])
                }
                mock_blog_class.return_value = mock_blog
                
                mock_store.return_value = f'large_storage_key_{i}'
                
                response = client.post('/generate', data={
                    'youtube_url': f'https://www.youtube.com/watch?v=large{i}',
                    'language': 'en'
                })
                
                assert response.status_code == 200
                
                # Force garbage collection
                gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Initial memory: {initial_memory:.2f} MB")
        print(f"Final memory: {final_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")
        
        # Memory increase should be reasonable (under 100MB for test)
        assert memory_increase < 100
    
    def test_pdf_generation_memory_usage(self, client, authenticated_user):
        """Test memory usage during PDF generation"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Generate PDFs with large content
        large_blog_data = {
            'blog_content': '# Large Blog\n\n' + '## Section\n\nContent paragraph. ' * 500,
            'title': 'Large Blog for PDF',
            'youtube_url': 'https://www.youtube.com/watch?v=pdftest'
        }
        
        for i in range(3):
            with patch('app.utils.security.retrieve_large_data') as mock_retrieve, \
                 patch('app.crew.tools.PDFGeneratorTool') as mock_pdf_class:
                
                mock_retrieve.return_value = large_blog_data
                
                mock_pdf = Mock()
                # Simulate large PDF content
                mock_pdf.generate_pdf_bytes.return_value = b'%PDF-1.4\n' + b'content' * 10000
                mock_pdf_class.return_value = mock_pdf
                
                with client.session_transaction() as sess:
                    sess['blog_storage_key'] = f'pdf_test_key_{i}'
                
                response = client.get('/download')
                assert response.status_code == 200
                
                # Force cleanup
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"PDF generation memory increase: {memory_increase:.2f} MB")
        
        # PDF generation should not cause excessive memory usage
        assert memory_increase < 50
    
    def test_session_storage_memory_usage(self, client):
        """Test memory usage of session storage system"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Store many large items in session storage
        with patch('flask.current_app') as mock_app:
            mock_app.temp_storage = {}
            
            from app.utils.security import store_large_data

            # Store many large items
            for i in range(10):
                large_data = {
                    'content': 'Large content item. ' * 1000,
                    'metadata': {'item': i, 'type': 'test'},
                    'additional_data': list(range(1000))
                }
                
                store_large_data(f'test_key_{i}', large_data, f'user_{i}')
            
            # Check storage size
            storage_size = len(mock_app.temp_storage)
            assert storage_size == 10
            
            # Test cleanup
            # Mock old timestamps to trigger cleanup
            import time

            from app.utils.security import cleanup_old_storage
            old_timestamp = time.time() - 7200  # 2 hours ago
            for key in mock_app.temp_storage:
                mock_app.temp_storage[key]['timestamp'] = old_timestamp
            
            cleanup_old_storage()
            
            # Storage should be cleaned
            assert len(mock_app.temp_storage) == 0
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"Session storage memory increase: {memory_increase:.2f} MB")
        assert memory_increase < 20
    
    def test_database_connection_memory_usage(self):
        """Test memory usage of database connections"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Test multiple database operations
        from app.models.user import BlogPost, User
        
        with patch('app.models.user.mongo_manager') as mock_manager:
            mock_manager.get_collection.return_value = Mock()
            
            # Create multiple model instances
            users = [User() for _ in range(10)]
            blog_posts = [BlogPost() for _ in range(10)]
            
            # Perform operations
            for i, (user, blog_post) in enumerate(zip(users, blog_posts)):
                # Mock operations that would normally hit database
                with patch.object(user, 'get_collection'), \
                     patch.object(blog_post, 'get_collection'):
                    
                    # These would normally be database operations
                    user.get_user_by_id(f'user_{i}')
                    blog_post.get_user_posts(f'user_{i}')
            
            # Clean up references
            del users
            del blog_posts
            gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"Database operations memory increase: {memory_increase:.2f} MB")
        assert memory_increase < 10