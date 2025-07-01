# src/tool.py
import os
import logging
import openai
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import re
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

# YouTube Transcript Tool
class TranscriptInput(BaseModel):
    youtube_url: str = Field(..., description="YouTube video URL")
    language: str = Field("en", description="Language code for transcript")

class YouTubeTranscriptTool(BaseTool):
    name: str = "YouTubeTranscriptTool"
    description: str = "Extract transcript from YouTube video using youtube-transcript-api"
    args_schema: Type[TranscriptInput] = TranscriptInput

    def _run(self, youtube_url: str, language: str = "en") -> str:
        """Extract transcript using youtube-transcript-api"""
        try:
            video_id = self._extract_video_id(youtube_url)
            if not video_id:
                raise ValueError("Could not extract video ID from URL")
            
            logger.info(f"Extracting transcript for video ID: {video_id}")
            
            # Try to get transcript in the specified language first
            try:
                if language == "en":
                    # For English, try multiple variants
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    
                    # Try to find English transcript (auto-generated or manual)
                    try:
                        transcript = transcript_list.find_transcript(['en'])
                    except:
                        # If no English, try auto-generated
                        try:
                            transcript = transcript_list.find_generated_transcript(['en'])
                        except:
                            # Get any available transcript and translate to English
                            available_transcripts = list(transcript_list)
                            if available_transcripts:
                                transcript = available_transcripts[0].translate('en')
                            else:
                                raise Exception("No transcripts available")
                else:
                    # For other languages
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript = transcript_list.find_transcript([language])
                
                # Get the transcript data
                transcript_data = transcript.fetch()
                
                # Format the transcript
                formatter = TextFormatter()
                formatted_transcript = formatter.format_transcript(transcript_data)
                
                # Clean up the transcript
                cleaned_transcript = self._clean_transcript(formatted_transcript)
                
                if len(cleaned_transcript) < 50:
                    raise ValueError("Transcript too short or empty")
                
                logger.info(f"Successfully extracted transcript ({len(cleaned_transcript)} characters)")
                return cleaned_transcript
                
            except Exception as e:
                logger.error(f"Error getting transcript: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Transcript extraction failed: {str(e)}")
            raise Exception(f"Could not extract transcript: {str(e)}")

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
            r'youtube\.com\/shorts\/([^&\n?#]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _clean_transcript(self, transcript: str) -> str:
        """Clean and format the transcript"""
        if not transcript:
            return ""
        
        # Remove extra whitespace and newlines
        transcript = re.sub(r'\n+', ' ', transcript)
        transcript = re.sub(r'\s+', ' ', transcript)
        
        # Remove timestamps if any remain
        transcript = re.sub(r'\[\d+:\d+\]', '', transcript)
        
        # Clean up common transcript artifacts
        transcript = re.sub(r'\[Music\]', '', transcript)
        transcript = re.sub(r'\[Applause\]', '', transcript)
        transcript = re.sub(r'\[Laughter\]', '', transcript)
        
        return transcript.strip()

# Blog Generator Tool
class BlogInput(BaseModel):
    content: str = Field(..., description="Transcript content to convert to blog")

class BlogGeneratorTool(BaseTool):
    name: str = "BlogGeneratorTool"
    description: str = "Convert transcript content into a well-structured blog article"
    args_schema: Type[BlogInput] = BlogInput

    def _run(self, content: str) -> str:
        """Generate blog article from transcript content"""
        try:
            if not content or len(content) < 50:
                raise ValueError("Content is too short to generate a meaningful blog article")
            
            # Create the prompt for blog generation
            prompt = self._create_blog_prompt(content)
            
            # Generate blog using OpenAI
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert blog writer who creates engaging, well-structured articles from video transcripts."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            blog_content = response.choices[0].message.content.strip()
            
            if len(blog_content) < 200:
                raise ValueError("Generated blog content is too short")
            
            logger.info(f"Successfully generated blog article ({len(blog_content)} characters)")
            return blog_content
                
        except Exception as e:
            logger.error(f"Blog generation failed: {str(e)}")
            raise Exception(f"Could not generate blog article: {str(e)}")

    def _create_blog_prompt(self, transcript: str) -> str:
        """Create a comprehensive prompt for blog generation"""
        return f"""
Please create a comprehensive, engaging blog article based on the following video transcript. 

REQUIREMENTS:
1. Create an engaging, descriptive title that reflects the main topic
2. Write a compelling introduction that hooks the reader
3. Organize the content into clear sections with appropriate headings
4. Extract and explain the key concepts, insights, and takeaways
5. Use Markdown formatting with proper headings (##, ###)
6. Make it at least 800-1000 words
7. Include specific examples or quotes from the transcript where relevant
8. End with a strong conclusion that summarizes the main points
9. Write in an engaging, conversational tone that's easy to read
10. Add a note at the end mentioning this was based on a YouTube video

TRANSCRIPT:
{transcript}

Please create a well-structured, informative blog article that would be valuable to readers interested in this topic.
"""


# Enhanced PDFGeneratorTool class
class PDFGeneratorTool:
    def __init__(self):
        self.styles = self._create_styles()
    
    def _create_styles(self):
        """Create styles with better error handling"""
        try:
            styles = getSampleStyleSheet()
            
            # Create custom styles
            styles.add(ParagraphStyle(
                name='Title',
                fontSize=24,
                leading=28,
                alignment=1,
                spaceAfter=20
            ))
            
            styles.add(ParagraphStyle(
                name='Heading1',
                fontSize=18,
                leading=22,
                spaceBefore=20,
                spaceAfter=10
            ))
            
            styles.add(ParagraphStyle(
                name='Normal',
                fontSize=12,
                leading=16,
                spaceAfter=10
            ))
            
            return styles
        except Exception as e:
            logger.error(f"Style creation failed: {str(e)}")
            # Return minimal styles
            styles = getSampleStyleSheet()
            return styles

    def generate_pdf_bytes(self, content: str) -> bytes:
        """Generate PDF with robust error handling"""
        try:
            buffer = io.BytesIO()
            
            # Create simple document
            doc = SimpleDocTemplate(
                buffer, 
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            
            elements = []
            styles = self.styles
            
            # Add title
            elements.append(Paragraph("Blog Article", styles['Title']))
            elements.append(Spacer(1, 12))
            
            # Add content
            content = content.replace('\n\n', '<br/><br/>')
            content = content.replace('\n', '<br/>')
            content_para = Paragraph(content, styles['Normal'])
            elements.append(content_para)
            
            # Build PDF
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            # Return minimal PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer)
            p.drawString(100, 750, "Blog Content Unavailable")
            p.save()
            pdf_bytes = buffer.getvalue()
            buffer.close()
            return pdf_bytes