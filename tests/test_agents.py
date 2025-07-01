import pytest
from unittest.mock import Mock, patch
from src.agent import create_agents

class TestCreateAgents:
    """Test cases for agent creation"""
    
    def test_create_agents_returns_two_agents(self):
        """Test that create_agents returns transcriber and writer agents"""
        with patch('src.agent.Agent') as mock_agent:
            mock_agent_instance = Mock()
            mock_agent.return_value = mock_agent_instance
            
            transcriber, writer = create_agents()
            
            assert transcriber is not None
            assert writer is not None
            assert mock_agent.call_count == 2
    
    def test_transcriber_agent_configuration(self):
        """Test transcriber agent is configured correctly"""
        with patch('src.agent.Agent') as mock_agent, \
             patch('src.agent.YouTubeTranscriptTool') as mock_tool:
            
            mock_agent_instance = Mock()
            mock_agent.return_value = mock_agent_instance
            mock_tool_instance = Mock()
            mock_tool.return_value = mock_tool_instance
            
            transcriber, writer = create_agents()
            
            # Check first call (transcriber)
            first_call = mock_agent.call_args_list[0]
            kwargs = first_call[1]
            
            assert kwargs['role'] == 'YouTube Video Transcriber'
            assert 'Extract accurate transcripts' in kwargs['goal']
            assert 'expert at extracting video transcripts' in kwargs['backstory']
            assert kwargs['verbose'] is True
            assert kwargs['memory'] is True
            assert kwargs['allow_delegation'] is False
    
    def test_writer_agent_configuration(self):
        """Test writer agent is configured correctly"""
        with patch('src.agent.Agent') as mock_agent, \
             patch('src.agent.YouTubeTranscriptTool'), \
             patch('src.agent.BlogGeneratorTool') as mock_blog_tool:
            
            mock_agent_instance = Mock()
            mock_agent.return_value = mock_agent_instance
            mock_blog_tool_instance = Mock()
            mock_blog_tool.return_value = mock_blog_tool_instance
            
            transcriber, writer = create_agents()
            
            # Check second call (writer)
            second_call = mock_agent.call_args_list[1]
            kwargs = second_call[1]
            
            assert kwargs['role'] == 'Blog Content Writer'
            assert 'Transform video transcripts' in kwargs['goal']
            assert 'professional content writer' in kwargs['backstory']
            assert kwargs['verbose'] is True
            assert kwargs['memory'] is True
            assert kwargs['allow_delegation'] is False
    
    def test_agents_have_correct_tools(self):
        """Test that agents are assigned correct tools"""
        with patch('src.agent.Agent') as mock_agent, \
             patch('src.agent.YouTubeTranscriptTool') as mock_transcript_tool, \
             patch('src.agent.BlogGeneratorTool') as mock_blog_tool:
            
            mock_agent_instance = Mock()
            mock_agent.return_value = mock_agent_instance
            
            create_agents()
            
            # Verify tools were created
            mock_transcript_tool.assert_called_once()
            mock_blog_tool.assert_called_once()
