import os
import re
import requests
import json
import logging
import gc
import sys
from contextlib import contextmanager
from dotenv import load_dotenv
from pathlib import Path
from fpdf import FPDF

# Initialize logging
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Get API keys
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

@contextmanager
def openai_client_context():
    """Context manager for OpenAI client to ensure proper cleanup"""
    client = None
    try:
        # Import OpenAI only when needed to avoid COM issues
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        yield client
    except Exception as e:
        logger.error(f"OpenAI client error: {str(e)}")
        raise
    finally:
        # Force cleanup
        if client:
            client = None
        gc.collect()

class YouTubeTranscriptTool:
    def __init__(self):
        if not SUPADATA_API_KEY:
            logger.error("Supadata API key not found in environment variables")
            raise RuntimeError("Supadata API key not configured")

    def _run(self, youtube_url: str, lang: str = 'en') -> str:
        """Fetch transcript from YouTube via Supadata API"""
        session = None
        try:
            # Use session for better connection management
            session = requests.Session()
            session.headers.update({"x-api-key": SUPADATA_API_KEY})
            
            endpoint = "https://api.supadata.ai/v1/youtube/transcript"
            params = {
                "url": youtube_url,
                "lang": lang,
                "text": "true"
            }

            logger.info(f"Fetching transcript for URL: {youtube_url}")
            
            resp = session.get(endpoint, params=params, timeout=30)
            resp.raise_for_status()
            
            data = resp.json()
            if "content" not in data:
                return f"ERROR: Transcript not found for video: {youtube_url}"
            
            logger.info(f"✅ Transcript extraction successful: {len(data['content'])} characters")
            return data["content"]
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            return f"ERROR: HTTP error - {str(e)}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return f"ERROR: Request failed - {str(e)}"
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from API")
            return f"ERROR: Invalid response from transcript API"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"ERROR: Unexpected error - {str(e)}"
        finally:
            if session:
                session.close()

