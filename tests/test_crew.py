import pytest
from unittest.mock import patch, MagicMock

class TestCrewComponents:
    
    @patch('app.crew.agents.Agent')
    def test_create_agents(self, mock_agent):
        """Test agent creation"""
        from app.crew.agents import create_agents
        
        # Mock agent instances
        mock_transcriber = MagicMock()
        mock_writer = MagicMock()
        mock_agent.side_effect = [mock_transcriber, mock_writer]
        
        transcriber, writer = create_agents()
        
        assert transcriber is not None
        assert writer is not None
        assert mock_agent.call_count == 2
    
    @patch('app.crew.tasks.Task')
    def test_create_tasks(self, mock_task_class):
        """Test task creation"""
        from app.crew.tasks import create_tasks

        # Mock agents
        mock_transcriber = MagicMock()
        mock_writer = MagicMock()

        # Mock task instances
        mock_transcript_task = MagicMock()
        mock_blog_task = MagicMock()
        mock_task_class.side_effect = [mock_transcript_task, mock_blog_task]

        tasks = create_tasks(mock_transcriber, mock_writer, 'https://youtube.com/watch?v=test', 'en')

        assert len(tasks) == 2
        assert tasks[0] == mock_transcript_task
        assert tasks[1] == mock_blog_task
        assert mock_task_class.call_count == 2
    
    @patch('app.crew.crew.create_agents')
    @patch('app.crew.crew.create_tasks')
    @patch('app.crew.crew.Crew')
    def test_blog_generation_crew(self, mock_crew_class, mock_create_tasks, mock_create_agents):
        """Test BlogGenerationCrew"""
        from app.crew.crew import BlogGenerationCrew
        
        mock_agents = (MagicMock(), MagicMock())
        mock_create_agents.return_value = mock_agents
        mock_tasks = [MagicMock(), MagicMock()]
        mock_create_tasks.return_value = mock_tasks
        
        mock_crew = mock_crew_class.return_value
        mock_crew.kickoff.return_value = "Generated blog content"
        
        crew = BlogGenerationCrew()
        result = crew.generate_blog('https://youtube.com/watch?v=test')
        
        assert result == "Generated blog content"
        mock_crew.kickoff.assert_called_once()

class TestPDFGeneratorTool:
    
    def test_clean_unicode_text(self):
        """Test Unicode text cleaning"""
        from app.crew.tools import PDFGeneratorTool
        
        tool = PDFGeneratorTool()
        
        input_text = "Test – with — unicode • characters"
        result = tool._clean_unicode_text(input_text)
        
        assert "–" not in result
        assert "—" not in result
        assert "•" not in result
    
    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes(self, mock_fpdf_class):
        """Test PDF generation"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'

        # Mock all the methods and attributes used in the tool
        mock_pdf.get_string_width.return_value = 100
        mock_pdf.w = 210  # A4 width in mm
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1

        # Mock all the methods that are called
        mock_pdf.add_page = MagicMock()
        mock_pdf.set_margins = MagicMock()
        mock_pdf.set_auto_page_break = MagicMock()
        mock_pdf.set_font = MagicMock()
        mock_pdf.set_text_color = MagicMock()
        mock_pdf.cell = MagicMock()
        mock_pdf.ln = MagicMock()
        mock_pdf.set_draw_color = MagicMock()
        mock_pdf.set_line_width = MagicMock()
        mock_pdf.line = MagicMock()
        mock_pdf.multi_cell = MagicMock()
        mock_pdf.set_x = MagicMock()

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes('# Test Title\n\nTest content')

        assert result == b'PDF content'
        mock_pdf.add_page.assert_called()