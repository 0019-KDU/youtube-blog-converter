import os
import pytest
from unittest.mock import patch, MagicMock
import sys

class TestRunModule:
    
    @patch('run.create_application')  # Fixed function name
    @patch('run.validate_environment')
    @patch('run.setup_environment')
    def test_main_execution(self, mock_setup, mock_validate, mock_create_application):  # Fixed parameter name
        """Test main application execution"""
        import run
        
        mock_app = MagicMock()
        mock_create_application.return_value = mock_app  # Fixed mock name
        
        # Mock the run method to prevent actual server start
        mock_app.run = MagicMock()
        
        # Execute main with mocked app.run
        with patch.object(sys, 'exit'):
            try:
                run.main()
            except SystemExit:
                pass
        
        mock_setup.assert_called_once()
        mock_validate.assert_called_once()
        mock_create_application.assert_called_once()  # Fixed assert
    
    def test_validate_environment_missing_vars(self):
        """Test environment validation with missing variables"""
        import run
        
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit):
                run.validate_environment()
    
    def test_validate_environment_success(self):
        """Test successful environment validation"""
        import run
        
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'SUPADATA_API_KEY': 'test-key',
            'MONGODB_URI': 'mongodb://test'
        }):
            # Should not raise any exception
            run.validate_environment()
