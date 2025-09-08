from crewai import Crew
from .agents import create_agents
from .tasks import create_tasks
import logging

logger = logging.getLogger(__name__)


class BlogGenerationCrew:
    """Enhanced CrewAI implementation for blog generation"""

    def __init__(self):
        self.transcriber, self.writer = create_agents()

    def generate_blog(self, youtube_url: str, language: str = "en") -> str:
        """Generate blog from YouTube URL using CrewAI"""
        try:
            logger.info(f"Starting CrewAI blog generation for: {youtube_url}")

            # Create tasks
            transcript_task, blog_task = create_tasks(
                self.transcriber, self.writer, youtube_url, language
            )

            # Create and execute crew
            crew = Crew(
                agents=[self.transcriber, self.writer],
                tasks=[transcript_task, blog_task],
                verbose=True,
                memory=False,
                max_rpm=10,
                share_crew=False,
            )

            logger.info("Executing CrewAI workflow...")
            result = crew.kickoff()

            logger.info(f"CrewAI execution completed: {len(str(result))} characters")
            return str(result)

        except Exception as e:
            logger.error(f"CrewAI blog generation failed: {str(e)}")
            return f"ERROR: CrewAI execution failed - {str(e)}"
