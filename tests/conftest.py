import pytest
import warnings
from unittest.mock import MagicMock

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for all tests"""
    monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test_secret")
    # Mock pytube and transcript API to avoid real network calls
    monkeypatch.setattr('src.tool.YouTube', MagicMock())
    monkeypatch.setattr('src.tool.YouTubeTranscriptApi.get_transcript', MagicMock())

@pytest.fixture
def mock_transcript():
    return "This is a sample video transcript for testing purposes."

@pytest.fixture
def mock_blog_content():
    return "Generated blog article based on video transcript."