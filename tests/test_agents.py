# ✅ tests/test_agent.py
from src.agent import create_agents

def test_create_agents():
    transcriber, writer = create_agents()
    assert transcriber.role == 'YouTube Video Transcriber'
    assert writer.role == 'Blog Content Writer'
    assert not transcriber.allow_delegation
    assert not writer.allow_delegation