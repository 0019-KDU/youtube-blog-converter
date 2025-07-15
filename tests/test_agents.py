import pytest
from unittest.mock import Mock, patch, MagicMock
import logging
from src.agent import create_agents

class TestCreateAgents:
    """Test cases for the create_agents function"""

    @patch('src.agent.Agent')
    def test_create_agents_success(self, mock_agent):
        """Test successful agent creation"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify
        assert transcriber is not None
        assert writer is not None
        assert mock_agent.call_count == 2
        
        # Verify agent configurations
        calls = mock_agent.call_args_list
        
        # Check transcriber agent
        transcriber_call = calls[0]
        assert transcriber_call[1]['role'] == 'YouTube Technical Content Extractor'
        assert 'Extract complete, detailed transcripts' in transcriber_call[1]['goal']
        assert transcriber_call[1]['verbose'] is True
        assert transcriber_call[1]['memory'] is False
        assert transcriber_call[1]['allow_delegation'] is False
        assert transcriber_call[1]['max_retry_limit'] == 1
        
        # Check writer agent
        writer_call = calls[1]
        assert writer_call[1]['role'] == 'Technical Blog Writer'
        assert 'Create detailed technical blog posts' in writer_call[1]['goal']
        assert writer_call[1]['verbose'] is True
        assert writer_call[1]['memory'] is False
        assert writer_call[1]['allow_delegation'] is False
        assert writer_call[1]['max_retry_limit'] == 1

    @patch('src.agent.Agent')
    def test_agent_tools_configuration(self, mock_agent):
        """Test that agents are configured with correct tools"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify tools are assigned
        calls = mock_agent.call_args_list
        
        # Check transcriber has YouTubeTranscriptTool
        transcriber_call = calls[0]
        transcriber_tools = transcriber_call[1]['tools']
        assert len(transcriber_tools) == 1
        assert transcriber_tools[0].__class__.__name__ == 'YouTubeTranscriptTool'
        
        # Check writer has BlogGeneratorTool
        writer_call = calls[1]
        writer_tools = writer_call[1]['tools']
        assert len(writer_tools) == 1
        assert writer_tools[0].__class__.__name__ == 'BlogGeneratorTool'

    @patch('src.agent.Agent')
    def test_agent_backstory_content(self, mock_agent):
        """Test agent backstory content for proper instructions"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify backstory content
        calls = mock_agent.call_args_list
        
        # Check transcriber backstory
        transcriber_backstory = calls[0][1]['backstory']
        assert 'expert at extracting technical content' in transcriber_backstory
        assert 'never generalize or summarize' in transcriber_backstory
        assert 'capture every specific detail' in transcriber_backstory
        assert 'handle errors gracefully' in transcriber_backstory
        
        # Check writer backstory
        writer_backstory = calls[1][1]['backstory']
        assert 'technical writer' in writer_backstory
        assert 'comprehensive, detailed blog posts' in writer_backstory
        assert 'never generalize' in writer_backstory
        assert 'preserve every tool name' in writer_backstory

    @patch('src.agent.Agent')
    def test_agent_step_callbacks(self, mock_agent):
        """Test that step callbacks are properly configured"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify step callbacks exist
        calls = mock_agent.call_args_list
        
        # Check transcriber callback
        transcriber_callback = calls[0][1]['step_callback']
        assert transcriber_callback is not None
        assert callable(transcriber_callback)
        
        # Check writer callback
        writer_callback = calls[1][1]['step_callback']
        assert writer_callback is not None
        assert callable(writer_callback)

    @patch('src.agent.Agent')
    @patch('src.agent.logger')
    def test_agent_creation_logging(self, mock_logger, mock_agent):
        """Test that agent creation is properly logged"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify logging
        mock_logger.info.assert_called_with("Enhanced agents created successfully")

    @patch('src.agent.Agent')
    def test_agent_memory_disabled(self, mock_agent):
        """Test that memory is disabled for both agents"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify memory is disabled
        calls = mock_agent.call_args_list
        
        for call in calls:
            assert call[1]['memory'] is False

    @patch('src.agent.Agent')
    def test_agent_delegation_disabled(self, mock_agent):
        """Test that delegation is disabled for both agents"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify delegation is disabled
        calls = mock_agent.call_args_list
        
        for call in calls:
            assert call[1]['allow_delegation'] is False

    @patch('src.agent.Agent')
    def test_agent_retry_limit_configuration(self, mock_agent):
        """Test that retry limit is properly configured"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify retry limit
        calls = mock_agent.call_args_list
        
        for call in calls:
            assert call[1]['max_retry_limit'] == 1

    @patch('src.agent.Agent')
    def test_agent_verbose_mode_enabled(self, mock_agent):
        """Test that verbose mode is enabled for both agents"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify verbose mode
        calls = mock_agent.call_args_list
        
        for call in calls:
            assert call[1]['verbose'] is True

    @patch('src.agent.Agent')
    def test_agent_roles_are_unique(self, mock_agent):
        """Test that both agents have unique roles"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify unique roles
        calls = mock_agent.call_args_list
        
        transcriber_role = calls[0][1]['role']
        writer_role = calls[1][1]['role']
        
        assert transcriber_role != writer_role
        assert transcriber_role == 'YouTube Technical Content Extractor'
        assert writer_role == 'Technical Blog Writer'

    @patch('src.agent.Agent')
    def test_agent_goals_are_specific(self, mock_agent):
        """Test that agent goals are specific and detailed"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify specific goals
        calls = mock_agent.call_args_list
        
        transcriber_goal = calls[0][1]['goal']
        writer_goal = calls[1][1]['goal']
        
        # Transcriber goal should mention extraction and technical terms
        assert 'Extract complete, detailed transcripts' in transcriber_goal
        assert 'technical terms' in transcriber_goal
        assert 'tool names' in transcriber_goal
        
        # Writer goal should mention blog posts and details
        assert 'Create detailed technical blog posts' in writer_goal
        assert 'preserve every specific detail' in writer_goal

    @patch('src.agent.Agent')
    def test_agent_import_dependencies(self, mock_agent):
        """Test that required tools are properly imported"""
        # This test verifies the import statements work correctly
        from src.tool import YouTubeTranscriptTool, BlogGeneratorTool
        
        # Verify tools can be instantiated
        youtube_tool = YouTubeTranscriptTool()
        blog_tool = BlogGeneratorTool()
        
        assert youtube_tool is not None
        assert blog_tool is not None

    @patch('src.agent.Agent')
    def test_create_agents_returns_tuple(self, mock_agent):
        """Test that create_agents returns a tuple of two agents"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        result = create_agents()
        
        # Verify return type
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        transcriber, writer = result
        assert transcriber is not None
        assert writer is not None

    @patch('src.agent.Agent')
    def test_agent_error_handling_configuration(self, mock_agent):
        """Test that agents are configured for proper error handling"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        # Execute
        transcriber, writer = create_agents()
        
        # Verify error handling mentioned in backstory
        calls = mock_agent.call_args_list
        
        transcriber_backstory = calls[0][1]['backstory']
        assert 'handle errors gracefully' in transcriber_backstory
        assert 'clear feedback when extraction fails' in transcriber_backstory

    @patch('src.agent.Agent')
    def test_step_callback_functionality(self, mock_agent):
        """Test that step callbacks execute without errors"""
        # Setup
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        
        with patch('src.agent.logger') as mock_logger:
            # Execute
            transcriber, writer = create_agents()
            
            # Get callbacks
            calls = mock_agent.call_args_list
            transcriber_callback = calls[0][1]['step_callback']
            writer_callback = calls[1][1]['step_callback']
            
            # Test callback execution
            mock_step = Mock()
            transcriber_callback(mock_step)
            writer_callback(mock_step)
            
            # Verify logging calls
            assert mock_logger.info.call_count >= 2
