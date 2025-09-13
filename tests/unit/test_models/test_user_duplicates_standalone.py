"""
Standalone duplicate user tests - completely isolated from all fixtures.
This module exists to work around CI/CD autouse fixture interference.
"""
import pytest
from unittest.mock import Mock
from bson import ObjectId


class TestUserDuplicatesStandalone:
    """Standalone tests for user duplicate detection - no fixtures used"""

    def test_create_user_duplicate_email_standalone(self):
        """Test user creation with duplicate email - completely standalone"""
        # Import inside test to avoid any module-level interference
        import sys
        import os

        # Add the project root to the path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Import the User class directly
        from app.models.user import User

        # Create a test user that bypasses all global mocking
        class StandaloneTestUser(User):
            def __init__(self):
                # Don't call super().__init__ to avoid BaseModel initialization
                self.collection_name = "users"

            def _ensure_connection(self):
                # Override to prevent any connection attempts
                pass

            def get_collection(self):
                # Return our controlled mock collection
                mock_collection = Mock()
                mock_collection.find_one.return_value = {
                    '_id': ObjectId(),
                    'email': 'test@example.com',
                    'username': 'existing_user'
                }
                return mock_collection

        # Test the duplicate detection
        test_user = StandaloneTestUser()
        result = test_user.create_user('testuser', 'test@example.com', 'password123')

        # Debug output for CI/CD
        print(f"STANDALONE DEBUG - Result: {result}")
        print(f"STANDALONE DEBUG - Result type: {type(result)}")

        # Verify we get the expected duplicate error
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result.get('success') is False, f"Expected success=False, got: {result}"
        assert 'already exists' in result.get('message', ''), f"Expected 'already exists' in message: {result}"

    def test_create_user_duplicate_username_standalone(self):
        """Test user creation with duplicate username - completely standalone"""
        # Import inside test to avoid any module-level interference
        import sys
        import os

        # Add the project root to the path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Import the User class directly
        from app.models.user import User

        # Create a test user that bypasses all global mocking
        class StandaloneTestUser(User):
            def __init__(self):
                # Don't call super().__init__ to avoid BaseModel initialization
                self.collection_name = "users"

            def _ensure_connection(self):
                # Override to prevent any connection attempts
                pass

            def get_collection(self):
                # Return our controlled mock collection for username duplicate
                mock_collection = Mock()
                mock_collection.find_one.return_value = {
                    '_id': ObjectId(),
                    'username': 'testuser',
                    'email': 'existing@example.com'
                }
                return mock_collection

        # Test the duplicate detection
        test_user = StandaloneTestUser()
        result = test_user.create_user('testuser', 'test@example.com', 'password123')

        # Verify we get the expected duplicate error
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result}"
        assert result.get('success') is False, f"Expected success=False, got: {result}"
        assert 'already exists' in result.get('message', ''), f"Expected 'already exists' in message: {result}"