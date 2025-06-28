# tests/test_tools.py
from unittest.mock import patch, MagicMock
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFTool
import os
import json
import re

# Fixtures for common test data
@pytest.fixture
def mock_player_response():
    return {
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "baseUrl": "https://example.com/caption/en",
                        "languageCode": "en"
                    },
                    {
                        "baseUrl": "https://example.com/caption/es",
                        "languageCode": "es"
                    }
                ]
            }
        }
    }

@pytest.fixture
def mock_captions_xml():
    return """
    <transcript>
        <text start="1.0" dur="5.0">Hello World</text>
        <text start="6.0" dur="4.0">This is a test transcript</text>
    </transcript>
    """

@pytest.fixture
def mock_player_response_no_captions():
    return {"captions": {}}

@pytest.fixture
def mock_player_response_empty_captions():
    return {"captions": {"playerCaptionsTracklistRenderer": {"captionTracks": []}}}

# YouTubeTranscriptTool Tests
def test_extract_video_id_valid_urls():
    tool = YouTubeTranscriptTool()
    
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/embed/dQw4w9WgXcQ",
        "https://youtube.com/v/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=ABCD",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
    ]
    
    for url in urls:
        assert tool._extract_video_id(url) == "dQw4w9WgXcQ"

def test_extract_video_id_invalid_urls():
    tool = YouTubeTranscriptTool()
    
    urls = [
        "https://example.com/",
        "not a url",
        "https://youtube.com/",
        "https://youtube.com/playlist?list=ABCD"
    ]
    
    for url in urls:
        assert tool._extract_video_id(url) is None

@patch('src.tool.requests.get')
def test_transcript_retry_logic(mock_get):
    tool = YouTubeTranscriptTool()
    
    # First two attempts fail, third succeeds
    mock_get.side_effect = [
        Exception("First error"),
        Exception("Second error"),
        MagicMock(status_code=200, text='<script>var ytInitialPlayerResponse = {}</script>')
    ]
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("https://youtube.com/watch?v=test", "en")
    assert "Transcript retrieval failed after 3 attempts" in str(excinfo.value)

@patch('src.tool.requests.get')
def test_transcript_html_parsing_failure(mock_get):
    tool = YouTubeTranscriptTool()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "No JSON here"
    mock_get.return_value = mock_response
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._get_transcript_from_html("test123", "en")
    assert "Could not find player response in HTML" in str(excinfo.value)

@patch('src.tool.requests.get')
def test_transcript_no_captions(mock_get, mock_player_response_no_captions):
    tool = YouTubeTranscriptTool()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response_no_captions)};</script>'
    mock_get.return_value = mock_response
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._get_transcript_from_html("test123", "en")
    assert "No caption tracks found" in str(excinfo.value)

@patch('src.tool.requests.get')
def test_transcript_empty_captions(mock_get, mock_player_response_empty_captions):
    tool = YouTubeTranscriptTool()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response_empty_captions)};</script>'
    mock_get.return_value = mock_response
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._get_transcript_from_html("test123", "en")
    assert "No caption tracks found" in str(excinfo.value)

@patch('src.tool.requests.get')
def test_transcript_captions_fetch_failure(mock_get, mock_player_response):
    tool = YouTubeTranscriptTool()
    
    html_response = MagicMock()
    html_response.status_code = 200
    html_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'
    
    captions_response = MagicMock()
    captions_response.status_code = 404
    
    mock_get.side_effect = [html_response, captions_response]
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._get_transcript_from_html("test123", "en")
    assert "Failed to fetch captions: HTTP 404" in str(excinfo.value)

# PDFTool Tests
def test_pdf_clean_content():
    tool = PDFTool()
    
    content = "Smart quotes: ‘single’ “double” – dash • bullet"
    cleaned = tool.clean_content(content)
    
    assert "'single'" in cleaned
    assert '"double"' in cleaned
    assert "- dash" in cleaned
    assert "• bullet" in cleaned  # Should remain unchanged
    assert "\r\n" not in cleaned

def test_pdf_formatting_headings():
    tool = PDFTool()
    content = "# Heading 1\n## Heading 2\n### Heading 3"
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert len(pdf_bytes) > 1000

def test_pdf_formatting_bullets():
    tool = PDFTool()
    content = "- Item 1\n* Item 2\n- Item 3"
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert len(pdf_bytes) > 1000

# Fix for test_pdf_formatting_entities
def test_pdf_formatting_entities():
    tool = PDFTool()
    content = "Ampersand: &amp; Less: &lt; Greater: &gt; Quote: &quot;"
    cleaned = tool.clean_content(content)
    
    assert "Ampersand: &" in cleaned
    assert "Less: <" in cleaned
    assert "Greater: >" in cleaned
    assert 'Quote: "' in cleaned
    
    # Also verify PDF generation doesn't fail
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000

def test_pdf_formatting_empty_lines():
    tool = PDFTool()
    content = "Line 1\n\n\nLine 2"
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert len(pdf_bytes) > 1000

def test_pdf_encoding_handling():
    tool = PDFTool()
    content = "Special chars: é à ñ ç ø π 汉字"
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert len(pdf_bytes) > 1000

# BlogGeneratorTool Tests
@patch('src.tool.openai.OpenAI')
def test_blog_generator_dict_inputs(mock_openai):
    tool = BlogGeneratorTool()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Generated blog"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    # Test different dictionary formats
    formats = [
        {'raw': 'Sample transcript'},
        {'description': 'Sample transcript'},
        {'output': 'Sample transcript'},
        {'unknown': 'format'}
    ]
    
    for data in formats:
        result = tool._run(data)
        assert "Generated blog" in result

# Fix for test_blog_generator_non_string_inputs
# Updated test_blog_generator_non_string_inputs
@patch('src.tool.openai.OpenAI')
def test_blog_generator_non_string_inputs(mock_openai):
    tool = BlogGeneratorTool()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Generated blog"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    # Test non-string inputs
    inputs = [
        123,  # Integer
        ['list', 'of', 'strings'],  # List
        None,  # None
        {"key": "value"},  # Dictionary
        b"bytes string"  # Bytes
    ]
    
    for data in inputs:
        result = tool._run(data)
        assert "Generated blog" in result

def test_blog_generator_missing_api_key(monkeypatch):
    tool = BlogGeneratorTool()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("Sample transcript")
    assert "OpenAI API key not provided" in str(excinfo.value)

# Run all tests
if __name__ == "__main__":
    pytest.main()