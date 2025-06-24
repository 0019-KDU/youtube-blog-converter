import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from fpdf import FPDF, FPDF_VERSION

class TranscriptInput(BaseModel):
    """Input schema for YouTube transcript tool."""
    youtube_url: str = Field(..., description="YouTube video URL")
    language: str = Field("en", description="Language code for transcript (e.g., 'en', 'en-US')")

class YouTubeTranscriptTool(BaseTool):
    name: str = "YouTubeTranscriptTool"
    description: str = "Retrieve transcript from a YouTube video URL in the specified language"
    args_schema: Type[TranscriptInput] = TranscriptInput

    def _run(self, youtube_url: str, language: str = "en") -> str:
        try:
            yt = YouTube(youtube_url)
            video_id = yt.video_id
        except Exception as e:
            raise RuntimeError(f"Invalid YouTube URL: {e}")
        
        try:
            # Handle auto language selection
            if language == "auto":
                return self._get_auto_transcript(video_id)
                
            # First try the exact language
            try:
                transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
                return self._format_transcript(transcript_data)
            except:
                # If that fails, try the base language (without region)
                base_lang = language.split('-')[0]
                try:
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[base_lang])
                    return self._format_transcript(transcript_data)
                except:
                    # Finally fall back to any available transcript
                    return self._get_auto_transcript(video_id)
        except Exception as e:
            # Try manual retrieval as fallback
            return self._manual_transcript_fallback(video_id, language)
    
    def _get_auto_transcript(self, video_id):
            """Get first available transcript if specific language fails"""
            try:
                # Replace deprecated list_transcripts() with list()
                transcript_list = YouTubeTranscriptApi.list(video_id)
                
                # Try to find an English transcript first
                for transcript in transcript_list:
                    if transcript.language_code.startswith('en'):
                        return self._format_transcript(transcript.fetch())
                
                # Otherwise, take the first available
                for transcript in transcript_list:
                    return self._format_transcript(transcript.fetch())
                    
                raise RuntimeError("No transcripts found for this video")
            except Exception as e:
                return self._manual_transcript_fallback(video_id)
    
    def _format_transcript(self, transcript_data):
        """Convert transcript data to text"""
        return " ".join(entry['text'] for entry in transcript_data)
    
    def _manual_transcript_fallback(self, video_id, language="en"):
        """Manual transcript retrieval fallback"""
        try:
            # Try direct API call as last resort
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=[language, 'en', 'en-US', 'en-GB'],
                preserve_formatting=True
            )
            return self._format_transcript(transcript)
        except Exception as e:
            # Final fallback to pytube captions
            try:
                yt = YouTube(f'https://www.youtube.com/watch?v={video_id}')
                caption = yt.captions.get(language, None) or yt.captions.get('en', None) or list(yt.captions.all())[0]
                return caption.generate_srt_captions()
            except Exception as fallback_e:
                raise RuntimeError(f"Transcript retrieval failed: {str(fallback_e)}")

class BlogInput(BaseModel):
    """Input schema for blog generation tool."""
    transcript: str = Field(..., description="Video transcript text")

