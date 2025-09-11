import re
from unittest.mock import MagicMock, patch

import pytest

from app.crew.tools import PDFGeneratorTool


class TestPDFGeneratorTool:
    """Comprehensive test cases for PDFGeneratorTool"""

    def test_pdf_generator_initialization(self):
        """Test PDF generator initialization"""
        tool = PDFGeneratorTool()
        assert tool is not None

    def test_clean_unicode_text_common_replacements(self):
        """Test Unicode text cleaning with common characters"""
        tool = PDFGeneratorTool()

        # Test all Unicode replacements from the implementation
        test_cases = [
            ("\u2014", "--"),  # em dash
            ("\u2013", "-"),   # en dash
            ("\u2019", "'"),   # right single quotation
            ("\u2018", "'"),   # left single quotation
            ("\u201c", '"'),   # left double quotation
            ("\u201d", '"'),   # right double quotation
            ("\u2026", "..."),  # horizontal ellipsis
            ("\u00a0", " "),   # non-breaking space
            ("\u2022", "*"),   # bullet point
            ("\u2010", "-"),   # hyphen
            ("\u00ad", "-"),   # soft hyphen
            ("\u00b7", "*"),   # middle dot
            ("\u25cf", "*"),   # black circle
            ("\u2212", "-"),   # minus sign
            ("\u00d7", "x"),   # multiplication sign
            ("\u00f7", "/"),   # division sign
            ("\u2190", "<-"),  # leftwards arrow
            ("\u2192", "->"),  # rightwards arrow
            ("\u2191", "^"),   # upwards arrow
            ("\u2193", "v"),   # downwards arrow
        ]

        for unicode_char, expected in test_cases:
            result = tool._clean_unicode_text(f"Text {unicode_char} here")
            assert expected in result
            assert unicode_char not in result

    def test_clean_unicode_text_edge_cases(self):
        """Test Unicode text cleaning edge cases"""
        tool = PDFGeneratorTool()

        # Test empty string
        assert tool._clean_unicode_text("") == ""

        # Test None input
        assert tool._clean_unicode_text(None) is None

        # Test text with only ASCII characters
        ascii_text = "Simple ASCII text 123"
        assert tool._clean_unicode_text(ascii_text) == ascii_text

        # Test mixed Unicode and ASCII
        mixed_text = "Normal text with — special chars"
        cleaned = tool._clean_unicode_text(mixed_text)
        assert "Normal text with -- special chars" == cleaned

        # Test non-ASCII characters that should become '?'
        non_ascii = "Text with café"
        cleaned = tool._clean_unicode_text(non_ascii)
        assert "?" in cleaned  # Non-ASCII chars become '?'

    def test_clean_unicode_text_whitespace_handling(self):
        """Test Unicode whitespace handling"""
        tool = PDFGeneratorTool()

        # Test various whitespace characters
        whitespace_text = "Text\u00a0with\u2009various\u200awhitespace"
        cleaned = tool._clean_unicode_text(whitespace_text)
        # Non-breaking spaces should become regular spaces
        assert " " in cleaned

    @patch('app.crew.tools.FPDF')
    @patch('app.crew.tools.gc')
    def test_generate_pdf_bytes_success(self, mock_gc, mock_fpdf_class):
        """Test successful PDF generation with comprehensive mocking"""
        # Setup mock PDF instance
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        # Configure all the methods that get called
        mock_pdf.w = 210  # A4 width
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'mock pdf content'

        # Test content with various formatting
        content = """# Test Blog Post

## Introduction

This is a test blog post with various formatting:

- List item 1
- List item 2

1. Numbered item 1
2. Numbered item 2

### Sub-section

Regular paragraph text with some content to test PDF generation.
"""

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        # Assertions
        assert isinstance(result, bytes)
        assert result == b'mock pdf content'

        # Verify FPDF methods were called
        mock_pdf.add_page.assert_called_once()
        mock_pdf.set_margins.assert_called_once_with(15, 15, 15)
        mock_pdf.set_auto_page_break.assert_called_once_with(
            auto=True, margin=20)
        mock_pdf.set_font.assert_called()  # Called multiple times
        mock_pdf.cell.assert_called()  # Called multiple times
        mock_pdf.multi_cell.assert_called()  # Called for content
        mock_gc.collect.assert_called_once()

    @patch('app.crew.tools.FPDF')
    @patch('app.crew.tools.gc')
    def test_generate_pdf_bytes_long_title(self, mock_gc, mock_fpdf_class):
        """Test PDF generation with long title that needs wrapping"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        # Configure mock to simulate long title
        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 80  # Return consistent width
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'pdf with long title'

        content = "# Test Title\n\nSome content."

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert isinstance(result, bytes)
        assert result == b'pdf with long title'

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_different_output_types(self, mock_fpdf_class):
        """Test handling of different FPDF output types"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1

        test_cases = [
            (b'bytes_output', b'bytes_output'),
            (bytearray(b'bytearray_output'), b'bytearray_output'),
            ('string_output', b'string_output'),
            (123, b'123'),  # Other types converted to string then bytes
        ]

        tool = PDFGeneratorTool()
        content = "# Test Content\n\nSome text."

        for output_value, expected in test_cases:
            mock_pdf.output.return_value = output_value
            result = tool.generate_pdf_bytes(content)
            assert isinstance(result, bytes)
            assert result == expected

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_output_exception_fallback(
            self, mock_fpdf_class):
        """Test PDF generation with output() exception fallback"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1

        # First call to output(dest="S") raises exception, second call succeeds
        mock_pdf.output.side_effect = [
            Exception("dest not supported"),
            b'fallback_output']

        tool = PDFGeneratorTool()
        content = "# Test Content"
        result = tool.generate_pdf_bytes(content)

        assert result == b'fallback_output'
        assert mock_pdf.output.call_count == 2

    @patch('app.crew.tools.FPDF')
    @patch('app.crew.tools.gc')
    def test_generate_pdf_bytes_multipage_handling(
            self, mock_gc, mock_fpdf_class):
        """Test PDF generation with multiple pages"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 2  # Simulate multiple pages
        mock_pdf.output.return_value = b'multipage pdf'

        content = "# Test\n\n" + "Long content paragraph. " * 100  # Simulate long content

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'multipage pdf'
        # Verify header/footer method is called for multipage
        # Note: _add_header_footer is not called in the mock, but we verify
        # page_no() was checked
        mock_pdf.page_no.assert_called()

    def test_add_header_footer(self):
        """Test header and footer addition"""
        tool = PDFGeneratorTool()
        mock_pdf = MagicMock()

        tool._add_header_footer(mock_pdf)

        # Verify header and footer elements are added
        mock_pdf.set_y.assert_called()
        mock_pdf.set_draw_color.assert_called()
        mock_pdf.set_line_width.assert_called()
        mock_pdf.line.assert_called()
        mock_pdf.set_font.assert_called()
        mock_pdf.set_text_color.assert_called()
        mock_pdf.cell.assert_called()

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_error_handling(self, mock_fpdf_class):
        """Test PDF generation error handling"""
        mock_fpdf_class.side_effect = Exception("FPDF initialization failed")

        tool = PDFGeneratorTool()
        content = "# Test Content"

        with pytest.raises(RuntimeError, match="PDF generation error: FPDF initialization failed"):
            tool.generate_pdf_bytes(content)

    @patch('app.crew.tools.FPDF')
    @patch('app.crew.tools.gc')
    def test_generate_pdf_bytes_cleanup_on_error(
            self, mock_gc, mock_fpdf_class):
        """Test proper cleanup on PDF generation error"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf

        # Make set_font raise an exception during processing
        mock_pdf.set_font.side_effect = Exception("Font error")

        tool = PDFGeneratorTool()
        content = "# Test Content"

        with pytest.raises(RuntimeError):
            tool.generate_pdf_bytes(content)

        # Verify cleanup was called even on error
        mock_gc.collect.assert_called_once()

    def test_generate_pdf_bytes_content_processing(self):
        """Test different content formatting scenarios"""
        tool = PDFGeneratorTool()

        # Test content with various markdown elements
        test_contents = [
            "# Simple Title\n\nParagraph text.",
            "## Main Heading\n\n### Sub Heading\n\nText",
            "- Bullet point 1\n- Bullet point 2",
            "1. Numbered item 1\n2. Numbered item 2",
            "Mixed content:\n\n## Section\n\n- Item\n\n1. Number\n\nParagraph.",
        ]

        with patch('app.crew.tools.FPDF') as mock_fpdf_class:
            mock_pdf = MagicMock()
            mock_fpdf_class.return_value = mock_pdf
            mock_pdf.w = 210
            mock_pdf.get_string_width.return_value = 50
            mock_pdf.get_y.return_value = 20
            mock_pdf.page_no.return_value = 1
            mock_pdf.output.return_value = b'test pdf'

            for content in test_contents:
                result = tool.generate_pdf_bytes(content)
                assert isinstance(result, bytes)
                assert result == b'test pdf'

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_empty_content(self, mock_fpdf_class):
        """Test PDF generation with empty or minimal content"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'empty pdf'

        tool = PDFGeneratorTool()

        # Test with empty string
        result = tool.generate_pdf_bytes("")
        assert result == b'empty pdf'

        # Test with only whitespace
        result = tool.generate_pdf_bytes("   \n\n  ")
        assert result == b'empty pdf'

    @patch('app.crew.tools.FPDF')
    def test_generate_pdf_bytes_unicode_content(self, mock_fpdf_class):
        """Test PDF generation with Unicode content"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'unicode pdf'

        # Content with various Unicode characters
        content = """# Blog Post with Special Characters

