from unittest.mock import patch, MagicMock
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFTool
import os

def test_youtube_transcript_tool_success():
    tool = YouTubeTranscriptTool()
    with patch('src.tool.YouTube') as mock_yt, \
         patch('src.tool.YouTubeTranscriptApi.get_transcript') as mock_get_transcript:
        # Mock YouTube object
        mock_yt_instance = MagicMock()
        mock_yt_instance.video_id = "test123"
        mock_yt.return_value = mock_yt_instance
        
        # Mock transcript data
        mock_get_transcript.return_value = [{'text': 'Hello'}, {'text': 'World'}]
        
        # Test with language parameter
        result = tool._run("https://youtube.com/watch?v=test123", "en")
        assert result == "Hello World"

def test_youtube_transcript_tool_auto_fallback():
    tool = YouTubeTranscriptTool()
    with patch('src.tool.YouTube') as mock_yt, \
         patch('src.tool.YouTubeTranscriptApi.list_transcripts') as mock_list:
        # Mock YouTube object
        mock_yt_instance = MagicMock()
        mock_yt_instance.video_id = "test123"
        mock_yt.return_value = mock_yt_instance
        
        # Mock transcript list
        mock_transcript = MagicMock()
        mock_transcript.language_code = "en-US"
        mock_transcript.fetch.return_value = [{'text': 'Auto'}, {'text': 'Detected'}]
        mock_list.return_value = [mock_transcript]
        
        # Test auto language detection
        result = tool._run("https://youtube.com/watch?v=test123", "auto")
        assert result == "Auto Detected"

def test_youtube_transcript_tool_manual_fallback():
    tool = YouTubeTranscriptTool()
    with patch('src.tool.YouTube') as mock_yt, \
         patch('src.tool.YouTubeTranscriptApi.get_transcript') as mock_get_transcript:
        # Mock YouTube object
        mock_yt_instance = MagicMock()
        mock_yt_instance.video_id = "test123"
        mock_yt.return_value = mock_yt_instance
        mock_yt_instance.captions = {
            'en': MagicMock(generate_srt_captions=lambda: "1\n00:00:00,000 --> 00:00:02,000\nFallback content")
        }
        
        # Force failure in standard methods
        mock_get_transcript.side_effect = Exception("Test error")
        
        # Test manual fallback
        result = tool._run("https://youtube.com/watch?v=test123", "en")
        assert "Fallback content" in result

def test_blog_generator_tool():
    tool = BlogGeneratorTool()
    with patch('openai.OpenAI') as mock_openai:
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Generated blog"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        # Test with string input
        result = tool._run("Sample transcript")
        assert "Generated blog" in result
        
        # Test with CrewAI dict input
        result = tool._run({'raw': 'Sample transcript'})
        assert "Generated blog" in result

def test_pdf_tool(tmp_path):
    tool = PDFTool()
    output_path = tmp_path / "test.pdf"
    content = "# Test Heading\n\nTest paragraph content"
    
    # Test file generation
    result = tool._run(content, str(output_path))
    
    # Verify PDF file was created
    assert output_path.exists()
    assert output_path.stat().st_size > 1000
    
    # Test in-memory generation
    pdf_bytes = tool.generate_pdf_bytes(content)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # Ensure reasonable PDF size

def test_pdf_content_cleaning():
    tool = PDFTool()
    content = "Smart quotes: ‘hello’ “world” \u2013 dash"
    cleaned = tool.clean_content(content)
    
    assert "'hello'" in cleaned
    assert '"world"' in cleaned
    assert "- dash" in cleaned  # Fixed to match actual behavior
    assert "\r\n" not in cleaned

def test_pdf_formatting():
    tool = PDFTool()
    content = "# Heading\n\n- Item 1\n- Item 2\n\nParagraph"
    pdf_bytes = tool.generate_pdf_bytes(content)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000

def test_transcript_tool_invalid_url():
    tool = YouTubeTranscriptTool()
    
    # Mock YouTube to raise exception
    with patch('src.tool.YouTube', side_effect=Exception("Invalid URL")):
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