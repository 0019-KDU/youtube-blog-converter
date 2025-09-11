import json
from unittest.mock import Mock, patch

import pytest


class TestHealthRoutes:
    """Test cases for health check routes"""
    
    def test_health_check_success(self, client, mock_mongodb_globally):
        """Test successful health check"""
        with patch('app.routes.health.mongo_manager') as mock_manager, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock system metrics
            mock_cpu.return_value = 25.5
            mock_memory.return_value = Mock(
                percent=60.0,
                used=8000000000,  # 8GB
                total=16000000000  # 16GB
            )
            mock_disk.return_value = Mock(
                used=500000000000,   # 500GB
                total=1000000000000, # 1TB
                free=500000000000    # 500GB free
            )
            
            # Mock database connection
            mock_manager.is_connected.return_value = True
            
            response = client.get('/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
            assert 'system' in data
            assert 'application' in data
    
    def test_health_check_database_disconnected(self, client):
        """Test health check with database disconnected"""
        with patch('app.routes.health.mongo_manager') as mock_manager, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock system metrics
            mock_cpu.return_value = 25.5
            mock_memory.return_value = Mock(percent=60.0, used=8000000000, total=16000000000)
            mock_disk.return_value = Mock(used=500000000000, total=1000000000000, free=500000000000)
            
            # Mock database disconnection
            mock_manager.is_connected.return_value = False
            
            response = client.get('/health')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
            assert data['database'] == 'disconnected'
    
    def test_health_check_exception(self, client):
        """Test health check with exception"""
        with patch('psutil.cpu_percent', side_effect=Exception("System error")):
            response = client.get('/health')
            
            assert response.status_code == 503
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
            assert 'error' in data
    
    def test_health_metrics(self, client, mock_mongodb_globally):
        """Test health metrics endpoint"""
        with patch('app.routes.health.mongo_manager') as mock_manager, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock system metrics
            mock_cpu.return_value = 30.0
            mock_memory.return_value = Mock(
                percent=70.0,
                used=7000000000,
                total=10000000000
            )
            mock_disk.return_value = Mock(
                used=400000000000,
                total=1000000000000
            )
            
            # Mock database connection
            mock_manager.is_connected.return_value = True
            
            response = client.get('/health-metrics')
            
            assert response.status_code == 200
            assert response.content_type == 'text/plain; charset=utf-8'
            assert b'app_health_status 1' in response.data
            assert b'app_database_status 1' in response.data
            assert b'app_cpu_percent 30.0' in response.data
    
    def test_health_metrics_database_error(self, client):
        """Test health metrics with database error"""
        with patch('app.routes.health.mongo_manager') as mock_manager, \
             patch('psutil.cpu_percent') as mock_cpu, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk:
            
            # Mock system metrics
            mock_cpu.return_value = 30.0
            mock_memory.return_value = Mock(percent=70.0, used=7000000000, total=10000000000)
            mock_disk.return_value = Mock(used=400000000000, total=1000000000000)
            
            # Mock database error
            mock_manager.is_connected.return_value = False
            
            response = client.get('/health-metrics')
            
            assert response.status_code == 200
            assert b'app_health_status 0' in response.data
            assert b'app_database_status 0' in response.data
    
    def test_health_metrics_exception(self, client):
        """Test health metrics with system exception"""
        with patch('psutil.cpu_percent', side_effect=Exception("CPU error")):
            response = client.get('/health-metrics')
            
            assert response.status_code == 503
            assert b'app_health_status 0' in response.data
            assert b'app_error' in response.data