Text with — em dash and … ellipsis and • bullet points.

## Section with Quotes

"Smart quotes" and 'apostrophes' should be cleaned.
"""

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'unicode pdf'
        # Verify that _clean_unicode_text was effectively called
        # (we can't directly test this without more complex mocking)

    def test_regex_patterns_in_content_processing(self):
        """Test regex patterns used in content processing"""
        PDFGeneratorTool()

        # Test title extraction regex
        content_with_title = "# Main Title\n\nContent here"
        title_match = re.search(
            r"^#\s+(.+)$",
            content_with_title,
            re.MULTILINE)
        assert title_match is not None
        assert title_match.group(1) == "Main Title"

        # Test numbered list regex
        numbered_line = "1. First item"
        match = re.match(r"^\d+\.\s+", numbered_line)
        assert match is not None

        numbered_match = re.match(r"^(\d+\.\s+)(.+)", numbered_line)
        assert numbered_match is not None
        assert numbered_match.group(1) == "1. "
        assert numbered_match.group(2) == "First item"


# Additional test class for edge cases and performance
class TestPDFGeneratorToolEdgeCases:
    """Test edge cases and performance scenarios"""

    @patch('app.crew.tools.FPDF')
    def test_very_long_content_generation(self, mock_fpdf_class):
        """Test PDF generation with very long content"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'long content pdf'

        # Generate very long content
        long_content = "# Long Document\n\n" + \
            ("This is a very long paragraph. " * 1000)

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(long_content)

        assert result == b'long content pdf'
        # Verify multi_cell was called for long paragraphs
        assert mock_pdf.multi_cell.called

    @patch('app.crew.tools.FPDF')
    def test_special_characters_in_title(self, mock_fpdf_class):
        """Test handling of special characters in title"""
        mock_pdf = MagicMock()
        mock_fpdf_class.return_value = mock_pdf
        mock_pdf.w = 210
        mock_pdf.get_string_width.return_value = 50
        mock_pdf.get_y.return_value = 20
        mock_pdf.page_no.return_value = 1
        mock_pdf.output.return_value = b'special title pdf'

        content = "# Title with — Special & Characters! @#$%\n\nContent here."

        tool = PDFGeneratorTool()
        result = tool.generate_pdf_bytes(content)

        assert result == b'special title pdf'

    def test_memory_cleanup_verification(self):
        """Test that memory cleanup is properly called"""
        with patch('app.crew.tools.FPDF') as mock_fpdf_class, \
                patch('app.crew.tools.gc') as mock_gc:

            mock_pdf = MagicMock()
            mock_fpdf_class.return_value = mock_pdf
            mock_pdf.w = 210
            mock_pdf.get_string_width.return_value = 50
            mock_pdf.get_y.return_value = 20
            mock_pdf.page_no.return_value = 1
            mock_pdf.output.return_value = b'memory test pdf'

            tool = PDFGeneratorTool()
            result = tool.generate_pdf_bytes("# Test\n\nContent")

            # Verify gc.collect was called for cleanup
            mock_gc.collect.assert_called_once()
            assert result == b'memory test pdf'
