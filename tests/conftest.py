import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import json
from bson import ObjectId
import datetime


# Test fixtures for the application
@pytest.fixture
def app():
    """Create a Flask app configured for testing"""
    # Set environment variables first
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key-for-testing-super-secret-12345"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-super-secret-12345"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["SUPADATA_API_KEY"] = "test-supadata-key"
    os.environ["MONGODB_URI"] = "mongodb://localhost:27017/test_db"
    os.environ["MONGODB_DB_NAME"] = "test_youtube_blog_db"

    from app import app

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SESSION_TYPE"] = "filesystem"

    # Create a proper session directory
    session_dir = tempfile.mkdtemp()
    app.config["SESSION_FILE_DIR"] = session_dir

    # Ensure secret key is properly set and long enough
    app.secret_key = "test-secret-key-for-testing-super-secret-12345"

    # Initialize session
    from flask_session import Session

    Session(app)

    with app.app_context():
        yield app

    # Cleanup
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)


@pytest.fixture
def client(app):
    """Create a test client for the Flask app"""
    return app.test_client()


@pytest.fixture
def mock_mongo_connection():
    """Mock MongoDB connection manager"""
    with patch("auth.models.mongo_manager") as mock_manager:
        mock_collection = Mock()
        mock_db = Mock()
        mock_client = Mock()

        # Setup mock methods
        mock_manager.get_collection.return_value = mock_collection
        mock_manager.get_database.return_value = mock_db
        mock_manager.get_connection.return_value = (mock_client, mock_db)
        mock_manager.is_connected.return_value = True
        mock_manager.close_connection.return_value = None

        yield {
            "manager": mock_manager,
            "collection": mock_collection,
            "db": mock_db,
            "client": mock_client,
        }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch("src.tool.openai_client_context") as mock_context:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = (
            "# Generated Blog\n\nThis is a test blog content."
        )
        mock_client.chat.completions.create.return_value = mock_response
        mock_context.return_value.__enter__.return_value = mock_client
        mock_context.return_value.__exit__.return_value = None
        yield mock_client


@pytest.fixture
def mock_requests():
    """Mock requests for API calls"""
    with patch("src.tool.requests.Session") as mock_session_class:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": "Test transcript content"}
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_session.close.return_value = None
        mock_session_class.return_value = mock_session
        yield mock_session


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "_id": str(ObjectId()),
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
    }


@pytest.fixture
def sample_blog_post():
    """Sample blog post for testing"""
    return {
        "_id": str(ObjectId()),
        "user_id": str(ObjectId()),
        "title": "Test Blog Post",
        "content": "# Test Blog\n\nThis is test content.",
        "youtube_url": "https://www.youtube.com/watch?v=test123",
        "video_id": "test123",
        "word_count": 100,
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
    }


@pytest.fixture
def authenticated_user(client, sample_user_data):
    """Create an authenticated user session"""
    with client.session_transaction() as sess:
        sess["access_token"] = "test_token"
        sess["user_id"] = sample_user_data["_id"]
    return sample_user_data


@pytest.fixture
def mock_jwt_functions():
    """Mock JWT functions"""
    with patch("auth.routes.create_access_token") as mock_create, patch(
        "auth.routes.decode_token"
    ) as mock_decode:
        mock_create.return_value = "mock_access_token"
        mock_decode.return_value = {"sub": str(ObjectId())}
        yield {"create_access_token": mock_create, "decode_token": mock_decode}


@pytest.fixture
def sample_transcript():
    """Sample transcript for testing"""
    return """
    Welcome to this technical video about AI tools.
    Today we'll discuss various AI productivity tools.
    First, let's talk about Fabric which is great for AI workflows.
    Then we'll cover some other tools like Claude and ChatGPT.
    Each tool has its strengths and weaknesses.
    """


@pytest.fixture
def sample_blog_content():
    """Sample blog content for testing"""
    return """
# AI Tools Review: A Comprehensive Guide

## Introduction

This article reviews various AI productivity tools and their capabilities.

## Main Tools Discussed

### Fabric
- Excellent for AI workflows
- Great automation capabilities
- User-friendly interface

### Claude
- Strong reasoning capabilities
- Good for complex tasks
- Reliable performance

## Conclusion

Each tool has its place in the AI productivity landscape.
"""


@pytest.fixture
def valid_youtube_urls():
    """Valid YouTube URLs for testing"""
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
    ]


@pytest.fixture
def invalid_youtube_urls():
    """Invalid YouTube URLs for testing"""
    return [
        "https://vimeo.com/123456789",
        "https://www.google.com",
        "not-a-url",
        "https://youtube.com/watch?v=",
        "",
    ]


@pytest.fixture
def mock_pdf_generator():
    """Mock PDF generator for testing"""
    with patch("src.tool.PDFGeneratorTool") as mock_pdf:
        mock_instance = Mock()
        mock_instance.generate_pdf_bytes.return_value = b"mock pdf content"
        mock_pdf.return_value = mock_instance
        yield mock_pdf


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture(autouse=True)
def setup_ga_test_environment():
    """Set up Google Analytics test environment"""
    with patch.dict(
        os.environ, {"GA_MEASUREMENT_ID": "G-TEST123456", "FLASK_ENV": "testing"}
    ):
        yield


@pytest.fixture
def app_with_ga_config(app):
    """App fixture with GA configuration"""
    app.config["GA_MEASUREMENT_ID"] = "G-TEST123456"
    return app


@pytest.fixture(scope="session")
def temp_directory():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing"""
    test_env = {
        "OPENAI_API_KEY": "test-openai-key",
        "SUPADATA_API_KEY": "test-supadata-key",
        "MONGODB_URI": "mongodb://test-mongo:27017/test_db",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "LOG_LEVEL": "DEBUG",
        "LOGGING_ENABLED": "true",
        "LOKI_ENDPOINT": "http://test-loki:3100",
    }

    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield test_env

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before any tests run"""
    os.environ["TESTING"] = "true"
    os.environ["FLASK_ENV"] = "testing"
    os.environ["CI"] = "true"
    os.environ["LOG_TO_FILE"] = "false"
    os.environ["LOG_LEVEL"] = "DEBUG"

    yield

    # Cleanup
    for key in ["TESTING", "FLASK_ENV", "CI", "LOG_TO_FILE", "LOG_LEVEL"]:
        os.environ.pop(key, None)


# E2E Test Configuration
def pytest_addoption(parser):
    """Add command line options for test execution"""
    parser.addoption(
        "--run-e2e", action="store_true", default=False, help="Run end-to-end tests"
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options"""
    # Skip E2E tests unless explicitly requested
    if not config.getoption("--run-e2e"):
        skip_e2e = pytest.mark.skip(
            reason="E2E tests skipped (use --run-e2e to enable)"
        )
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)

    # Skip integration tests unless explicitly requested or in CI
    if not config.getoption("--run-integration") and not os.environ.get("CI"):
        skip_integration = pytest.mark.skip(
            reason="Integration tests skipped (use --run-integration to enable)"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
