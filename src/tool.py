import os
import time
import logging
import random
import re
import json
import requests
from typing import Type
from pydantic import BaseModel, Field
import openai
from fpdf import FPDF, FPDF_VERSION
from crewai.tools import BaseTool
from fpdf.enums import XPos, YPos
# Set up logging
logger = logging.getLogger(__name__)

# Set custom headers to mimic a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

class TranscriptInput(BaseModel):
    """Input schema for YouTube transcript tool."""
    youtube_url: str = Field(..., description="YouTube video URL")
    language: str = Field("auto", description="Language code for transcript (e.g., 'en', 'en-US'), or 'auto' for auto-detect")

class YouTubeTranscriptTool(BaseTool):
    name: str = "YouTubeTranscriptTool"
    description: str = "Retrieve transcript from a YouTube video URL in the specified language. Use 'auto' for automatic language detection."
    args_schema: Type[TranscriptInput] = TranscriptInput

    def _run(self, youtube_url: str, language: str = "auto") -> str:
        """Retrieve transcript with retry logic and proper headers"""
        max_retries = 3
        backoff_factor = 1
        transcript = None
        
        for attempt in range(max_retries):
            try:
                transcript = self._get_transcript(youtube_url, language)
                if transcript:
                    return transcript
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Transcript retrieval failed after {max_retries} attempts: {str(e)}")
                
                # Exponential backoff with jitter
                sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
        
        return transcript

    def _get_transcript(self, youtube_url: str, language: str) -> str:
        """Main logic to retrieve transcript"""
        try:
            # Extract video ID from URL
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                raise RuntimeError("Invalid YouTube URL format")
            
            logger.info(f"Retrieving transcript for video: {video_id}")
            
            # Use the reliable HTML parsing method
            return self._get_transcript_from_html(video_id, language)
                
        except Exception as e:
            logger.error(f"Transcript retrieval failed: {str(e)}")
            raise RuntimeError(f"Transcript retrieval failed: {str(e)}")

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r"youtube\.com/watch\?v=([^&]+)",
            r"youtu\.be/([^?]+)",
            r"youtube\.com/embed/([^?]+)",
            r"youtube\.com/v/([^?]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from short URL parameters
        if "youtu.be" in url:
            path = url.split("youtu.be/")[1].split("?")[0]
            return path.split("/")[0]
        
        return None

    def _get_transcript_from_html(self, video_id: str, language: str) -> str:
        """Get transcript by parsing YouTube HTML"""
        try:
            # Fetch the watch page
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                raise RuntimeError(f"Failed to fetch video page: HTTP {response.status_code}")
            
            html = response.text
            
            # Find the JSON data in the HTML
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
            if not match:
                raise RuntimeError("Could not find player response in HTML")
            
            # Parse the JSON data
            player_response = json.loads(match.group(1))
            
            # Find captions in the player response
            captions = player_response.get('captions', {})
            caption_tracks = captions.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
            
            if not caption_tracks:
                raise RuntimeError("No caption tracks found")
            
            # Find the best matching caption track
            caption_url = None
            for track in caption_tracks:
                if language == "auto" and track.get('languageCode', '').startswith('en'):
                    caption_url = track.get('baseUrl')
                    break
                elif track.get('languageCode', '') == language:
                    caption_url = track.get('baseUrl')
                    break
                elif track.get('languageCode', '').split('-')[0] == language.split('-')[0]:
                    caption_url = track.get('baseUrl')
                    break
            
            if not caption_url:
                # Use the first available caption
                caption_url = caption_tracks[0].get('baseUrl')
            
            if not caption_url:
                raise RuntimeError("No captions URL found")
            
            # Fetch the captions XML
            captions_response = requests.get(caption_url, headers=HEADERS)
            if captions_response.status_code != 200:
                raise RuntimeError(f"Failed to fetch captions: HTTP {captions_response.status_code}")
            
            # Parse XML to extract text
            text_lines = []
            for line in captions_response.text.split('<text '):
                if 'start=' in line and 'dur=' in line:
                    text = line.split('>', 1)[1].split('</text>', 1)[0]
                    # Handle HTML entities
                    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
                    text_lines.append(text)
            
            return ' '.join(text_lines)
            
        except Exception as e:
            logger.error(f"HTML transcript retrieval failed: {str(e)}")
            raise RuntimeError(f"HTML transcript retrieval failed: {str(e)}")

# Rest of the file remains the same...
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
        "As an expert content writer, create a comprehensive, well-structured blog article based on the video transcript below. "
        "Follow these guidelines:\n\n"
        "1. Structure: Use clear headings and subheadings (H2, H3) to organize content\n"
        "2. Introduction: Start with an engaging overview that summarizes the key topic\n"
        "3. Content Body:\n"
        "   - Break down complex ideas into digestible sections\n"
        "   - Include bullet points for key takeaways\n"
        "   - Add relevant examples where appropriate\n"
        "4. Tone: Maintain a professional yet conversational style\n"
        "5. SEO Optimization:\n"
        "   - Naturally incorporate relevant keywords\n"
        "   - Include meta description at the end\n"
        "6. Formatting: Use Markdown for headings, lists, and emphasis\n"
        "7. Conclusion: End with a summary and thought-provoking question\n"
        "8. Additional Elements:\n"
        "   - Create 3-5 FAQ questions based on content\n"
        "   - Suggest 3 related topics for further reading\n\n"
        "Video Transcript:\n"
        f"{transcript}"
       )
        try:
            # Use a valid model name
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert content writer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            blog_text = response.choices[0].message.content.strip()
            return blog_text
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}")

class PDFInput(BaseModel):
    """Input schema for PDF creation tool."""
    content: str = Field(..., description="Text content to write into PDF")
    output_path: str = Field("blog_article.pdf", description="Output PDF file path")

import io  # Add this import at the top of the file

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
        # Replace smart quotes and dashes
        content = content.replace('‘', "'").replace('’', "'")
        content = content.replace('“', '"').replace('”', '"')
        content = content.replace('\u2013', '-').replace('\u2014', '--')
        
        # Normalize newlines
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        return content

    def generate_pdf_bytes(self, content: str) -> bytes:
        """Generate PDF in memory with professional formatting"""
        if not content:
            raise RuntimeError("No content provided for PDF generation.")
        
        # Clean and format content
        content = self.clean_content(content)

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
        pdf.cell(0, 15, "Blog Article", fill=True, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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
                pdf.cell(0, 10, line[2:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font_size(12)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(4)
            elif line.startswith('## '):
                pdf.set_font_size(14)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(0, 10, line[3:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font_size(12)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(3)
            elif line.startswith('### '):
                pdf.set_font(style='B')
                pdf.set_text_color(70, 70, 70)
                pdf.cell(0, 10, line[4:].strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font(style='')
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)
            else:
                # Process paragraphs
                # Handle bullet points
                if line.startswith('- ') or line.startswith('* '):
                    pdf.set_x(15)
                    pdf.cell(5, 6, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
                    line = line[2:].strip()
                
                # Write the text
                try:
                    pdf.multi_cell(0, 6, line)
                except:
                    pdf.multi_cell(0, 6, line.encode('latin1', 'replace').decode('latin1'))
            
            pdf.ln(4)  # Space between lines
        
        # Add footer
        pdf.set_y(-15)
        pdf.set_font_size(10)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Generated by YouTube to Blog Converter", new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        # Return as bytes using BytesIO
        with io.BytesIO() as output_buffer:
            pdf.output(output_buffer)
            return output_buffer.getvalue()