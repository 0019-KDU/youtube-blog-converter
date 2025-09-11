import datetime
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

# Ensure app directory is in path before any imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up environment variables BEFORE importing any app modules
os.environ.update({
    'OPENAI_API_KEY': 'test-openai-key-12345',
    'SUPADATA_API_KEY': 'test-supadata-key-12345',
    'MONGODB_URI': 'mongodb://test:test@localhost:27017/test_db',
    'MONGODB_DB_NAME': 'test_youtube_blog_db',
    'JWT_SECRET_KEY': 'test-jwt-secret-key-for-testing-only-12345',
    'FLASK_SECRET_KEY': 'test-flask-secret-key-for-testing-only-12345',
    'SECRET_KEY': 'test-secret-key-12345',
    'FLASK_ENV': 'testing',
    'LOG_LEVEL': 'ERROR',
    'LOKI_URL': 'http://test-loki:3100',
    'GA_MEASUREMENT_ID': 'GA-TEST-123456',
    'JWT_ACCESS_TOKEN_EXPIRES': '86400',
})

# Import ObjectId after setting environment
try:
    from bson import ObjectId
except ImportError:
    class ObjectId:
        def __init__(self, oid=None):
            self._id = oid or 'test_object_id_12345'
        
        def __str__(self):
            return str(self._id)


@pytest.fixture(autouse=True)
def mock_environment_variables(monkeypatch):
    """Mock environment variables for all tests"""
    env_vars = {
        "OPENAI_API_KEY": "test_openai_key_12345",
        "SUPADATA_API_KEY": "test_supadata_key_12345", 
        "MONGODB_URI": "mongodb://test:test@localhost:27017/test_db",
        "MONGODB_DB_NAME": "test_blog_db",
        "JWT_SECRET_KEY": "test_jwt_secret_key_12345",
        "FLASK_SECRET_KEY": "test_flask_secret_key_12345",
        "SECRET_KEY": "test_secret_key_12345",
        "FLASK_ENV": "testing",
        "LOG_LEVEL": "ERROR",
        "JWT_ACCESS_TOKEN_EXPIRES": "86400",
        "LOKI_URL": "http://test-loki:3100",
        "GA_MEASUREMENT_ID": "GA-TEST-123456",
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture(autouse=True)
def mock_logging():
    """Mock logging to reduce test output noise"""
    with patch('logging.getLogger') as mock_logger:
        mock_instance = Mock()
        mock_instance.info = Mock()
        mock_instance.warning = Mock()
        mock_instance.error = Mock()
        mock_instance.debug = Mock()
        mock_logger.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_mongodb_globally():
    """Mock MongoDB connections globally for all tests"""
    with patch('app.models.user.MongoClient') as mock_client, \
         patch('app.models.user.mongo_manager') as mock_manager, \
         patch('pymongo.MongoClient') as mock_pymongo_client:
        
        # Configure mock collection
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = Mock(inserted_id=ObjectId())
        mock_collection.update_one.return_value = Mock(modified_count=1)
        mock_collection.delete_one.return_value = Mock(deleted_count=1)
        mock_collection.find.return_value = Mock()
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = []
        mock_collection.count_documents.return_value = 0
        
        # Configure mock database
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Configure mock client
        mock_client_instance = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_client_instance.server_info.return_value = {'version': '4.4.0'}
        mock_client_instance.admin.command.return_value = {'ok': 1}
        mock_client.return_value = mock_client_instance
        mock_pymongo_client.return_value = mock_client_instance
        
        # Configure mock manager
        mock_manager.is_connected.return_value = True
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.get_database.return_value = mock_db
        mock_manager.client = mock_client_instance
        mock_manager.db = mock_db
        
        yield {
            'client': mock_client,
            'manager': mock_manager,
            'db': mock_db,
            'collection': mock_collection
        }


@pytest.fixture
def app():
    """Create Flask app for testing using the app factory"""
    # Set test environment variables before creating app
    import os
    os.environ.update({
        'TESTING': 'True',
        'SECRET_KEY': 'test-secret-key-12345',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-12345',
        'MONGODB_URI': 'mongodb://test:test@localhost:27017/test_db',
        'MONGODB_DB_NAME': 'test_blog_db',
        'OPENAI_API_KEY': 'test-openai-key-12345',
        'SUPADATA_API_KEY': 'test-supadata-key-12345',
        'JWT_ACCESS_TOKEN_EXPIRES': '86400',
        'FLASK_ENV': 'testing',
    })
    
    # Use the app factory to create the app with all blueprints registered
    from app import create_app
    app = create_app()
    
    # Override config for testing
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SESSION_COOKIE_SECURE': False,
    })
    
    yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provide app context for tests"""
    with app.app_context():
        yield app


@pytest.fixture
def request_context(app):
    """Provide request context for tests"""
    with app.test_request_context():
        yield


@pytest.fixture
def flask_contexts(app):
    """Combined app and request context"""
    with app.app_context():
        with app.test_request_context():
            yield app


@pytest.fixture
def mock_requests_session():
    """Mock requests session for API calls"""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'content': 'This is a comprehensive test transcript about artificial intelligence and machine learning technologies.',
        'video_id': 'test123',
        'title': 'Technology Innovation Video'
    }
    mock_response.raise_for_status.return_value = None
    
    mock_session.get.return_value = mock_response
    mock_session.post.return_value = mock_response
    mock_session.close.return_value = None
    mock_session.headers = {}
    
    yield mock_session


@pytest.fixture
def mock_user_data():
    """Sample user data for testing"""
    return {
        '_id': ObjectId(),
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': 'hashed_password_12345',
        'created_at': datetime.datetime.utcnow(),
        'updated_at': datetime.datetime.utcnow(),
        'is_active': True
    }


@pytest.fixture
def authenticated_user(client, mock_user_data):
    """Create an authenticated user session"""
    with client.session_transaction() as sess:
        sess['user_id'] = str(mock_user_data['_id'])
        sess['access_token'] = 'test-jwt-token-12345'
    return mock_user_data


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


# Test utilities
def create_test_user(user_model, **kwargs):
    """Helper to create test user"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com', 
        'password': 'testpassword123',
        **kwargs
    }
    return user_model.create_user(**user_data)


def assert_successful_response(response):
    """Helper to assert successful API response"""
    assert response.status_code in [200, 201]
    if response.content_type and 'application/json' in response.content_type:
        try:
            data = response.get_json()
            assert data.get('success', True) is True
        except Exception:
            pass


def assert_error_response(response, expected_status=400):
    """Helper to assert error API response"""
    assert response.status_code == expected_status
    if response.content_type and 'application/json' in response.content_type:
        try:
            data = response.get_json()
            assert data.get('success', False) is False
            assert 'message' in data
        except Exception:
            pass


# Sample data fixtures
@pytest.fixture
def sample_youtube_urls():
    """Provide various YouTube URL formats for testing"""
    return [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtu.be/dQw4w9WgXcQ',
        'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'https://www.youtube.com/shorts/dQw4w9WgXcQ',
        'https://m.youtube.com/watch?v=dQw4w9WgXcQ',
    ]


@pytest.fixture
def sample_invalid_urls():
    """Provide invalid URLs for testing"""
    return [
        '',
        'not-a-url',
        'https://example.com',
        'https://vimeo.com/123456',
        'ftp://youtube.com/watch?v=test',
        'https://youtube.com',
        'https://youtube.com/watch',
    ]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "crewai: mark test to run only if crewai is available")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")
