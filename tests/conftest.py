import sys
import pytest
from unittest.mock import MagicMock, patch
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret")

@pytest.fixture
def mock_transcript():
    return "This is a sample transcript from a YouTube video. It contains technical terms like Fabric, Kubernetes, and version 1.2.3."

@pytest.fixture
def mock_blog_content():
    return """# Sample Blog Title
This is a comprehensive technical blog generated from a YouTube transcript.
- Preserving technical terms: Fabric, Kubernetes
- Version numbers: 1.2.3
- Winners: Fabric wins AI category"""

@pytest.fixture
def youtube_url():
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

@pytest.fixture
def mock_tools():
    with patch('src.tool.YouTubeTranscriptTool') as mock_transcript_tool, \
         patch('src.tool.BlogGeneratorTool') as mock_blog_tool:
        mock_transcript_tool.return_value._run.return_value = "mock transcript"
        mock_blog_tool.return_value._run.return_value = "mock blog content"
        yield mock_transcript_tool, mock_blog_tool

@pytest.fixture
def test_client():
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            yield client
            
@pytest.fixture(scope="session")
def sample_transcript_data():
    """Sample transcript data for testing"""
    return [
        {'text': 'Hello world', 'start': 0.0, 'duration': 2.0},
        {'text': 'This is a test', 'start': 2.0, 'duration': 3.0},
        {'text': 'Docker wins the container race', 'start': 5.0, 'duration': 4.0}
    ]

@pytest.fixture
def sample_blog_content():
    """Sample blog content for testing"""
    return "This is a comprehensive blog article about Docker and Kubernetes. " * 50            