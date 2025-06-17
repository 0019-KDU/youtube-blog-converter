import os
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from fpdf import FPDF

class TranscriptInput(BaseModel):
    """Input schema for YouTube transcript tool."""
    youtube_url: str = Field(..., description="YouTube video URL")

class YouTubeTranscriptTool(BaseTool):
    name: str = "YouTubeTranscriptTool"
    description: str = "Retrieve transcript from a YouTube video URL"
    args_schema: Type[TranscriptInput] = TranscriptInput

    def _run(self, youtube_url: str) -> str:
        try:
            yt = YouTube(youtube_url)
            video_id = yt.video_id
        except Exception as e:
            raise RuntimeError(f"Invalid YouTube URL: {e}")
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = " ".join(entry['text'] for entry in transcript_data)
            return full_text
        except Exception as e:
            raise RuntimeError(f"Transcript retrieval failed: {e}")

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
        if not content:
            raise RuntimeError("No content provided for PDF generation.")
        
        # Replace problematic Unicode characters with ASCII equivalents
        replacements = {
            '\u2019': "'",   # right single quotation mark
            '\u2018': "'",   # left single quotation mark
            '\u201c': '"',   # left double quotation mark
            '\u201d': '"',   # right double quotation mark
            '\u2013': '-',   # en dash
            '\u2014': '--',  # em dash
            '\u2026': '...', # ellipsis
        }
        
        for orig, repl in replacements.items():
            content = content.replace(orig, repl)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        for paragraph in content.split("\n\n"):
            pdf.multi_cell(0, 10, paragraph)
            pdf.ln()
        
        pdf.output(output_path)
        return f"PDF saved to {output_path}"