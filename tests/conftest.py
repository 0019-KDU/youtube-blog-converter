import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import json

# Test fixtures for the application
@pytest.fixture
def app():
    """Create a Flask app configured for testing"""
    os.environ['FLASK_SECRET_KEY'] = 'test-secret-key-for-testing'
    os.environ['OPENAI_API_KEY'] = 'test-openai-key'
    os.environ['SUPADATA_API_KEY'] = 'test-supadata-key'
    
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = tempfile.mkdtemp()
    
    with app.app_context():
        yield app
    
    # Cleanup
    if os.path.exists(app.config['SESSION_FILE_DIR']):
        shutil.rmtree(app.config['SESSION_FILE_DIR'])

@pytest.fixture
def client(app):
    """Create a test client for the Flask app"""
    return app.test_client()

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('src.tool.openai_client') as mock_client:
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated blog content"
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_client

@pytest.fixture
def mock_requests():
    """Mock requests for API calls"""
    with patch('src.tool.requests') as mock_requests:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'content': 'Test transcript content'}
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response
        yield mock_requests

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

### ChatGPT
- Versatile conversational AI
- Wide range of applications
- Continuous improvements

## Conclusion

Each tool has its place in the AI productivity landscape.
"""

@pytest.fixture
def valid_youtube_urls():
    """Valid YouTube URLs for testing"""
    return [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtu.be/dQw4w9WgXcQ',
        'https://youtube.com/watch?v=dQw4w9WgXcQ',
        'https://m.youtube.com/watch?v=dQw4w9WgXcQ',
        'https://www.youtube.com/embed/dQw4w9WgXcQ',
        'https://www.youtube.com/v/dQw4w9WgXcQ',
        'https://www.youtube.com/shorts/dQw4w9WgXcQ',
        'https://youtube.com/live/dQw4w9WgXcQ'
    ]

@pytest.fixture
def invalid_youtube_urls():
    """Invalid YouTube URLs for testing"""
    return [
        'https://vimeo.com/123456789',
        'https://www.google.com',
        'not-a-url',
        'https://youtube.com/watch?v=invalid',
        'https://youtube.com/watch?v=',
        '',
        None
    ]

@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing"""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'SUPADATA_API_KEY': 'test-supadata-key',
        'OPENAI_MODEL_NAME': 'gpt-4.1-nano-2025-04-14',
        'FLASK_SECRET_KEY': 'test-secret-key',
        'FLASK_DEBUG': 'False',
        'FLASK_HOST': '127.0.0.1',
        'PORT': '5000'
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def temp_session_dir():
    """Create temporary session directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_pdf_generator():
    """Mock PDF generator for testing"""
    with patch('src.tool.PDFGeneratorTool') as mock_pdf:
        mock_instance = Mock()
        mock_instance.generate_pdf_bytes.return_value = b'mock pdf content'
        mock_pdf.return_value = mock_instance
        yield mock_pdf

@pytest.fixture
def mock_crew_ai():
    """Mock CrewAI components for testing"""
    with patch('src.agents.Agent') as mock_agent, \
         patch('src.tasks.Task') as mock_task:
        
        # Mock agent
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Mock task
        mock_task_instance = Mock()
        mock_task_instance.output = "Mock task output"
        mock_task.return_value = mock_task_instance
        
        yield {
            'agent': mock_agent,
            'task': mock_task,
            'agent_instance': mock_agent_instance,
            'task_instance': mock_task_instance
        }

@pytest.fixture
def mock_logging():
    """Mock logging for testing"""
    with patch('src.main.logger') as mock_logger:
        yield mock_logger

# Test data fixtures
@pytest.fixture
def api_response_success():
    """Successful API response for testing"""
    return {
        'content': 'This is a test transcript from YouTube video'
    }

@pytest.fixture
def api_response_failure():
    """Failed API response for testing"""
    return {
        'error': 'Video not found or transcript unavailable'
    }

@pytest.fixture
def cleanup_test_files():
    """Cleanup test files after testing"""
    test_files = []
    
    def add_file(filename):
        test_files.append(filename)
    
    yield add_file
    
    # Cleanup after test
    for file in test_files:
        if os.path.exists(file):
            os.remove(file)

# Configuration for pytest
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )

# Skip tests if environment variables are not set
def pytest_runtest_setup(item):
    """Setup for each test run"""
    if 'requires_api_keys' in item.keywords:
        if not os.getenv('OPENAI_API_KEY') or not os.getenv('SUPADATA_API_KEY'):
            pytest.skip('API keys not configured for testing')
