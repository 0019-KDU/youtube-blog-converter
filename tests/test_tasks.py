# ✅ tests/test_task.py
from src.task import create_tasks
from src.agent import create_agents

def test_create_tasks():
    transcriber, writer = create_agents()
    transcript_task, blog_task = create_tasks(transcriber, writer, "https://youtu.be/test123", "en")
    assert "transcript" in transcript_task.description.lower()
    assert "blog" in blog_task.description.lower()
    assert transcript_task.agent == transcriber
    assert blog_task.agent == writer
    assert blog_task.context == [transcript_task]