# tests/conftest.py
import pytest
import warnings
from unittest.mock import MagicMock, patch
import json

# Suppress Pydantic deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for all tests"""
    monkeypatch.setenv("OPENAI_API_KEY", "test_api_key")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test_secret")
    
    # Mock requests to avoid real network calls
    monkeypatch.setattr('src.tool.requests.get', MagicMock())

@pytest.fixture
def mock_transcript():
    return "This is a sample video transcript for testing purposes."

@pytest.fixture
def mock_blog_content():
    return "Generated blog article based on video transcript."

@pytest.fixture
def mock_player_response():
    """Mock YouTube player response JSON"""
    return {
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "baseUrl": "https://example.com/captions/en",
                        "languageCode": "en"
                    }
                ]
            }
        }
    }

@pytest.fixture
def mock_captions_xml():
    """Mock YouTube captions XML"""
    return '''
    <transcript>
        <text start="0" dur="1">Hello</text>
        <text start="1" dur="1">World</text>
        <text start="2" dur="1">This is a test transcript</text>
    </transcript>
    '''