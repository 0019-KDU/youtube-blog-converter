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

    def test_init(self):
        """Test PDFGeneratorTool initialization"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()
        assert tool is not None

    def test_clean_unicode_text_basic(self):
        """Test basic Unicode text cleaning"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()

        input_text = "Test – with — unicode • characters"
        result = tool._clean_unicode_text(input_text)

        assert "–" not in result
        assert "—" not in result
        assert "•" not in result
        assert "-" in result  # Should be replaced with ASCII dash
        assert "*" in result  # Bullet should be replaced with asterisk

    def test_clean_unicode_text_comprehensive(self):
        """Test comprehensive Unicode character cleaning"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()

        input_text = """Test "smart quotes" and 'apostrophes'
        Em dash — and en dash –
        Ellipsis… and non-breaking spaces
        Bullet • points and arrows → ← ↑ ↓
        Math symbols × ÷ −
        Middle dot · and soft hyphen­"""

        result = tool._clean_unicode_text(input_text)

        # Check replacements
        assert '"' in result and '\u201c' not in result  # Smart quotes replaced
        assert "'" in result and '\u2019' not in result  # Smart apostrophes replaced
        assert "--" in result  # Em dash replacement
        assert "..." in result  # Ellipsis replacement
        assert "*" in result  # Bullet replacement
        assert "->" in result  # Arrow replacements
        assert "<-" in result
        assert "x" in result and "×" not in result  # Math symbols
        assert "/" in result and "÷" not in result

    def test_clean_unicode_text_empty(self):
        """Test cleaning empty text"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text("")
        assert result == ""

    def test_clean_unicode_text_none(self):
        """Test cleaning None input"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()
        result = tool._clean_unicode_text(None)
        assert result is None

    def test_clean_unicode_text_non_ascii_fallback(self):
        """Test non-ASCII characters are replaced with question marks"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()

        # Include some characters not in the replacement dict
        input_text = "Test with émojis 🚀 and accénts"
        result = tool._clean_unicode_text(input_text)

        # Should keep ASCII characters and replace unknown ones with ?
        assert "Test with" in result
        assert "?" in result  # Non-ASCII chars become question marks

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_basic(self, mock_fpdf_class):
        """Test basic PDF generation"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210  # A4 width
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes('# Test Title\n\nTest content')

        assert result == b'PDF content'
        mock_pdf.add_page.assert_called()
        mock_pdf.set_margins.assert_called_with(15, 15, 15)
        mock_pdf.set_auto_page_break.assert_called_with(auto=True, margin=20)

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_with_headings(self, mock_fpdf_class):
        """Test PDF generation with different heading levels"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        content = """# Main Title
## Section Heading
### Subsection Heading
Regular paragraph text"""

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'PDF content'
        # Verify different font sizes are set for different heading levels
        font_calls = mock_pdf.set_font.call_args_list
        font_sizes = [call[0][2] for call in font_calls if len(call[0]) > 2]
        assert 18 in font_sizes  # Main title
        assert 14 in font_sizes  # Section heading
        assert 12 in font_sizes  # Subsection heading

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_with_lists(self, mock_fpdf_class):
        """Test PDF generation with bullet and numbered lists"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        content = """# Title
- First bullet point
- Second bullet point
1. First numbered item
2. Second numbered item"""

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'PDF content'
        # Verify set_x is called for list indentation
        mock_pdf.set_x.assert_called()

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_long_title(self, mock_fpdf_class):
        """Test PDF generation with long title that needs line breaking"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        # Simulate long title that exceeds page width
        mock_pdf.get_string_width.side_effect = lambda text: len(text) * 5  # Fake width calculation

        long_title = "# " + "Very Long Title That Should Break Into Multiple Lines Because It Exceeds Page Width"

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(long_title + '\n\nContent')

        assert result == b'PDF content'
        # Should have multiple cell calls for multi-line title
        assert mock_pdf.cell.call_count >= 2

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_no_title(self, mock_fpdf_class):
        """Test PDF generation without explicit title"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        content = "Just some content without a title"

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'PDF content'
        # Should use default title "Generated Blog Article"
        mock_pdf.cell.assert_called()

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_multipage(self, mock_fpdf_class):
        """Test PDF generation with multiple pages"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 2  # Simulate multi-page document
        mock_pdf.get_string_width.return_value = 100

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes('# Title\n\nContent')

        assert result == b'PDF content'
        # Should call header/footer method for multi-page
        # This is tested indirectly through the page_no mock

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_different_output_types(self, mock_fpdf_class):
        """Test PDF generation with different output types from FPDF"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()

        # Test bytes output
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF bytes'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        result = tool.generate_pdf_bytes('# Title\n\nContent')
        assert result == b'PDF bytes'

        # Test bytearray output
        mock_pdf.output.return_value = bytearray(b'PDF bytearray')
        result = tool.generate_pdf_bytes('# Title\n\nContent')
        assert result == b'PDF bytearray'

        # Test string output
        mock_pdf.output.return_value = 'PDF string'
        result = tool.generate_pdf_bytes('# Title\n\nContent')
        assert isinstance(result, bytes)

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_fpdf_exception(self, mock_fpdf_class):
        """Test PDF generation when FPDF raises exception"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.add_page.side_effect = Exception("FPDF error")

        tool = PDFGeneratorTool()

        with pytest.raises(RuntimeError, match="PDF generation error"):
            tool.generate_pdf_bytes('# Title\n\nContent')

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_output_exception_fallback(self, mock_fpdf_class):
        """Test PDF generation when first output call fails but second succeeds"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 1
        mock_pdf.get_string_width.return_value = 100

        # First output call raises exception, second succeeds
        mock_pdf.output.side_effect = [Exception("First call fails"), b'PDF content']

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes('# Title\n\nContent')

        assert result == b'PDF content'
        assert mock_pdf.output.call_count == 2

    @patch('app.crew.tools.FPDF')
    def test_add_header_footer(self, mock_fpdf_class):
        """Test header and footer addition (indirectly through multi-page)"""
        from app.crew.tools import PDFGeneratorTool

        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.output.return_value = b'PDF content'
        mock_pdf.w = 210
        mock_pdf.get_y.return_value = 50
        mock_pdf.page_no.return_value = 2  # Multi-page to trigger header/footer
        mock_pdf.get_string_width.return_value = 100

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes('# Title\n\nContent')

        assert result == b'PDF content'
        # Verify header/footer drawing methods are called
        mock_pdf.set_draw_color.assert_called()
        mock_pdf.line.assert_called()

    def test_clean_unicode_text_whitespace_preservation(self):
        """Test that whitespace characters are preserved during cleaning"""
        from app.crew.tools import PDFGeneratorTool

        tool = PDFGeneratorTool()

        input_text = "Line 1\nLine 2\tTabbed\r\nWindows line ending"
        result = tool._clean_unicode_text(input_text)

        assert "\n" in result
        assert "\t" in result
        assert result.count("\n") >= 2  # Should preserve newlines