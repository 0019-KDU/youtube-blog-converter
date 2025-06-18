from unittest.mock import patch, MagicMock
import pytest
from src.main import generate_blog_from_youtube

@patch('src.main.Crew')
@patch('src.main.create_agents')
@patch('src.main.create_tasks')
def test_generate_blog_success(mock_tasks, mock_agents, mock_crew, tmp_path):
    # Mock agents and tasks
    mock_transcriber = MagicMock()
    mock_writer = MagicMock()
    mock_agents.return_value = (mock_transcriber, mock_writer)
    
    # Mock tasks
    mock_blog_task = MagicMock()
    mock_blog_task.output.raw = "Generated blog content"
    mock_tasks.return_value = (MagicMock(), mock_blog_task)
    
    # Mock crew
    mock_crew_instance = MagicMock()
    mock_crew.return_value = mock_crew_instance
    mock_crew_instance.kickoff.return_value = "Crew result"
    
    # Test PDF generation
    with patch('src.main.PDFTool') as mock_pdf:
        mock_pdf.return_value._run.return_value = "PDF saved"
        
        blog, pdf = generate_blog_from_youtube("https://youtube.com/test")
        assert "Generated blog" in blog
        assert pdf.endswith(".pdf")

def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OpenAI API key not found"):
        generate_blog_from_youtube("https://youtube.com/test")