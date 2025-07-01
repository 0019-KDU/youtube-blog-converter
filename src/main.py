import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew
from src.agent import create_agents
from src.task import create_tasks
import re

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def _extract_video_id(url: str) -> str:
    """Extract video ID from URL"""
    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"youtube\.com/embed/([^?]+)",
        r"youtube\.com/v/([^?]+)",
        r"youtube\.com/shorts/([^?]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def _is_video_related(content: str, youtube_url: str) -> bool:
    """Check if blog content is related to the video"""
    if not content or len(content) < 200:
        return False
    
    # Check for meaningful content indicators
    video_indicators = [
        "transcript", "video", "discusses", "explains", 
        "mentions", "according to", "speaker", "presenter"
    ]
    
    content_lower = content.lower()
    indicator_count = sum(1 for indicator in video_indicators if indicator in content_lower)
    
    # Must have at least 2 video-related indicators and be substantial
    return indicator_count >= 2 and len(content) > 500

def generate_blog_from_youtube(youtube_url: str, language: str = "en") -> str:
    """Generate a blog article from a YouTube video URL"""
    # Validate input
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found")
        raise RuntimeError("OpenAI API key not found")
    
    if not youtube_url or not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', youtube_url):
        raise ValueError("Invalid YouTube URL provided")
    
    logger.info(f"Starting blog generation for: {youtube_url}")
    
    try:
        # Create agents and tasks
        transcriber, writer = create_agents()
        transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
        
        # Form the crew
        crew = Crew(
            agents=[transcriber, writer],
            tasks=[transcript_task, blog_task],
            verbose=True
        )
        
        # Execute crew
        result = crew.kickoff()
        
        # Convert result to string if it's not already
        if hasattr(result, 'raw'):
            result_text = result.raw
        else:
            result_text = str(result)
        
        # Verify the result contains video-related content
        if not _is_video_related(result_text, youtube_url):
            logger.warning("Generated blog not sufficiently video-related")
            # Return the result anyway, but log the issue
        
        logger.info(f"Successfully generated blog for: {youtube_url}")
        return result_text
        
    except Exception as e:
        logger.error(f"Blog generation failed: {str(e)}")
        raise

def cli_main():
    """Command line interface"""
    youtube_url = input("Enter YouTube video URL: ").strip()
    language = input("Enter language (e.g., 'en'): ").strip() or "en"

    try:
        blog_output = generate_blog_from_youtube(youtube_url, language)
        print("\nGenerated blog article:")
        print(blog_output[:500] + "...\n")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cli_main()