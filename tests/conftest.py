import logging
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set test environment variables before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only'
os.environ['MONGODB_URI'] = 'mongodb://localhost:27017/test_db'
os.environ['MONGODB_DB_NAME'] = 'test_youtube_blog_db'
os.environ['OPENAI_API_KEY'] = 'test-openai-key'
os.environ['SUPADATA_API_KEY'] = 'test-supadata-key'
os.environ['LOKI_URL'] = 'http://test-loki:3100'
os.environ['GA_MEASUREMENT_ID'] = 'G-TEST123'

# Configure logging
logging.basicConfig(level=logging.CRITICAL)

@pytest.fixture
def app():
    """Create and configure a test Flask application"""
    from app import create_app
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Initialize temp storage
    app.temp_storage = {}
    app.start_time = 1234567890
    
    yield app
@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands"""
    return app.test_cli_runner()

@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client"""
    with patch('app.models.user.MongoClient') as mock:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_client.server_info.return_value = {'version': '4.4.0'}
        mock_client.admin.command.return_value = {'ok': 1}
        mock.return_value = mock_client
        yield mock_client

@pytest.fixture
def mock_user():
    """Mock user data"""
    return {
        '_id': '507f1f77bcf86cd799439011',
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': 'hashed_password',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'is_active': True
    }

@pytest.fixture
def mock_blog_post():
    """Mock blog post data"""
    return {
        '_id': '507f1f77bcf86cd799439012',
        'user_id': '507f1f77bcf86cd799439011',
        'youtube_url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'title': 'Test Blog Post',
        'content': '# Test Blog Post\n\nThis is test content.',
        'video_id': 'dQw4w9WgXcQ',
        'word_count': 10,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }