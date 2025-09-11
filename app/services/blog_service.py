import gc
import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Get API key
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
            prompt = """
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
                            "content": "You are a professional technical writer who creates clean, well-formatted blog posts without markdown artifacts.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=5000,
                    top_p=0.9,
                    frequency_penalty=0.1,
                    presence_penalty=0.1,
                )

                generated_content = response.choices[0].message.content.strip()

            # Clean up the generated content
            cleaned_content = self._clean_markdown_content(generated_content)

            logger.info(
                f"✅ Blog generation successful: {
                    len(cleaned_content)} characters")
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
        content = re.sub(
            r"\*\*([^*]+)\*\*",
            r"\1",
            content)  # Remove bold asterisks
        # Remove italic asterisks
        content = re.sub(r"\*([^*]+)\*", r"\1", content)
        content = re.sub(r"_{2,}", "", content)  # Remove underscores
        content = re.sub(r"-{3,}", "", content)  # Remove horizontal rules
        content = re.sub(r"\|{2,}", "", content)  # Remove pipe symbols
        content = re.sub(r"`{3,}", "", content)  # Remove code blocks
        content = re.sub(r"`([^`]+)`", r"\1", content)  # Remove inline code

        # Fix spacing issues
        content = re.sub(r"\n{3,}", "\n\n", content)  # Max 2 newlines
        content = re.sub(
            r"^\s+", "", content, flags=re.MULTILINE
        )  # Remove leading spaces
        content = re.sub(
            r"\s+$", "", content, flags=re.MULTILINE
        )  # Remove trailing spaces

        # Ensure proper heading format
        content = re.sub(
            r"^#{4,}\s*", "### ", content, flags=re.MULTILINE
        )  # Max 3 levels
        content = re.sub(
            r"^(#{1,3})\s*(.+?)$",
            r"\1 \2\n",
            content,
            flags=re.MULTILINE)

        # Fix list formatting
        content = re.sub(
            r"^\*\s+", "- ", content, flags=re.MULTILINE
        )  # Convert asterisk lists to dashes
        content = re.sub(
            r"^(\d+)\.\s+", r"\1. ", content, flags=re.MULTILINE
        )  # Fix numbered lists

        # Ensure proper paragraph spacing
        lines = content.split("\n")
        formatted_lines = []
        prev_line_empty = False

        for line in lines:
            line = line.strip()

            if not line:
                if not prev_line_empty:
                    formatted_lines.append("")
                prev_line_empty = True
            else:
                if line.startswith("#"):
                    if formatted_lines and formatted_lines[-1] != "":
                        formatted_lines.append("")
                    formatted_lines.append(line)
                    formatted_lines.append("")
                    prev_line_empty = True
                else:
                    formatted_lines.append(line)
                    prev_line_empty = False

        return "\n".join(formatted_lines).strip()


def generate_blog_from_youtube(youtube_url: str, language: str = "en") -> str:
    """Generate a blog article from a YouTube video URL"""
    import time

    start_time = time.time()

    # Check required API keys
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found")
        return _create_error_response(
            youtube_url, "OpenAI API key not found in environment variables"
        )

    if not os.getenv("SUPADATA_API_KEY"):
        logger.error("Supadata API key not found")
        return _create_error_response(
            youtube_url, "SUPADATA_API_KEY not found in environment variables"
        )

    if not youtube_url or not re.match(
        r"^https?://(www\.)?(youtube\.com|youtu\.be)/", youtube_url
    ):
        return _create_error_response(
            youtube_url, "Invalid YouTube URL provided")

    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return _create_error_response(
            youtube_url, "Could not extract valid video ID from URL"
        )

    logger.info(f"Starting blog generation for video ID: {video_id}")

    try:
        logger.info("Using Supadata API approach...")
        result_text = individual_components_test(youtube_url, language)

        if result_text and len(result_text) > 500:
            cleaned_output = _clean_final_output(result_text)
            duration = time.time() - start_time
            logger.info(
                f"✅ Blog generated successfully in {
                    duration:.2f}s (cleaned length: {
                    len(cleaned_output)})")
            return cleaned_output

        duration = time.time() - start_time
        logger.error(f"❌ Blog generation failed after {duration:.2f}s")
        return _create_error_response(
            youtube_url, "Could not generate blog content")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ Blog generation failed after {
                duration:.2f}s: {
                str(e)}")
        return _create_error_response(
            youtube_url, f"Unexpected error: {str(e)}")


def individual_components_test(youtube_url: str, language: str = "en") -> str:
    """Test each component separately to isolate issues"""
    logger.info("Testing individual components...")

    try:
        logger.info("Testing YouTube Transcript Tool...")
        from app.services.youtube_service import YouTubeTranscriptTool

        transcript_tool = YouTubeTranscriptTool()
        transcript_result = transcript_tool._run(youtube_url, language)

        if transcript_result.startswith("ERROR:"):
            logger.error(
                f"❌ Transcript extraction failed: {transcript_result}")
            return _create_error_response(youtube_url, transcript_result)

        logger.info(
            f"✅ Transcript extraction successful: {
                len(transcript_result)} characters")

        # Test Blog Generator Tool
        logger.info("Testing Blog Generator Tool...")
        blog_tool = BlogGeneratorTool()
        blog_result = blog_tool._run(transcript_result)

        if blog_result.startswith("ERROR:"):
            logger.error(f"❌ Blog generation failed: {blog_result}")
            return _create_error_response(youtube_url, blog_result)

        logger.info(
            f"✅ Blog generation successful: {
                len(blog_result)} characters")
        return blog_result

    except Exception as e:
        logger.error(f"❌ Component test failed: {str(e)}")
        return _create_error_response(
            youtube_url,
            f"Component test failed: {
                str(e)}")


def _extract_video_id(url: str) -> str:
    """Extract video ID from URL with enhanced patterns"""
    if not url:
        return None

    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"youtube\.com/embed/([^?]+)",
        r"youtube\.com/v/([^?]+)",
        r"youtube\.com/shorts/([^?]+)",
        r"m\.youtube\.com/watch\?v=([^&]+)",
        r"youtube\.com/live/([^?]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            if re.match(r"^[a-zA-Z0-9_-]{11}$", video_id):
                return video_id
    return None


def _clean_final_output(content: str) -> str:
    """Enhanced content cleaning for better presentation"""
    if not content:
        return ""

    # Remove tool mentions and actions
    content = re.sub(r"Action:\s*\w+", "", content, flags=re.IGNORECASE)
    content = re.sub(r"Tool:\s*\w+", "", content, flags=re.IGNORECASE)
    content = re.sub(r"BlogGeneratorTool", "", content, flags=re.IGNORECASE)
    content = re.sub(
        r"YouTubeTranscriptTool",
        "",
        content,
        flags=re.IGNORECASE)

    # Remove JSON artifacts and unmatched braces
    content = re.sub(r'\{[^{}]*"[^"]*"[^{}]*\}', "", content, flags=re.DOTALL)
    content = re.sub(r"\{[^{}]*\}", "", content, flags=re.DOTALL)
    content = re.sub(r"[{}]", "", content)

    # Remove markdown artifacts but preserve proper formatting
    content = re.sub(r"\*{3,}", "", content)  # Remove excess asterisks
    content = re.sub(r"-{3,}", "", content)  # Remove horizontal rules
    content = re.sub(r"\|{2,}", "", content)  # Remove pipe symbols
    content = re.sub(r"_{3,}", "", content)  # Remove excess underscores

    # Fix heading formatting with proper spacing
    content = re.sub(r"^(\s*#{4,})\s*", r"\1### ", content, flags=re.MULTILINE)
    content = re.sub(
        r"^(\s*#{1,3})\s*(\S)",
        r"\1 \2",
        content,
        flags=re.MULTILINE)

    # Ensure proper spacing between sections
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"^\s+", "", content, flags=re.MULTILINE)
    content = re.sub(r"\s+$", "", content, flags=re.MULTILINE)

    # Fix list formatting
    content = re.sub(r"^\•\s+", "- ", content, flags=re.MULTILINE)
    content = re.sub(r"^\*\s+", "- ", content, flags=re.MULTILINE)
    content = re.sub(r"^(\d+)\.\s+", r"\1. ", content, flags=re.MULTILINE)

    # Ensure proper paragraph structure with better spacing
    lines = content.split("\n")
    formatted_lines = []
    prev_line_empty = False

    for line in lines:
        line = line.strip()

        if not line:
            if not prev_line_empty:
                formatted_lines.append("")
            prev_line_empty = True
        else:
            # Add extra spacing before headings
            if line.startswith("#"):
                if formatted_lines and formatted_lines[-1] != "":
                    formatted_lines.append("")
                formatted_lines.append(line)
                formatted_lines.append("")
                prev_line_empty = True
            else:
                formatted_lines.append(line)
                prev_line_empty = False

    return "\n".join(formatted_lines).strip()


def _create_error_response(youtube_url: str, error_msg: str) -> str:
    """Create informative error response"""
    import time

    return """# YouTube Video Analysis - Technical Issue

## Video Information

**URL**: {youtube_url}
**Processing Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Technical Issue Encountered

{error_msg}

## Troubleshooting Steps

1. **Verify Video Accessibility**: Ensure the video is public and has captions/transcripts available
2. **Check API Limits**: Supadata API may have rate limits
3. **Network Connectivity**: Verify internet connection and API accessibility
4. **Video Format**: Some videos may not have extractable transcripts

## Alternative Approaches

- Try again in a few minutes
- Verify the video has closed captions enabled
- Check if the video is region-restricted
- Ensure the video ID is correctly extracted from the URL
"""
