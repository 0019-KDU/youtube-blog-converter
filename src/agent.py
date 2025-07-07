from crewai import Agent
from src.tool import YouTubeTranscriptTool, BlogGeneratorTool
import logging

logger = logging.getLogger(__name__)

def create_agents():
    """Create agents with enhanced configuration to prevent tool reuse issues"""
    
    transcriber = Agent(
        role='YouTube Technical Content Extractor',
        goal='Extract complete, detailed transcripts preserving all technical terms and specific tool names',
        backstory=(
            'You are an expert at extracting technical content from videos. '
            'You never generalize or summarize - you capture every specific detail, '
            'tool name, version number, and technical explanation exactly as mentioned. '
            'You handle errors gracefully and provide clear feedback when extraction fails.'
        ),
        tools=[YouTubeTranscriptTool()],
        verbose=True,
        memory=False,  # Disable memory to prevent input reuse
        allow_delegation=False,
        max_retry_limit=1,  # Limit retries to prevent loops
        step_callback=lambda step: logger.info(f"Transcriber step completed")
    )

    writer = Agent(
        role='Technical Blog Writer',
        goal='Create detailed technical blog posts that preserve every specific detail from transcripts',
        backstory=(
            'You are a technical writer who specializes in creating comprehensive, '
            'detailed blog posts from video transcripts. You never generalize or '
            'create vague content. You preserve every tool name, technical comparison, '
            'specific recommendation, and detailed explanation from the original content.'
        ),
        tools=[BlogGeneratorTool()],
        verbose=True,
        memory=False,  # Disable memory to prevent conflicts
        allow_delegation=False,
        max_retry_limit=1,
        step_callback=lambda step: logger.info(f"Writer step completed")
    )
    
    logger.info("Enhanced agents created successfully")
    return transcriber, writer
