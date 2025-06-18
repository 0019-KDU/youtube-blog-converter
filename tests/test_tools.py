from unittest.mock import patch, MagicMock
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool, PDFTool

def test_youtube_transcript_tool_success():
    tool = YouTubeTranscriptTool()
    with patch('src.tool.YouTube') as mock_yt, \
         patch('src.tool.YouTubeTranscriptApi.get_transcript') as mock_get_transcript:
        mock_yt_instance = MagicMock()
        mock_yt_instance.video_id = "test123"
        mock_yt.return_value = mock_yt_instance
        
        mock_get_transcript.return_value = [{'text': 'Hello'}, {'text': 'World'}]
        
        result = tool._run("https://youtube.com/watch?v=test123")
        assert result == "Hello World"

def test_blog_generator_tool():
    tool = BlogGeneratorTool()
    with patch('openai.OpenAI') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated blog"
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        result = tool._run("Sample transcript")
        assert "Generated blog" in result

def test_pdf_tool(tmp_path):
    tool = PDFTool()
    output_path = tmp_path / "test.pdf"
    content = "Test PDF content"
    
    result = tool._run(content, str(output_path))
    assert output_path.exists()
    assert "PDF saved" in result