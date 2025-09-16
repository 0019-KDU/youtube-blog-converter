from datetime import datetime
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash


class TestMongoDBConnectionManager:
    
    @patch('app.models.user.MongoClient')
    def test_singleton_pattern(self, mock_client):
        """Test that MongoDBConnectionManager follows singleton pattern"""
        from app.models.user import MongoDBConnectionManager
        
        manager1 = MongoDBConnectionManager()
        manager2 = MongoDBConnectionManager()
        
        assert manager1 is manager2
    
    @patch('app.models.user.MongoClient')
    def test_get_connection_creates_new(self, mock_client):
        """Test connection creation when none exists"""
        from app.models.user import MongoDBConnectionManager
        
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.server_info.return_value = {'version': '4.4.0'}
        
        manager = MongoDBConnectionManager()
        manager.client = None  # Force new connection
        
        client, db = manager.get_connection()
        
        assert client is not None
        assert db is not None
        mock_client.assert_called()
    
    @patch('app.models.user.MongoClient')
    def test_close_connection(self, mock_client):
        """Test connection closing"""
        from app.models.user import MongoDBConnectionManager
        
        mock_client_instance = MagicMock()
        
        manager = MongoDBConnectionManager()
        manager.client = mock_client_instance
        manager.db = MagicMock()
        
        manager.close_connection()
        
        mock_client_instance.close.assert_called_once()
        assert manager.client is None
        assert manager.db is None
    
    @patch('app.models.user.MongoClient')
    def test_is_connected(self, mock_client):
        """Test connection status check"""
        from app.models.user import MongoDBConnectionManager
        
        mock_client_instance = MagicMock()
        
        manager = MongoDBConnectionManager()
        manager.client = mock_client_instance
        
        # Test connected
        mock_client_instance.admin.command.return_value = {'ok': 1}
        assert manager.is_connected() is True
        
        # Test disconnected
        mock_client_instance.admin.command.side_effect = Exception()
        assert manager.is_connected() is False

class TestUserModel:
    
    @patch('app.models.user.mongo_manager')
    def test_create_user_success(self, mock_manager):
        """Test successful user creation"""
        from app.models.user import User
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = None  # No existing user
        mock_collection.insert_one.return_value.inserted_id = ObjectId('507f1f77bcf86cd799439011')
        mock_collection.find_one.side_effect = [None, {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': True
        }]
        
        user = User()
        result = user.create_user('testuser', 'test@example.com', 'password123')
        
        assert result['success'] is True
        assert result['user']['username'] == 'testuser'
        assert result['user']['email'] == 'test@example.com'
        assert 'password_hash' not in result['user']
    
    @patch('app.models.user.mongo_manager')
    def test_create_user_already_exists(self, mock_manager):
        """Test user creation when user already exists"""
        from app.models.user import User
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = {'email': 'test@example.com'}
        
        user = User()
        result = user.create_user('testuser', 'test@example.com', 'password123')
        
        assert result['success'] is False
        assert 'already exists' in result['message']
    
    @patch('app.models.user.mongo_manager')
    @patch('app.models.user.check_password_hash')
    def test_authenticate_user_success(self, mock_check_password, mock_manager):
        """Test successful user authentication"""
        from app.models.user import User
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_check_password.return_value = True
        
        user_data = {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed_password'
        }
        mock_collection.find_one.return_value = user_data
        
        user = User()
        result = user.authenticate_user('test@example.com', 'password123')
        
        assert result is not None
        assert result['username'] == 'testuser'
        assert 'password_hash' not in result
    
    @patch('app.models.user.mongo_manager')
    def test_get_user_by_id(self, mock_manager):
        """Test getting user by ID"""
        from app.models.user import User
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        
        user_data = {
            '_id': ObjectId('507f1f77bcf86cd799439011'),
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed'
        }
        mock_collection.find_one.return_value = user_data
        
        user = User()
        result = user.get_user_by_id('507f1f77bcf86cd799439011')
        
        assert result['username'] == 'testuser'
        assert 'password_hash' not in result

class TestBlogPostModel:
    
    @patch('app.models.user.mongo_manager')
    def test_create_post(self, mock_manager):
        """Test blog post creation"""
        from app.models.user import BlogPost
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_collection.insert_one.return_value.inserted_id = ObjectId('507f1f77bcf86cd799439012')
        
        blog = BlogPost()
        result = blog.create_post(
            '507f1f77bcf86cd799439011',
            'https://youtube.com/watch?v=test',
            'Test Title',
            'Test content with multiple words',  # This has 5 words
            'test_video_id'
        )
        
        assert result is not None
        assert result['title'] == 'Test Title'
        assert result['word_count'] == 5  # Fixed from 4 to 5
    
    @patch('app.models.user.mongo_manager')
    def test_get_user_posts(self, mock_manager):
        """Test getting user posts"""
        from app.models.user import BlogPost
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        
        posts_data = [
            {
                '_id': ObjectId('507f1f77bcf86cd799439012'),
                'user_id': ObjectId('507f1f77bcf86cd799439011'),
                'title': 'Post 1',
                'content': 'Content 1'
            },
            {
                '_id': ObjectId('507f1f77bcf86cd799439013'),
                'user_id': ObjectId('507f1f77bcf86cd799439011'),
                'title': 'Post 2',
                'content': 'Content 2'
            }
        ]
        
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.skip.return_value = posts_data
        mock_collection.find.return_value = mock_cursor
        
        blog = BlogPost()
        result = blog.get_user_posts('507f1f77bcf86cd799439011')
        
        assert len(result) == 2
        assert all(isinstance(post['_id'], str) for post in result)
    
    @patch('app.models.user.mongo_manager')
    def test_delete_post(self, mock_manager):
        """Test post deletion"""
        from app.models.user import BlogPost
        
        mock_collection = MagicMock()
        mock_manager.get_collection.return_value = mock_collection
        mock_collection.delete_one.return_value.deleted_count = 1
        
        blog = BlogPost()
        result = blog.delete_post('507f1f77bcf86cd799439012', '507f1f77bcf86cd799439011')
        
        assert result is True