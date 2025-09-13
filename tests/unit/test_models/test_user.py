import datetime
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId
from werkzeug.security import generate_password_hash


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connection and manager"""
    with patch('app.models.user.mongo_manager') as mock_manager:
        mock_manager.is_connected.return_value = True
        mock_manager.get_collection.return_value = Mock()
        yield mock_manager




class TestUser:
    """Test cases for User model"""

    def test_create_user_success(self, mock_mongodb_globally):
        """Test successful user creation"""
        from app.models.user import User

        user_id = ObjectId()
        mock_collection = mock_mongodb_globally['collection']
        
        # Reset and configure mock for successful user creation
        mock_collection.reset_mock()
        mock_collection.find_one.side_effect = [
            None,  # First call: no existing user
            {      # Second call: return created user
                '_id': user_id,
                'username': 'testuser',
                'email': 'test@example.com',
                'password_hash': 'hashed_password',
                'created_at': datetime.datetime.now(datetime.UTC),
                'updated_at': datetime.datetime.now(datetime.UTC),
                'is_active': True
            }
        ]

        mock_insert_result = Mock()
        mock_insert_result.inserted_id = user_id
        mock_collection.insert_one.return_value = mock_insert_result

        user = User()
        result = user.create_user('testuser', 'test@example.com', 'password123')

        assert result['success'] is True
        assert 'user' in result
        assert 'username' in result['user']
        assert 'email' in result['user']
        assert 'password_hash' not in result['user']

    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email - final approach"""
        from app.models.user import User

        # Since all our mocking approaches are being bypassed in CI/CD,
        # let's test the actual logic by calling the method with controlled conditions

        # Create a test-specific User class that we can control completely
        class TestUser(User):
            def get_collection(self):
                # Return a mock collection that simulates duplicate user
                mock_collection = Mock()
                mock_collection.find_one.return_value = {
                    '_id': ObjectId(),
                    'email': 'test@example.com',
                    'username': 'existing_user'
                }
                return mock_collection

        # Test the duplicate detection logic
        test_user = TestUser()
        result = test_user.create_user('testuser', 'test@example.com', 'password123')

        # Debug output for CI/CD troubleshooting
        print(f"CI/CD FINAL DEBUG - Result: {result}")
        print(f"CI/CD FINAL DEBUG - Result type: {type(result)}")

        # The assertions that should work regardless of environment
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        assert 'success' in result, f"Result missing 'success' key: {result}"
        assert result['success'] is False, f"Expected success=False but got {result}"
        assert 'message' in result, f"Result missing 'message' key: {result}"
        assert 'already exists' in result['message'], f"Expected 'already exists' in message: {result['message']}"

    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username - final approach"""
        from app.models.user import User

        # Create a test-specific User class that we can control completely
        class TestUser(User):
            def get_collection(self):
                # Return a mock collection that simulates duplicate username
                mock_collection = Mock()
                mock_collection.find_one.return_value = {
                    '_id': ObjectId(),
                    'username': 'testuser',
                    'email': 'existing@example.com'
                }
                return mock_collection

        # Test the duplicate detection logic
        test_user = TestUser()
        result = test_user.create_user('testuser', 'test@example.com', 'password123')

        # The assertions that should work regardless of environment
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        assert 'success' in result, f"Result missing 'success' key: {result}"
        assert result['success'] is False, f"Expected success=False but got {result}"
        assert 'message' in result, f"Result missing 'message' key: {result}"
        assert 'already exists' in result['message'], f"Expected 'already exists' in message: {result['message']}"

    def test_create_user_insert_failure(self, mock_mongodb_globally):
        """Test user creation when insert fails"""
        from app.models.user import User

        # Reset and configure mock for insert failure
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.reset_mock()
        mock_collection.find_one.return_value = None
        mock_insert_result = Mock()
        mock_insert_result.inserted_id = None
        mock_collection.insert_one.return_value = mock_insert_result

        user = User()
        result = user.create_user('testuser', 'test@example.com', 'password123')

        assert result['success'] is False
        assert result['message'] == "Failed to create user"

    def test_create_user_database_error(self, mock_mongodb_globally):
        """Test user creation with database error"""
        from app.models.user import User

        # Configure mock for database error
        mock_mongodb_globally['manager'].get_collection.side_effect = Exception("Database connection failed")

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
                'created_at': datetime.datetime.now(datetime.UTC),
                'updated_at': datetime.datetime.now(datetime.UTC),
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

        with patch.object(User, 'get_collection'):
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
