# ✅ tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from src.tool import PDFGeneratorTool

@pytest.fixture
def dummy_transcript():
    return "This is a sample transcript from a YouTube video about Python development."

@pytest.fixture
def dummy_blog():
    return "# Blog Title\n\nThis is a sample blog article generated from a transcript."

@pytest.fixture
def mock_openai_response():
    with patch("openai.OpenAI") as mock_client:
        instance = MagicMock()
        fake_content = "This is a detailed blog article. " * 20  # >200 characters
        instance.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=fake_content))
        ]
        mock_client.return_value = instance
        yield mock_client


@pytest.fixture
def pdf_generator():
    return PDFGeneratorTool()