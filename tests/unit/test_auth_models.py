import pytest
from unittest.mock import Mock, patch, MagicMock
from bson import ObjectId
import datetime
from auth.models import MongoDBConnectionManager, BaseModel, User, BlogPost, mongo_manager

class TestMongoDBConnectionManager:
    """Test MongoDB connection manager"""
    
    def test_singleton_pattern(self):
        """Test that MongoDBConnectionManager follows singleton pattern"""
        manager1 = MongoDBConnectionManager()
        manager2 = MongoDBConnectionManager()
        assert manager1 is manager2
    
# Update the test_connect_success method in TestMongoDBConnectionManager
    @patch('auth.models.MongoClient')
    @patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017', 'MONGODB_DB_NAME': 'test_db'})
    def test_connect_success(self, mock_mongo_client):
        """Test successful MongoDB connection"""
        # Create a MagicMock instead of Mock to handle magic methods
        mock_client = MagicMock()
        mock_client.admin.command.return_value = None
        mock_db = Mock()
        
        # Configure the client to return the database when accessed like client[db_name]
        mock_client.__getitem__ = Mock(return_value=mock_db)
        mock_mongo_client.return_value = mock_client
        
        manager = MongoDBConnectionManager()
        manager._connect()  # Changed from manager.connect() to manager._connect()
        
        # Verify the connection was established
        mock_mongo_client.assert_called_once_with(
            'mongodb://test:27017',
            maxPoolSize=50,
            minPoolSize=5,
            maxIdleTimeMS=30000,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            retryWrites=True,
            w='majority'
        )
        mock_client.admin.command.assert_called_once_with('ping')
        mock_client.__getitem__.assert_called_once_with('test_db')
        
        # Use pytest assertions instead of unittest assertions
        assert manager.is_connected() is True
        assert manager.db == mock_db


    @patch('auth.models.MongoClient')
    @patch.dict('os.environ', {}, clear=True)
    def test_connect_no_uri(self, mock_mongo_client):
        """Test connection failure when no URI provided"""
        manager = MongoDBConnectionManager()
        
        with pytest.raises(ValueError, match="MONGODB_URI environment variable not set"):
            manager._connect()
    
    @patch('auth.models.MongoClient')
    @patch.dict('os.environ', {'MONGODB_URI': 'mongodb://test:27017'})
    def test_connect_failure(self, mock_mongo_client):
        """Test connection failure"""
        mock_mongo_client.side_effect = Exception("Connection failed")
        
        manager = MongoDBConnectionManager()
        
        with pytest.raises(Exception):
            manager._connect()
    
    def test_close_connection(self):
        """Test closing MongoDB connection"""
        manager = MongoDBConnectionManager()
        mock_client = Mock()
        manager.client = mock_client
        manager.db = Mock()
        
        manager.close_connection()
        
        mock_client.close.assert_called_once()  # Now mock_client has close method
        assert manager.client is None
        assert manager.db is None

    
    def test_is_connected_true(self):
        """Test is_connected returns True when connected"""
        manager = MongoDBConnectionManager()
        manager.client = Mock()
        manager.client.admin.command.return_value = None
        
        assert manager.is_connected() is True
    
    def test_is_connected_false(self):
        """Test is_connected returns False when not connected"""
        manager = MongoDBConnectionManager()
        manager.client = None
        
        assert manager.is_connected() is False
    
    def test_get_collection(self):
        """Test getting collection"""
        manager = MongoDBConnectionManager()
        mock_db = Mock()
        mock_collection = Mock()
        
        # Mock the database to support db[collection_name] syntax
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        manager.db = mock_db
        manager.client = Mock()  # Ensure client exists
        
        collection = manager.get_collection('test_collection')
        
        mock_db.__getitem__.assert_called_with('test_collection')
        assert collection == mock_collection


class TestBaseModel:
    """Test BaseModel class"""
    
    @patch('auth.models.mongo_manager')
    def test_init(self, mock_manager):
        """Test BaseModel initialization"""
        mock_manager.is_connected.return_value = True
        
        model = BaseModel('test_collection')
        
        assert model.collection_name == 'test_collection'
    
    @patch('auth.models.mongo_manager')
    def test_ensure_connection_when_connected(self, mock_manager):
        """Test _ensure_connection when already connected"""
        mock_manager.is_connected.return_value = True
        
        model = BaseModel('test_collection')
        model._ensure_connection()
        
        mock_manager.is_connected.assert_called()
        mock_manager.reconnect.assert_not_called()
    
    @patch('auth.models.mongo_manager')
    def test_ensure_connection_when_not_connected(self, mock_manager):
        """Test _ensure_connection when not connected"""
        # Configure the manager to be disconnected initially
        mock_manager.is_connected.return_value = False
        
        model = BaseModel('test_collection')
        
        # Reset mock to clear any calls from __init__
        mock_manager.reset_mock()
        mock_manager.is_connected.return_value = False
        
        # Call the method under test
        model._ensure_connection()
        
        # Verify the expected calls
        mock_manager.is_connected.assert_called()
        mock_manager.reconnect.assert_called_once()


    
    @patch('auth.models.mongo_manager')
    def test_get_collection(self, mock_manager):
        """Test getting collection from BaseModel"""
        mock_collection = Mock()
        mock_manager.is_connected.return_value = True
        mock_manager.get_collection.return_value = mock_collection
        
        model = BaseModel('test_collection')
        collection = model.get_collection()
        
        mock_manager.get_collection.assert_called_with('test_collection')
        assert collection == mock_collection

