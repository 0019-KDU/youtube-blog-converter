# tests/test_tools.py
from unittest.mock import patch, MagicMock
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFTool
import os
import json

@patch('src.tool.requests.get')
def test_youtube_transcript_tool_success(mock_get, mock_player_response, mock_captions_xml):
    # Mock the YouTube page response
    mock_html_response = MagicMock()
    mock_html_response.status_code = 200
    mock_html_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'
    
    # Mock the captions response
    mock_xml_response = MagicMock()
    mock_xml_response.status_code = 200
    mock_xml_response.text = mock_captions_xml
    
    mock_get.side_effect = [mock_html_response, mock_xml_response]

    tool = YouTubeTranscriptTool()
    result = tool._run("https://youtube.com/watch?v=test123", "en")
    assert "Hello" in result
    assert "World" in result
    assert "test transcript" in result

@patch('src.tool.requests.get')
def test_youtube_transcript_tool_auto_fallback(mock_get, mock_player_response, mock_captions_xml):
    # Modify response to have multiple languages
    mock_player_response['captions']['playerCaptionsTracklistRenderer']['captionTracks'].append({
        "baseUrl": "https://example.com/caption/es",
        "languageCode": "es"
    })
    
    mock_html_response = MagicMock()
    mock_html_response.status_code = 200
    mock_html_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'
    
    mock_xml_response = MagicMock()
    mock_xml_response.status_code = 200
    mock_xml_response.text = mock_captions_xml
    
    mock_get.side_effect = [mock_html_response, mock_xml_response]

    tool = YouTubeTranscriptTool()
    result = tool._run("https://youtube.com/watch?v=test123", "auto")
    assert "Hello" in result
    assert "World" in result

@patch('src.tool.requests.get')
def test_youtube_transcript_tool_manual_fallback(mock_get):
    # Mock failed HTML response
    mock_html_response = MagicMock()
    mock_html_response.status_code = 404
    
    mock_get.return_value = mock_html_response

    tool = YouTubeTranscriptTool()
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("https://youtube.com/watch?v=test123", "en")
    assert "Failed to fetch video page" in str(excinfo.value)

@patch('src.tool.requests.get')
def test_youtube_transcript_tool_translation_fallback(mock_get, mock_player_response, mock_captions_xml):
    # Remove English track
    mock_player_response['captions']['playerCaptionsTracklistRenderer']['captionTracks'] = [{
        "baseUrl": "https://example.com/caption/fr",
        "languageCode": "fr"
    }]
    
    mock_html_response = MagicMock()
    mock_html_response.status_code = 200
    mock_html_response.text = f'<script>var ytInitialPlayerResponse = {json.dumps(mock_player_response)};</script>'
    
    mock_xml_response = MagicMock()
    mock_xml_response.status_code = 200
    mock_xml_response.text = mock_captions_xml
    
    mock_get.side_effect = [mock_html_response, mock_xml_response]

    tool = YouTubeTranscriptTool()
    result = tool._run("https://youtube.com/watch?v=test123", "en")
    assert "Hello" in result  # Should still get content

@patch('src.tool.openai.OpenAI')
def test_blog_generator_tool(mock_openai):
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
    
    result = tool._run({'raw': 'Sample transcript'})
    assert "Generated blog" in result

def test_pdf_tool(tmp_path):
    tool = PDFTool()
    output_path = tmp_path / "test.pdf"
    content = "# Test Heading\n\nTest paragraph content"
    
    result = tool._run(content, str(output_path))
    assert output_path.exists()
    assert "PDF saved" in result
    assert output_path.stat().st_size > 1000
    
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000

def test_pdf_content_cleaning():
    tool = PDFTool()
    content = "Smart quotes: ‘hello’ “world” \u2013 dash"
    cleaned = tool.clean_content(content)
    
    assert "'hello'" in cleaned
    assert '"world"' in cleaned
    assert "- dash" in cleaned
    assert "\r\n" not in cleaned

def test_pdf_formatting():
    tool = PDFTool()
    content = "# Heading\n\n- Item 1\n- Item 2\n\nParagraph"
    pdf_bytes = tool.generate_pdf_bytes(content)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000

@patch('src.tool.requests.get')
def test_transcript_tool_invalid_url(mock_get):
    tool = YouTubeTranscriptTool()
    mock_get.side_effect = Exception("Invalid URL")
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("invalid_url", "en")
    assert "Invalid YouTube URL" in str(excinfo.value)

def test_blog_tool_empty_transcript():
    tool = BlogGeneratorTool()
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("   ")
    assert "Transcript is empty" in str(excinfo.value)

def test_pdf_tool_empty_content():
    tool = PDFTool()
    with pytest.raises(RuntimeError) as excinfo:
        tool.generate_pdf_bytes("")
    assert "No content provided" in str(excinfo.value)
    
@patch('src.tool.openai.OpenAI')
def test_blog_generator_tool_api_error(mock_openai):
    tool = BlogGeneratorTool()
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
    
    with pytest.raises(RuntimeError) as excinfo:
        tool._run("Sample transcript")
    assert "OpenAI API call failed" in str(excinfo.value)

def test_pdf_tool_long_content():
    tool = PDFTool()
    content = "# Long Article\n\n" + "This is a test paragraph. " * 500
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000

def test_pdf_tool_special_characters():
    tool = PDFTool()
    content = "Special characters: \u2022 \u2013 \u2014 \u00e9 \u00e0 \u00f1"
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000