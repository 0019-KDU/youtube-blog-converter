import os
from dotenv import load_dotenv
from crewai import Crew, Process

# Load environment variables
load_dotenv()

# Use absolute imports
from src.agent import create_agents
from src.task import create_tasks
from src.tool import PDFTool

def generate_blog_from_youtube(youtube_url):
    """Generate blog article from YouTube video URL"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI API key not found. Please set OPENAI_API_KEY in .env file")
    
    # Set API key in environment
    os.environ["OPENAI_API_KEY"] = api_key

    # Create agents and tasks
    transcriber, writer = create_agents()
    transcript_task, blog_task = create_tasks(transcriber, writer)
    
    # Set up crew
    crew = Crew(
        agents=[transcriber, writer],
        tasks=[transcript_task, blog_task],
        process=Process.sequential
    )

    try:
        # Execute crew
        result = crew.kickoff(inputs={"youtube_url": youtube_url})
    except Exception as e:
        raise RuntimeError(f"Error during Crew execution: {e}")

    # Get blog content
    blog_output = blog_task.output.raw.strip()
    
    # Generate PDF
    pdf_path = "blog_article.pdf"
    pdf_tool = PDFTool()
    try:
        pdf_tool._run(content=blog_output, output_path=pdf_path)
    except Exception as e:
        print(f"PDF generation warning: {e}")
    
    return blog_output, pdf_path

# Original CLI main function
def cli_main():
    """Command line interface for the application"""
    # Get user inputs
    youtube_url = input("Enter YouTube video URL: ").strip()

    try:
        blog_output, pdf_path = generate_blog_from_youtube(youtube_url)
        
        print("\nGenerated blog article:")
        print(blog_output[:200] + "...\n")
        print(f"PDF saved to {pdf_path}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    cli_main()