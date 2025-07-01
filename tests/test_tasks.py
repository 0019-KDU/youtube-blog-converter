import pytest
from unittest.mock import Mock, patch
from src.task import create_tasks

class TestCreateTasks:
    """Test cases for task creation"""
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing"""
        transcriber = Mock()
        writer = Mock()
        return transcriber, writer
    
    def test_create_tasks_returns_two_tasks(self, mock_agents):
        """Test that create_tasks returns transcript and blog tasks"""
        transcriber, writer = mock_agents
        youtube_url = "https://www.youtube.com/watch?v=test123"
        language = "en"
        
        with patch('src.task.Task') as mock_task:
            mock_task_instance = Mock()
            mock_task.return_value = mock_task_instance
            
            transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
            
            assert transcript_task is not None
            assert blog_task is not None
            assert mock_task.call_count == 2
    
    def test_transcript_task_configuration(self, mock_agents):
        """Test transcript task is configured correctly"""
        transcriber, writer = mock_agents
        youtube_url = "https://www.youtube.com/watch?v=test123"
        language = "en"
        
        with patch('src.task.Task') as mock_task:
            mock_task_instance = Mock()
            mock_task.return_value = mock_task_instance
            
            create_tasks(transcriber, writer, youtube_url, language)
            
            # Check first call (transcript task)
            first_call = mock_task.call_args_list[0]
            kwargs = first_call[1]
            
            assert youtube_url in kwargs['description']
            assert language in kwargs['description']
            assert 'Extract the complete transcript' in kwargs['description']
            assert 'complete, accurate transcript' in kwargs['expected_output']
            assert kwargs['agent'] == transcriber
    
    def test_blog_task_configuration(self, mock_agents):
        """Test blog task is configured correctly"""
        transcriber, writer = mock_agents
        youtube_url = "https://www.youtube.com/watch?v=test123"
        language = "en"
        
        with patch('src.task.Task') as mock_task:
            mock_task_instance = Mock()
            mock_task.return_value = mock_task_instance
            
            transcript_task, blog_task = create_tasks(transcriber, writer, youtube_url, language)
            
            # Check second call (blog task)
            second_call = mock_task.call_args_list[1]
            kwargs = second_call[1]
            
            assert 'comprehensive blog article' in kwargs['description']
            assert 'engaging title' in kwargs['description']
            assert 'Markdown' in kwargs['description']
            assert 'at least 800 words' in kwargs['description']
            assert kwargs['agent'] == writer
            assert transcript_task in kwargs['context']
    
    def test_task_descriptions_contain_requirements(self, mock_agents):
        """Test that task descriptions contain all required elements"""
        transcriber, writer = mock_agents
        youtube_url = "https://www.youtube.com/watch?v=test123"
        language = "fr"  # Test with different language
        
        with patch('src.task.Task') as mock_task:
            create_tasks(transcriber, writer, youtube_url, language)
            
            # Check transcript task requirements
            transcript_call = mock_task.call_args_list[0][1]
            assert 'meaningful dialogue' in transcript_call['description']
            assert 'properly formatted' in transcript_call['expected_output']
            
            # Check blog task requirements
            blog_call = mock_task.call_args_list[1][1]
            blog_desc = blog_call['description']
            assert 'engaging title' in blog_desc
            assert 'brief introduction' in blog_desc
            assert 'clear sections' in blog_desc
            assert 'detailed explanations' in blog_desc
            assert 'conclusion' in blog_desc
            assert 'Markdown' in blog_desc
    
    def test_different_languages_handled(self, mock_agents):
        """Test that different languages are properly handled"""
        transcriber, writer = mock_agents
        youtube_url = "https://www.youtube.com/watch?v=test123"
        
        languages = ["en", "es", "fr", "de"]
        
        for language in languages:
            with patch('src.task.Task') as mock_task:
                create_tasks(transcriber, writer, youtube_url, language)
                
                # Check that language is included in description
                first_call = mock_task.call_args_list[0]
                assert language in first_call[1]['description']
