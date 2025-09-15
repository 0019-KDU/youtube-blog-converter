import pytest
from unittest.mock import patch, MagicMock

class TestAppFactory:
    
    def test_create_app(self):
        """Test Flask app creation"""
        from app import create_app
        
        app = create_app()
        
        assert app is not None
        assert app.config['SECRET_KEY'] is not None
        assert app.config['JWT_SECRET_KEY'] is not None
        assert 'temp_storage' in dir(app)
    
    def test_app_blueprints(self, app):
        """Test that all blueprints are registered"""
        blueprints = [bp.name for bp in app.blueprints.values()]
        
        assert 'auth' in blueprints
        assert 'blog' in blueprints
        assert 'health' in blueprints
    
    def test_error_handlers(self, client):
        """Test error handlers"""
        # Test 404 handler
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        
        # Test 401 handler (will redirect)
        with patch('app.routes.blog.AuthService.get_current_user', return_value=None):
            response = client.get('/generate-page')
            assert response.status_code == 302
    
    def test_template_filters(self, app):
        """Test custom template filters"""
        # Test nl2br filter
        nl2br = app.jinja_env.filters['nl2br']
        assert nl2br('line1\nline2') == 'line1<br>line2'
        assert nl2br(None) == ''
    
    def test_template_globals(self, app):
        """Test template global functions"""
        with app.test_request_context():
            # Test format_date
            format_date = app.jinja_env.globals['format_date']
            result = format_date()
            assert result is not None
            
            # Test moment
            moment = app.jinja_env.globals['moment']
            mock_moment = moment()
            assert hasattr(mock_moment, 'format')