class TestUser:
    """Test User model"""
    
    @patch('auth.models.mongo_manager')
    def test_create_user_success(self, mock_manager, sample_user_data):
        """Test successful user creation"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        # Mock no existing user
        mock_collection.find_one.side_effect = [None, sample_user_data]
        
        # Mock successful insertion
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        
        user_model = User()
        result = user_model.create_user('testuser', 'test@example.com', 'password123')
        
        assert result['success'] is True
        assert 'user' in result
        mock_collection.insert_one.assert_called_once()
    
    @patch('auth.models.mongo_manager')
    def test_create_user_already_exists(self, mock_manager, sample_user_data):
        """Test user creation when user already exists"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        # Mock existing user
        mock_collection.find_one.return_value = sample_user_data
        
        user_model = User()
        result = user_model.create_user('testuser', 'test@example.com', 'password123')
        
        assert result['success'] is False
        assert 'already exists' in result['message']
    
    @patch('auth.models.mongo_manager')
    def test_authenticate_user_success(self, mock_manager, sample_user_data):
        """Test successful user authentication"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        # Mock user with hashed password
        user_with_password = sample_user_data.copy()
        user_with_password['password_hash'] = 'hashed_password'
        mock_collection.find_one.return_value = user_with_password
        
        with patch('auth.models.check_password_hash', return_value=True):
            user_model = User()
            result = user_model.authenticate_user('test@example.com', 'password123')
        
        assert result is not None
        assert result['email'] == 'test@example.com'
        assert 'password_hash' not in result
    
    @patch('auth.models.mongo_manager')
    def test_authenticate_user_invalid_password(self, mock_manager, sample_user_data):
        """Test user authentication with invalid password"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        user_with_password = sample_user_data.copy()
        user_with_password['password_hash'] = 'hashed_password'
        mock_collection.find_one.return_value = user_with_password
        
        with patch('auth.models.check_password_hash', return_value=False):
            user_model = User()
            result = user_model.authenticate_user('test@example.com', 'wrongpassword')
        
        assert result is None
    
    @patch('auth.models.mongo_manager')
    def test_get_user_by_id_success(self, mock_manager, sample_user_data):
        """Test getting user by ID successfully"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_collection.find_one.return_value = sample_user_data
        
        user_model = User()
        result = user_model.get_user_by_id(sample_user_data['_id'])
        
        assert result is not None
        assert result['_id'] == sample_user_data['_id']
    
    @patch('auth.models.mongo_manager')
    def test_get_user_by_id_invalid_id(self, mock_manager):
        """Test getting user by invalid ID"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        user_model = User()
        result = user_model.get_user_by_id('invalid_id')
        
        assert result is None
    
    @patch('auth.models.mongo_manager')
    def test_update_user_success(self, mock_manager, sample_user_data):
        """Test successful user update"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        
        user_model = User()
        result = user_model.update_user(sample_user_data['_id'], {'username': 'newusername'})
        
        assert result is True
        mock_collection.update_one.assert_called_once()

class TestBlogPost:
    """Test BlogPost model"""
    
    @patch('auth.models.mongo_manager')
    def test_create_post_success(self, mock_manager, sample_blog_post):
        """Test successful blog post creation"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result
        
        blog_model = BlogPost()
        result = blog_model.create_post(
            sample_blog_post['user_id'],
            sample_blog_post['youtube_url'],
            sample_blog_post['title'],
            sample_blog_post['content'],
            sample_blog_post['video_id']
        )
        
        assert result is not None
        assert result['title'] == sample_blog_post['title']
        mock_collection.insert_one.assert_called_once()
    
    @patch('auth.models.mongo_manager')
    def test_get_user_posts(self, mock_manager, sample_blog_post):
        """Test getting user posts"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.skip.return_value = [sample_blog_post]
        mock_collection.find.return_value = mock_cursor
        
        blog_model = BlogPost()
        result = blog_model.get_user_posts(sample_blog_post['user_id'])
        
        assert len(result) == 1
        assert result[0]['title'] == sample_blog_post['title']
    
    @patch('auth.models.mongo_manager')
    def test_delete_post_success(self, mock_manager, sample_blog_post):
        """Test successful post deletion"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        
        blog_model = BlogPost()
        result = blog_model.delete_post(sample_blog_post['_id'], sample_blog_post['user_id'])
        
        assert result is True
        mock_collection.delete_one.assert_called_once()
    
    @patch('auth.models.mongo_manager')
    def test_get_posts_count(self, mock_manager, sample_blog_post):
        """Test getting posts count"""
        mock_collection = Mock()
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.is_connected.return_value = True
        
        mock_collection.count_documents.return_value = 5
        
        blog_model = BlogPost()
        result = blog_model.get_posts_count(sample_blog_post['user_id'])
        
        assert result == 5
        mock_collection.count_documents.assert_called_once()
