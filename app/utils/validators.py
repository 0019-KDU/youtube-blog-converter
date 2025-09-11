import re
import logging

logger = logging.getLogger(__name__)


def validate_youtube_url(url: str) -> bool:
    """Validate if the provided URL is a valid YouTube URL"""
    if not url:
        return False

    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)/", url))


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL with enhanced patterns"""
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


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_password(password: str) -> bool:
    """Validate password strength"""
    if not password:
        return False

    return len(password) >= 8


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    if not filename or not filename.strip():
        return "untitled"

    filename = filename.strip()

    # Remove or replace invalid characters
    sanitized = re.sub(r"[^\w\s-]", "", filename)
    sanitized = re.sub(r"[-\s]+", "-", sanitized)

    # Limit length and clean up
    result = sanitized[:50].strip("-")
    return result if result else "untitled"
