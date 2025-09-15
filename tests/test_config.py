import pytest
import os

class TestConfiguration:
    
    def test_config_loading(self):
        """Test configuration loading"""
        from app.config import Config
        
        config = Config()
        
        assert config.SECRET_KEY is not None
        assert config.JWT_SECRET_KEY is not None
        assert config.MONGODB_URI is not None
    
    def test_development_config(self):
        """Test development configuration"""
        from app.config import DevelopmentConfig
        
        config = DevelopmentConfig()
        
        assert config.DEBUG is True
        assert config.FLASK_ENV == 'development'
    
    def test_production_config(self):
        """Test production configuration"""
        from app.config import ProductionConfig
        
        config = ProductionConfig()
        
        assert config.DEBUG is False
        assert config.FLASK_ENV == 'production'
        assert config.SESSION_COOKIE_SECURE is True