from src.agent import create_agents

def test_agent_creation():
    transcriber, writer = create_agents()
    
    assert transcriber.role == "Transcription Specialist"
    assert writer.role == "Blog Writer"
    assert len(transcriber.tools) == 1
    assert len(writer.tools) == 1