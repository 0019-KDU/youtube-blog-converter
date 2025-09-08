import os
import json
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Get API key
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

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