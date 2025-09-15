import pytest
from unittest.mock import patch, MagicMock

class TestHealthRoutes:
    
    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_check_healthy(self, mock_psutil, mock_mongo, client):
        """Test health check when system is healthy"""
        mock_mongo.is_connected.return_value = True
        
        mock_psutil.cpu_percent.return_value = 50.0
        mock_memory = MagicMock()
        mock_memory.percent = 60.0
        mock_memory.used = 8 * 1024 * 1024 * 1024
        mock_memory.total = 16 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = MagicMock()
        mock_disk.used = 50 * 1024 * 1024 * 1024
        mock_disk.total = 100 * 1024 * 1024 * 1024
        mock_disk.free = 50 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['database'] == 'connected'
    
    @patch('app.routes.health.mongo_manager')
    def test_health_check_unhealthy(self, mock_mongo, client):
        """Test health check when database is disconnected"""
        mock_mongo.is_connected.return_value = False
        
        response = client.get('/health')
        
        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert data['database'] == 'disconnected'