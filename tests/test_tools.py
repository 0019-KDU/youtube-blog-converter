# ✅ tests/test_tool.py
import pytest
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool

def test_transcript_tool_extracts_video_id():
    tool = YouTubeTranscriptTool()
    video_id = tool._extract_video_id("https://www.youtube.com/watch?v=abc123xyz")
    assert video_id == "abc123xyz"

def test_transcript_tool_clean_transcript():
    tool = YouTubeTranscriptTool()
    dirty = "Hello \n\n\n[Music] everyone!"
    clean = tool._clean_transcript(dirty)
    assert "[Music]" not in clean and "\n" not in clean

def test_blog_tool_creates_prompt():
    tool = BlogGeneratorTool()
    prompt = tool._create_blog_prompt("Sample transcript text")
    assert "TRANSCRIPT:" in prompt

def test_blog_tool_run_valid(mock_openai_response):
    tool = BlogGeneratorTool()
    result = tool._run("This is a good transcript with more than 50 characters.")
    assert "detailed blog article" in result
