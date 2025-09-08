import os
import re
import gc
import logging
from fpdf import FPDF

logger = logging.getLogger(__name__)


class PDFGeneratorTool:
    def __init__(self):
        pass

    def _clean_unicode_text(self, text: str) -> str:
        """Clean text of problematic Unicode characters for PDF generation"""
        if not text:
            return text

        # Replace common Unicode characters with ASCII equivalents
        unicode_replacements = {
            "\u2014": "--",  # em dash
            "\u2013": "-",  # en dash
            "\u2019": "'",  # right single quotation mark
            "\u2018": "'",  # left single quotation mark
            "\u201c": '"',  # left double quotation mark
            "\u201d": '"',  # right double quotation mark
            "\u2026": "...",  # horizontal ellipsis
            "\u00a0": " ",  # non-breaking space
            "\u2022": "*",  # bullet point
            "\u2010": "-",  # hyphen
            "\u00ad": "-",  # soft hyphen
            "\u00b7": "*",  # middle dot
            "\u25cf": "*",  # black circle
            "\u2212": "-",  # minus sign
            "\u00d7": "x",  # multiplication sign
            "\u00f7": "/",  # division sign
            "\u2190": "<-",  # leftwards arrow
            "\u2192": "->",  # rightwards arrow
            "\u2191": "^",  # upwards arrow
            "\u2193": "v",  # downwards arrow
        }

        for unicode_char, replacement in unicode_replacements.items():
            text = text.replace(unicode_char, replacement)

        # Remove any remaining non-ASCII characters but keep basic punctuation
        cleaned_text = ""
        for char in text:
            if ord(char) < 128:
                cleaned_text += char
            elif char.isspace():
                cleaned_text += " "
            else:
                cleaned_text += "?"  # Replace unknown chars with ?

        return cleaned_text

    def _add_header_footer(self, pdf: FPDF) -> None:
        """Add header and footer to PDF"""
        # Add a subtle header line
        pdf.set_y(10)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)
        pdf.line(15, 12, pdf.w - 15, 12)

        # Add page number in footer
        pdf.set_y(-20)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 10, f"Page {pdf.page_no()}", 0, 0, "C")

    def generate_pdf_bytes(self, content: str) -> bytes:
        """Generate PDF with proper width and formatting"""
        pdf = None
        try:
            # Clean the content first
            content = self._clean_unicode_text(content)

            # Create PDF with A4 size and proper margins
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.add_page()

            # Set proper margins for full width utilization
            pdf.set_margins(15, 15, 15)  # Left, Top, Right margins
            pdf.set_auto_page_break(auto=True, margin=20)  # Bottom margin

            # Calculate effective width
            effective_width = pdf.w - 30  # 210mm - 30mm (margins)

            # Extract and add title
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else "Generated Blog Article"
            title = self._clean_unicode_text(title)

            # Title formatting
            pdf.set_font("Arial", "B", 18)
            pdf.set_text_color(44, 62, 80)

            # Check if title is too long and break it if necessary
            title_width = pdf.get_string_width(title)
            if title_width > effective_width:
                # Break long titles into multiple lines
                words = title.split()
                lines = []
                current_line = ""

                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if pdf.get_string_width(test_line) <= effective_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)

                if current_line:
                    lines.append(current_line)

                # Output multi-line title
                for i, line in enumerate(lines):
                    pdf.cell(0, 12, line, ln=True, align="C")
                    if i < len(lines) - 1:
                        pdf.ln(2)
            else:
                pdf.cell(0, 15, title, ln=True, align="C")

            pdf.ln(10)

            # Add a separator line
            pdf.set_draw_color(102, 126, 234)
            pdf.set_line_width(0.8)
            pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())
            pdf.ln(8)

            # Process content line by line
            lines = content.split("\n")

            for line in lines:
                line = line.strip()

                if not line:
                    pdf.ln(4)
                    continue

                # Skip the main title as it's already added
                if line.startswith("# "):
                    continue

                # Handle main headings (##)
                if line.startswith("## "):
                    pdf.ln(6)
                    pdf.set_font("Arial", "B", 14)
                    pdf.set_text_color(44, 62, 80)
                    heading_text = self._clean_unicode_text(line[3:])

                    if pdf.get_string_width(heading_text) > effective_width:
                        pdf.multi_cell(0, 8, heading_text)
                    else:
                        pdf.cell(0, 10, heading_text, ln=True)
                    pdf.ln(4)
                    continue

                # Handle sub-headings (###)
                elif line.startswith("### "):
                    pdf.ln(4)
                    pdf.set_font("Arial", "B", 12)
                    pdf.set_text_color(52, 73, 94)
                    heading_text = self._clean_unicode_text(line[4:])

                    if pdf.get_string_width(heading_text) > effective_width:
                        pdf.multi_cell(0, 7, heading_text)
                    else:
                        pdf.cell(0, 8, heading_text, ln=True)
                    pdf.ln(3)
                    continue

                # Handle bullet lists
                elif line.startswith("- "):
                    pdf.set_font("Arial", "", 11)
                    pdf.set_text_color(0, 0, 0)
                    list_text = self._clean_unicode_text(line[2:])

                    pdf.set_x(25)
                    pdf.cell(5, 6, "*", ln=False)
                    pdf.set_x(30)

                    available_width = effective_width - 15
                    pdf.multi_cell(available_width, 6, list_text)
                    pdf.ln(2)
                    continue

                # Handle numbered lists
                elif re.match(r"^\d+\.\s+", line):
                    pdf.set_font("Arial", "", 11)
                    pdf.set_text_color(0, 0, 0)

                    match = re.match(r"^(\d+\.\s+)(.+)", line)
                    if match:
                        number = match.group(1)
                        text = self._clean_unicode_text(match.group(2))

                        pdf.set_x(25)
                        number_width = pdf.get_string_width(number)
                        pdf.cell(number_width + 2, 6, number, ln=False)
                        pdf.set_x(25 + number_width + 2)

                        available_width = effective_width - (number_width + 12)
                        pdf.multi_cell(available_width, 6, text)
                        pdf.ln(2)
                    continue

                # Handle regular paragraphs
                else:
                    pdf.set_font("Arial", "", 11)
                    pdf.set_text_color(0, 0, 0)
                    paragraph_text = self._clean_unicode_text(line)

                    if paragraph_text:
                        pdf.multi_cell(0, 7, paragraph_text, align="J")
                        pdf.ln(4)

            # Add page numbers for multi-page documents
            if pdf.page_no() > 1:
                self._add_header_footer(pdf)

            # Generate PDF bytes
            try:
                pdf_output = pdf.output(dest="S")
            except Exception:
                pdf_output = pdf.output()

            # Handle different return types from FPDF
            if isinstance(pdf_output, bytes):
                return pdf_output
            elif isinstance(pdf_output, bytearray):
                return bytes(pdf_output)
            elif isinstance(pdf_output, str):
                return pdf_output.encode("latin1")
            else:
                return bytes(str(pdf_output), "latin1")

        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise RuntimeError(f"PDF generation error: {str(e)}")
        finally:
            if pdf:
                pdf = None
            gc.collect()