class BlogGeneratorTool(BaseTool):
    name: str = "BlogGeneratorTool"
    description: str = "Generate a blog article from a video transcript using OpenAI GPT-4"
    args_schema: Type[BlogInput] = BlogInput

    def _run(self, transcript: str | dict) -> str:
        # Extract actual transcript from CrewAI output format
        if isinstance(transcript, dict):
            # Handle different possible CrewAI output formats
            if 'raw' in transcript:
                transcript = transcript['raw']
            elif 'description' in transcript:
                transcript = transcript['description']
            elif 'output' in transcript:
                transcript = transcript['output']
            else:
                # Try to convert the dictionary to string
                transcript = str(transcript)
        
        if not isinstance(transcript, str):
            raise TypeError(f"Transcript should be a string, got {type(transcript)}")
        
        if not transcript.strip():
            raise RuntimeError("Transcript is empty; cannot generate blog.")
            
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OpenAI API key not provided. Set OPENAI_API_KEY.")
            
        # Initialize OpenAI client with the new API
        client = openai.OpenAI(api_key=api_key)
        
        prompt = (
            "Write a detailed, well-structured blog article based on the following video transcript:\n\n"
            f"{transcript}"
        )
        try:
            # Use a valid model name
            response = client.chat.completions.create(
                model="gpt-4-turbo",  # Valid current model
                messages=[
                    {"role": "system", "content": "You are an expert content writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            blog_text = response.choices[0].message.content.strip()
            return blog_text
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")

class PDFInput(BaseModel):
    """Input schema for PDF creation tool."""
    content: str = Field(..., description="Text content to write into PDF")
    output_path: str = Field("blog_article.pdf", description="Output PDF file path")

class PDFTool(BaseTool):
    name: str = "PDFTool"
    description: str = "Generate a PDF file from given content"
    args_schema: Type[PDFInput] = PDFInput

    def _run(self, content: str, output_path: str) -> str:
        """Original method that saves to file (for CLI)"""
        pdf_bytes = self.generate_pdf_bytes(content)
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        return f"PDF saved to {output_path}"

    def clean_content(self, content: str) -> str:
        """Normalize content formatting"""
        # Replace problematic characters
        replacements = {
            '\u2019': "'",   # right single quotation mark
            '\u2018': "'",   # left single quotation mark
            '\u201c': '"',   # left double quotation mark
            '\u201d': '"',   # right double quotation mark
            '\u2013': '-',   # en dash
            '\u2014': '--',  # em dash
            '\u2026': '...', # ellipsis
            '\u2022': '-',   # bullet point
        }
        for orig, repl in replacements.items():
            content = content.replace(orig, repl)
        
        # Normalize line breaks
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Ensure consistent heading spacing
        content = content.replace('# ', '#').replace(' #', '#')
        content = content.replace('## ', '##').replace(' ##', '##')
        content = content.replace('### ', '###').replace(' ###', '###')
        
        # Normalize bullet points
        content = content.replace('• ', '- ').replace('* ', '- ')
        
        return content

    def generate_pdf_bytes(self, content: str) -> bytes:
        """Generate PDF in memory with professional formatting"""
        if not content:
            raise RuntimeError("No content provided for PDF generation.")
        
        # Clean and format content
        content = self.clean_content(content)
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        
        # Set font for the whole document
        if FPDF_VERSION < "2.7.8":
            pdf.set_font("Arial", size=12)
        else:
            pdf.set_font("helvetica", size=12)
        
        # Add title
        pdf.set_fill_color(64, 172, 254)  # #4facfe
        pdf.set_text_color(255, 255, 255)
        pdf.set_font_size(18)
        pdf.cell(0, 15, "Blog Article", ln=1, fill=True, align='C')
        pdf.ln(10)
        
        # Reset font for content
        pdf.set_text_color(0, 0, 0)
        if FPDF_VERSION < "2.7.8":
            pdf.set_font("Arial", size=12)
        else:
            pdf.set_font("helvetica", size=12)
        
        # Process content with formatting
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(6)  # Extra space for empty lines
                continue
                
            # Detect headings
            if line.startswith('# '):
                pdf.set_font_size(16)
                pdf.set_text_color(30, 30, 30)
                pdf.cell(0, 10, line[2:].strip(), ln=1)
                pdf.set_font_size(12)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(4)
            elif line.startswith('## '):
                pdf.set_font_size(14)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 10, line[3:].strip(), ln=1)
                pdf.set_font_size(12)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
            elif line.startswith('### '):
                pdf.set_font(style='B')
                pdf.set_text_color(70, 70, 70)
                pdf.cell(0, 10, line[4:].strip(), ln=1)
                pdf.set_font(style='')
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
            else:
                # Process paragraphs
                # Handle bullet points
                if line.startswith('- ') or line.startswith('* '):
                    pdf.set_x(15)
                    pdf.cell(5, 6, "-", ln=0)  # Use simple dash instead of bullet
                    line = line[2:].strip()
                
                # Write the text
                try:
                    # Try to write normally
                    pdf.multi_cell(0, 6, line)
                except:
                    # Fallback for encoding issues
                    pdf.multi_cell(0, 6, line.encode('latin1', 'replace').decode('latin1'))
            
            pdf.ln(4)  # Space between lines
        
        # Add footer
        pdf.set_y(-15)
        pdf.set_font_size(10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Generated by YouTube to Blog Converter", 0, 0, 'C')
        
        # Return as bytes - use 'S' for string then encode
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin1', 'replace')
        elif isinstance(pdf_output, bytearray):
            return bytes(pdf_output)
        else:
            return pdf_output