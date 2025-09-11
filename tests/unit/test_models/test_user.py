import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connection and manager"""
    with patch('app.models.user.mongo_manager') as mock_manager:
        mock_manager.is_connected.return_value = True
        mock_manager.get_collection.return_value = Mock()
        yield mock_manager


class TestUser:
    """Test cases for User model"""
    
    def test_create_user_success(self):
        """Test successful user creation"""
        from app.models.user import User
        
        user_id = ObjectId()
        with patch.object(User, 'get_collection') as mock_get_collection:
            # Mock collection methods
            mock_coll = Mock()
            mock_coll.find_one.side_effect = [
                None,  # First call: no existing user
                {      # Second call: return created user
                    '_id': user_id,
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password_hash': 'hashed_password',
                    'created_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow(),
                    'is_active': True
                }
            ]
            
            mock_insert_result = Mock()
            mock_insert_result.inserted_id = user_id
            mock_coll.insert_one.return_value = mock_insert_result
            
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.create_user('testuser', 'test@example.com', 'password123')
            
            assert result['success'] is True
            assert 'user' in result
            assert result['user']['username'] == 'testuser'
            assert result['user']['email'] == 'test@example.com'
            assert 'password_hash' not in result['user']
            assert result['message'] == "User created successfully"
    
    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': ObjectId(),
                'email': 'test@example.com'
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.create_user('testuser', 'test@example.com', 'password123')
            
            assert result['success'] is False
            assert 'already exists' in result['message']
    
    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': ObjectId(),
                'username': 'testuser'
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.create_user('testuser', 'test@example.com', 'password123')
            
            assert result['success'] is False
            assert 'already exists' in result['message']
    
    def test_create_user_insert_failure(self):
        """Test user creation when insert fails"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = None  # No existing user
            mock_insert_result = Mock()
            mock_insert_result.inserted_id = None  # Insert failed
            mock_coll.insert_one.return_value = mock_insert_result
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.create_user('testuser', 'test@example.com', 'password123')
            
            assert result['success'] is False
            assert result['message'] == "Failed to create user"
    
    def test_create_user_database_error(self):
        """Test user creation with database error"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_get_collection.side_effect = Exception("Database connection failed")
            
            user = User()
            result = user.create_user('testuser', 'test@example.com', 'password123')
            
            assert result['success'] is False
            assert 'Database error' in result['message']
    
    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        from app.models.user import User
        
        user_id = ObjectId()
        hashed_password = generate_password_hash('password123')
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': user_id,
                'username': 'testuser',
                'email': 'test@example.com',
                'password_hash': hashed_password,
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'is_active': True
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.authenticate_user('test@example.com', 'password123')
            
            assert result is not None
            assert result['username'] == 'testuser'
            assert result['email'] == 'test@example.com'
            assert '_id' in result
            assert 'password_hash' not in result
    
    def test_authenticate_user_invalid_password(self):
        """Test authentication with invalid password"""
        from app.models.user import User
        
        hashed_password = generate_password_hash('correct_password')
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': ObjectId(),
                'email': 'test@example.com',
                'password_hash': hashed_password,
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.authenticate_user('test@example.com', 'wrong_password')
            
            assert result is None
    
    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = None
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.authenticate_user('nonexistent@example.com', 'password123')
            
            assert result is None
    
    def test_authenticate_user_database_error(self):
        """Test authentication with database error"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_get_collection.side_effect = Exception("Database error")
            
            user = User()
            result = user.authenticate_user('test@example.com', 'password123')
            
            assert result is None
    
    def test_get_user_by_id_success(self):
        """Test getting user by ID"""
        from app.models.user import User
        
        user_id = ObjectId()
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': user_id,
                'username': 'testuser',
                'email': 'test@example.com',
                'password_hash': 'hashed_password',
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.get_user_by_id(str(user_id))
            
            assert result is not None
            assert result['username'] == 'testuser'
            assert result['_id'] == str(user_id)
            assert 'password_hash' not in result
    
    def test_get_user_by_id_objectid(self):
        """Test getting user by ObjectId"""
        from app.models.user import User
        
        user_id = ObjectId()
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = {
                '_id': user_id,
                'username': 'testuser',
                'email': 'test@example.com',
                'password_hash': 'hashed_password',
            }
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.get_user_by_id(user_id)
            
            assert result is not None
            assert result['username'] == 'testuser'
    
    def test_get_user_by_id_not_found(self):
        """Test getting non-existent user by ID"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_coll.find_one.return_value = None
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.get_user_by_id(str(ObjectId()))
            
            assert result is None
    
    def test_get_user_by_id_invalid_objectid(self):
        """Test getting user with invalid ObjectId"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            user = User()
            result = user.get_user_by_id('invalid-objectid')
            
            assert result is None
    
    def test_get_user_by_id_database_error(self):
        """Test getting user with database error"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_get_collection.side_effect = Exception("Database error")
            
            user = User()
            result = user.get_user_by_id(str(ObjectId()))
            
            assert result is None
    
    def test_update_user_success(self):
        """Test successful user update"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_update_result = Mock()
            mock_update_result.modified_count = 1
            mock_coll.update_one.return_value = mock_update_result
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.update_user(str(ObjectId()), {'username': 'newusername'})
            
            assert result is True
            # Verify update_one was called with correct parameters
            mock_coll.update_one.assert_called_once()
            call_args = mock_coll.update_one.call_args
            assert '$set' in call_args[0][1]
            assert 'updated_at' in call_args[0][1]['$set']
    
    def test_update_user_not_found(self):
        """Test updating non-existent user"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_coll = Mock()
            mock_update_result = Mock()
            mock_update_result.modified_count = 0
            mock_coll.update_one.return_value = mock_update_result
            mock_get_collection.return_value = mock_coll
            
            user = User()
            result = user.update_user(str(ObjectId()), {'username': 'newusername'})
            
            assert result is False
    
    def test_update_user_database_error(self):
        """Test updating user with database error"""
        from app.models.user import User
        
        with patch.object(User, 'get_collection') as mock_get_collection:
            mock_get_collection.side_effect = Exception("Database error")
            
            user = User()
            result = user.update_user(str(ObjectId()), {'username': 'newusername'})
            
            assert result is False
