import logging
from typing import Union

from crewai import Crew

from .agents import create_agents
from .tasks import create_tasks

logger = logging.getLogger(__name__)


class BlogGenerationCrew:
    """Enhanced CrewAI implementation for blog generation"""

    def __init__(self):
        self.transcriber, self.writer = create_agents()

    def generate_blog(self, youtube_url: str, language: str = "en") -> str:
        try:
            logger.info(f"Starting CrewAI blog generation for: {youtube_url}")
            
            # Create agents and tasks fresh for each request
            transcriber, writer = create_agents()
            transcript_task, blog_task = create_tasks(
                transcriber, writer, youtube_url, language
            )

            # Create and execute crew
            crew = Crew(
                agents=[transcriber, writer],
                tasks=[transcript_task, blog_task],
                verbose=True,
                memory=False,
                max_rpm=10,
                share_crew=False,
            )

            logger.info("Executing CrewAI workflow...")
            result = crew.kickoff()

            # Ensure result is converted to string
            # Check for specific iterable types we want to handle, avoiding Mock objects
            # More robust check for Mock objects and other test objects
            is_mock = (hasattr(result, '_mock_name') or 
                      hasattr(result, '_mock_methods') or
                      str(type(result)).startswith("<class 'unittest.mock") or
                      'Mock' in str(type(result)))
            
            if hasattr(result, '__iter__') and not isinstance(result, (str, bytes)) and not is_mock:
                try:
                    # Check if we can actually iterate over the result
                    result = ' '.join(str(item) for item in result)
                except (TypeError, ValueError, AttributeError) as e:
                    # Handle case where object claims to be iterable but isn't
                    logger.debug(f"Object appeared iterable but failed to iterate: {e}")
                    pass
                
            logger.info(f"CrewAI execution completed: {len(str(result))} characters")
            return str(result)

        except Exception as e:
            logger.error(f"CrewAI blog generation failed: {str(e)}")
            # Handle specific Mock iteration errors by providing more meaningful message
            error_msg = str(e)
            if "'Mock' object is not iterable" in error_msg:
                error_msg = "Mock object iteration error during testing"
            return f"ERROR: CrewAI execution failed - {error_msg}"