class BlogGeneratorTool:
    def __init__(self):
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not found in environment variables")
            raise RuntimeError("OpenAI API key not configured")

    def _run(self, transcript: str) -> str:
        """Generate blog content from transcript using OpenAI"""
        try:
            if not transcript or len(transcript) < 100:
                return "ERROR: Invalid or empty transcript provided"
            
            if transcript.startswith("ERROR:"):
                return transcript
            
            logger.info("Generating blog content from transcript...")
            
            # Enhanced prompt for better formatting
            prompt = f"""
            Create a comprehensive, well-formatted blog article from the following YouTube transcript.
            
            FORMATTING REQUIREMENTS:
            - Use clean Markdown formatting
            - Start with a compelling title using # (single hash only)
            - Use ## for main sections and ### for subsections
            - Write in complete sentences and paragraphs
            - Use bullet points (-) for lists, not asterisks
            - No markdown artifacts like **, ---, ||, or excess symbols
            - Proper spacing between sections
            - Professional, readable tone
            
            CONTENT REQUIREMENTS:
            - Preserve all specific tool names, company names, and technical terms
            - Include detailed explanations and comparisons
            - Maintain original structure and recommendations
            - Add an engaging introduction and conclusion
            - Use proper paragraph breaks for readability
            
            AVOID:
            - Markdown artifacts (**, ---, ||, etc.)
            - Excessive symbols or decorative elements
            - Poor spacing or formatting
            - Vague generalizations
            
            Transcript:
            {transcript[:15000]}
            """
            
            # Use context manager for proper OpenAI client cleanup
            with openai_client_context() as client:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL_NAME,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a professional technical writer who creates clean, well-formatted blog posts without markdown artifacts."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=0.2,
                    max_tokens=5000,
                    top_p=0.9,
                    frequency_penalty=0.1,
                    presence_penalty=0.1
                )
                
                generated_content = response.choices[0].message.content.strip()
            
            # Clean up the generated content
            cleaned_content = self._clean_markdown_content(generated_content)
            
            logger.info(f"✅ Blog generation successful: {len(cleaned_content)} characters")
            return cleaned_content
        
        except Exception as e:
            logger.error(f"Blog generation failed: {str(e)}")
            return f"ERROR: Blog generation failed - {str(e)}"
        finally:
            # Force garbage collection to clean up COM objects
            gc.collect()
    
    def _clean_markdown_content(self, content: str) -> str:
        """Clean up markdown content to remove artifacts and improve formatting"""
        if not content:
            return content
        
        # Remove markdown artifacts
        content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Remove bold asterisks
        content = re.sub(r'\*([^*]+)\*', r'\1', content)      # Remove italic asterisks
        content = re.sub(r'_{2,}', '', content)               # Remove underscores
        content = re.sub(r'-{3,}', '', content)               # Remove horizontal rules
        content = re.sub(r'\|{2,}', '', content)              # Remove pipe symbols
        content = re.sub(r'`{3,}', '', content)               # Remove code blocks
        content = re.sub(r'`([^`]+)`', r'\1', content)        # Remove inline code
        
        # Fix spacing issues
        content = re.sub(r'\n{3,}', '\n\n', content)          # Max 2 newlines
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)  # Remove leading spaces
        content = re.sub(r'\s+$', '', content, flags=re.MULTILINE)  # Remove trailing spaces
        
        # Ensure proper heading format
        content = re.sub(r'^#{4,}\s*', '### ', content, flags=re.MULTILINE)  # Max 3 levels
        content = re.sub(r'^(#{1,3})\s*(.+?)$', r'\1 \2\n', content, flags=re.MULTILINE)
        
        # Fix list formatting
        content = re.sub(r'^\*\s+', '- ', content, flags=re.MULTILINE)  # Convert asterisk lists to dashes
        content = re.sub(r'^(\d+)\.\s+', r'\1. ', content, flags=re.MULTILINE)  # Fix numbered lists
        
        # Ensure proper paragraph spacing
        lines = content.split('\n')
        formatted_lines = []
        prev_line_empty = False
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if not prev_line_empty:
                    formatted_lines.append('')
                prev_line_empty = True
            else:
                if line.startswith('#'):
                    if formatted_lines and formatted_lines[-1] != '':
                        formatted_lines.append('')
                    formatted_lines.append(line)
                    formatted_lines.append('')
                    prev_line_empty = True
                else:
                    formatted_lines.append(line)
                    prev_line_empty = False
        
        return '\n'.join(formatted_lines).strip()

