# tests/test_tools.py
from unittest.mock import patch, MagicMock
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFTool
import os
import json
import re
import io
from fpdf import FPDF  # Import FPDF to fix NameError

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
def test_transcript_retry_success(mock_get, mock_player_response, mock_captions_xml):
    tool = YouTubeTranscriptTool()
    
    # First attempt fails, second succeeds
    mock_get.side_effect = [
        Exception("First error"),
        MagicMock(status_code=200, text=f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'),
        MagicMock(status_code=200, text=mock_captions_xml)
    ]
    
    result = tool._run("https://youtube.com/watch?v=test", "en")
    assert "Hello" in result
    assert "World" in result

@patch('src.tool.requests.get')
def test_transcript_retry_failure(mock_get):
    tool = YouTubeTranscriptTool()
    
    # All attempts fail
    mock_get.side_effect = Exception("Persistent error")
    
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

@patch('src.tool.requests.get')
def test_transcript_language_fallback(mock_get, mock_player_response, mock_captions_xml):
    tool = YouTubeTranscriptTool()
    
    # Remove the requested language
    mock_player_response['captions']['playerCaptionsTracklistRenderer']['captionTracks'][0]['languageCode'] = 'fr'
    
    html_response = MagicMock()
    html_response.status_code = 200
    html_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'
    
    captions_response = MagicMock()
    captions_response.status_code = 200
    captions_response.text = mock_captions_xml
    
    mock_get.side_effect = [html_response, captions_response]
    
    result = tool._get_transcript_from_html("test123", "en")
    assert "Hello" in result

# PDFTool Tests
def test_pdf_clean_content():
    tool = PDFTool()
    
    content = "Smart quotes: ‘single’ “double” – dash • bullet &amp; &lt; &gt;"
    cleaned = tool.clean_content(content)
    
    assert "'single'" in cleaned
    assert '"double"' in cleaned
    assert "- dash" in cleaned
    assert "&amp;" not in cleaned
    assert "&lt;" not in cleaned
    assert "&gt;" not in cleaned
    assert "• bullet" in cleaned
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
def test_blog_generator_success(mock_openai):
    tool = BlogGeneratorTool()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Generated blog"
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    result = tool._run("Sample transcript")
    assert "Generated blog" in result

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

def test_blog_generator_empty_transcript():
    tool = BlogGeneratorTool()
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("   ")
    assert "Transcript is empty" in str(excinfo.value)

def test_blog_generator_missing_api_key(monkeypatch):
    tool = BlogGeneratorTool()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("Sample transcript")
    assert "OpenAI API key not provided" in str(excinfo.value)

@patch('src.tool.openai.OpenAI')
def test_blog_generator_api_error(mock_openai):
    tool = BlogGeneratorTool()
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("Sample transcript")
    assert "OpenAI API call failed" in str(excinfo.value)

# Run all tests
if __name__ == "__main__":
    pytest.main()