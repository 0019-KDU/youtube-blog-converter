from crewai import Task
import logging

logger = logging.getLogger(__name__)


def create_tasks(transcriber, writer, youtube_url, language):
    """Create enhanced tasks with better error handling and validation"""

    transcript_task = Task(
        description=(
            f"Extract the complete, detailed transcript from: {youtube_url}. "
            f"Language: {language}. CRITICAL: Preserve ALL specific tool names, "
            "company names, technical terms, version numbers, and detailed explanations. "
            "Do not summarize or generalize - capture every specific detail mentioned. "
            "If extraction fails, provide a clear error message with details about what went wrong."
        ),
        expected_output=(
            "Complete transcript with ALL specific tool names, technical details, "
            "company names, version numbers, and exact quotes preserved. "
            "Include every specific recommendation and technical explanation. "
            "If extraction fails, provide ERROR: followed by detailed explanation."
        ),
        agent=transcriber,
        callback=lambda task: logger.info(
            f"Transcript task completed: {task.output[:100] if task.output else 'No output'}..."
        ),
    )

    blog_task = Task(
        description=(
            "Create a comprehensive, detailed blog article from the provided content. "
            "CRITICAL REQUIREMENTS: "
            "1. If the input starts with 'ERROR:', create an informative article about the video URL and explain the technical limitations "
            "2. If valid transcript is provided, PRESERVE ALL SPECIFIC INFORMATION: "
            "   - Include EVERY tool name, company name, and technical term mentioned "
            "   - Preserve all specific recommendations and winners in each category "
            "   - Include exact version numbers, technical specifications, and comparisons "
            "   - Maintain the original structure and categorization "
            "   - Include specific quotes and technical explanations "
            "   - Do NOT generalize or create vague statements "
            "3. If the video mentions 'Fabric wins AI category', write exactly that "
            "4. If specific tools are compared, include the comparison details "
            "5. Preserve all technical reasoning and decision criteria "
            "6. Include specific use cases and implementation details mentioned "
            "FORMAT: Use the exact categories and structure from the original content"
        ),
        expected_output=(
            "Either: Detailed blog article that reads like a comprehensive technical review, "
            "preserving every specific tool name, technical detail, comparison, and "
            "recommendation from the original video. Should include specific winners "
            "in each category with detailed explanations of why they won. "
            "OR: Informative article about the video with troubleshooting guidance if transcript extraction failed."
        ),
        agent=writer,
        context=[transcript_task],
        callback=lambda task: logger.info(
            f"Blog task completed: {len(task.output) if task.output else 0} characters"
        ),
    )

    logger.info("Enhanced tasks created successfully")
    return transcript_task, blog_task