class PDFGeneratorTool:
    def __init__(self):
        pass
    
    def _clean_unicode_text(self, text: str) -> str:
        """Clean text of problematic Unicode characters for PDF generation"""
        if not text:
            return text
        
        # Replace common Unicode characters with ASCII equivalents
        unicode_replacements = {
            '\u2014': '--',      # em dash
            '\u2013': '-',       # en dash
            '\u2019': "'",       # right single quotation mark
            '\u2018': "'",       # left single quotation mark
            '\u201c': '"',       # left double quotation mark
            '\u201d': '"',       # right double quotation mark
            '\u2026': '...',     # horizontal ellipsis
            '\u00a0': ' ',       # non-breaking space
            '\u2022': '*',       # bullet point
            '\u2010': '-',       # hyphen
            '\u00ad': '-',       # soft hyphen
            '\u00b7': '*',       # middle dot
            '\u25cf': '*',       # black circle
            '\u2212': '-',       # minus sign
            '\u00d7': 'x',       # multiplication sign
            '\u00f7': '/',       # division sign
            '\u2190': '<-',      # leftwards arrow
            '\u2192': '->',      # rightwards arrow
            '\u2191': '^',       # upwards arrow
            '\u2193': 'v',       # downwards arrow
        }
        
        for unicode_char, replacement in unicode_replacements.items():
            text = text.replace(unicode_char, replacement)
        
        # Remove any remaining non-ASCII characters
        text = ''.join(char if ord(char) < 128 else '?' for char in text)
        
        return text
    
    def generate_pdf_bytes(self, content: str) -> bytes:
        """Generate PDF with proper width and formatting"""
        pdf = None
        try:
            # Clean the content first
            content = self._clean_unicode_text(content)
            
            # Create PDF with A4 size and proper margins
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            
            # Set proper margins for full width utilization
            pdf.set_margins(15, 15, 15)  # Left, Top, Right margins
            pdf.set_auto_page_break(auto=True, margin=20)  # Bottom margin
            
            # Calculate effective width
            effective_width = pdf.w - 30  # 210mm - 30mm (margins)
            
            # Extract and add title
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "Generated Blog Article"
            title = self._clean_unicode_text(title)
            
            # Title formatting
            pdf.set_font('Arial', 'B', 20)
            pdf.cell(0, 15, title, ln=True, align='C')
            pdf.ln(10)
            
            # Add a separator line
            pdf.set_draw_color(102, 126, 234)
            pdf.set_line_width(0.8)
            pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())
            pdf.ln(8)
            
            # Process content line by line
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    pdf.ln(4)
                    continue
                
                # Skip the main title as it's already added
                if line.startswith('# '):
                    continue
                
                # Handle main headings (##)
                if line.startswith('## '):
                    pdf.ln(6)
                    pdf.set_font('Arial', 'B', 16)
                    pdf.set_text_color(44, 62, 80)  # Dark blue-gray
                    heading_text = self._clean_unicode_text(line[3:])
                    pdf.cell(0, 10, heading_text, ln=True)
                    pdf.ln(4)
                    continue
                    
                # Handle sub-headings (###)
                elif line.startswith('### '):
                    pdf.ln(4)
                    pdf.set_font('Arial', 'B', 14)
                    pdf.set_text_color(52, 73, 94)  # Medium gray
                    heading_text = self._clean_unicode_text(line[4:])
                    pdf.cell(0, 8, heading_text, ln=True)
                    pdf.ln(3)
                    continue
                
                # Handle bullet lists
                elif line.startswith('- '):
                    pdf.set_font('Arial', '', 11)
                    pdf.set_text_color(0, 0, 0)  # Black text
                    list_text = self._clean_unicode_text(line[2:])
                    
                    # Proper indentation for lists
                    pdf.set_x(25)  # Indent 10mm from left margin
                    pdf.cell(5, 6, "*", ln=False)
                    pdf.set_x(30)  # Text starts after bullet
                    
                    # Use multi_cell for wrapping with proper width
                    pdf.multi_cell(effective_width - 15, 6, list_text)
                    pdf.ln(2)
                    continue
                
                # Handle numbered lists
                elif re.match(r'^\d+\.\s+', line):
                    pdf.set_font('Arial', '', 11)
                    pdf.set_text_color(0, 0, 0)
                    
                    # Extract number and text
                    match = re.match(r'^(\d+\.\s+)(.+)', line)
                    if match:
                        number = match.group(1)
                        text = self._clean_unicode_text(match.group(2))
                        
                        # Proper indentation for numbered lists
                        pdf.set_x(25)
                        pdf.cell(10, 6, number, ln=False)
                        pdf.set_x(35)
                        pdf.multi_cell(effective_width - 20, 6, text)
                        pdf.ln(2)
                    continue
                
                # Handle regular paragraphs
                else:
                    pdf.set_font('Arial', '', 11)
                    pdf.set_text_color(0, 0, 0)
                    paragraph_text = self._clean_unicode_text(line)
                    
                    if paragraph_text:
                        # Use full width for paragraphs
                        pdf.multi_cell(0, 7, paragraph_text)
                        pdf.ln(4)
            
            # Generate PDF bytes with proper handling
            pdf_output = pdf.output(dest='S')
            
            # Handle different return types from FPDF
            if isinstance(pdf_output, bytes):
                return pdf_output
            elif isinstance(pdf_output, bytearray):
                return bytes(pdf_output)
            elif isinstance(pdf_output, str):
                return pdf_output.encode('latin1')
            else:
                return bytes(pdf_output)
        
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            raise RuntimeError(f"PDF generation error: {str(e)}")
        finally:
            # Clean up PDF object
            if pdf:
                pdf = None
            gc.collect()

# Helper function to safely cleanup resources
def cleanup_resources():
    """Force cleanup of resources to prevent Win32 exceptions"""
    gc.collect()
    if hasattr(gc, 'set_debug'):
        gc.set_debug(0)
