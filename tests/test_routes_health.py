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
    @patch('app.routes.health.psutil')
    def test_health_check_unhealthy(self, mock_psutil, mock_mongo, client):
        """Test health check when database is disconnected"""
        mock_mongo.is_connected.return_value = False

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

        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert data['database'] == 'disconnected'

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    @patch.dict('os.environ', {'LOKI_URL': 'http://loki:3100', 'FLASK_ENV': 'development'})
    def test_health_check_with_env_vars(self, mock_psutil, mock_mongo, client):
        """Test health check with environment variables set"""
        mock_mongo.is_connected.return_value = True

        mock_psutil.cpu_percent.return_value = 25.5
        mock_memory = MagicMock()
        mock_memory.percent = 45.2
        mock_memory.used = 4 * 1024 * 1024 * 1024
        mock_memory.total = 8 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 30 * 1024 * 1024 * 1024
        mock_disk.total = 100 * 1024 * 1024 * 1024
        mock_disk.free = 70 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk

        response = client.get('/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['loki_url'] == 'http://loki:3100'
        assert data['application']['environment'] == 'development'
        assert data['system']['cpu_percent'] == 25.5
        assert data['system']['memory_percent'] == 45.2

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_check_with_app_uptime(self, mock_psutil, mock_mongo, client, app):
        """Test health check with application uptime"""
        mock_mongo.is_connected.return_value = True

        mock_psutil.cpu_percent.return_value = 30.0
        mock_memory = MagicMock()
        mock_memory.percent = 50.0
        mock_memory.used = 4 * 1024 * 1024 * 1024
        mock_memory.total = 8 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 25 * 1024 * 1024 * 1024
        mock_disk.total = 100 * 1024 * 1024 * 1024
        mock_disk.free = 75 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk

        # Set start time to test uptime calculation
        import time
        with app.app_context():
            app.start_time = time.time() - 120  # 2 minutes ago

            response = client.get('/health')

            assert response.status_code == 200
            data = response.get_json()
            assert data['application']['uptime_seconds'] >= 119
            assert data['application']['uptime_seconds'] <= 121

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_check_exception(self, mock_psutil, mock_mongo, client):
        """Test health check when exception occurs"""
        mock_mongo.is_connected.side_effect = Exception("Database connection error")

        response = client.get('/health')

        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert 'error' in data
        assert 'Database connection error' in data['error']

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_check_psutil_exception(self, mock_psutil, mock_mongo, client):
        """Test health check when psutil raises exception"""
        mock_mongo.is_connected.return_value = True
        mock_psutil.cpu_percent.side_effect = Exception("CPU monitoring error")

        response = client.get('/health')

        assert response.status_code == 503
        data = response.get_json()
        assert data['status'] == 'unhealthy'
        assert 'error' in data

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_metrics_success(self, mock_psutil, mock_mongo, client):
        """Test health metrics endpoint success"""
        mock_mongo.is_connected.return_value = True

        mock_psutil.cpu_percent.return_value = 35.5
        mock_memory = MagicMock()
        mock_memory.percent = 65.2
        mock_memory.used = 8 * 1024 * 1024 * 1024
        mock_memory.total = 16 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 40 * 1024 * 1024 * 1024
        mock_disk.total = 100 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk

        response = client.get('/health-metrics')

        assert response.status_code == 200
        assert response.mimetype == 'text/plain'

        content = response.get_data(as_text=True)
        assert 'app_health_status 1' in content
        assert 'app_database_status 1' in content
        assert 'app_cpu_percent 35.5' in content
        assert 'app_memory_percent 65.2' in content
        assert f'app_memory_used_bytes {8 * 1024 * 1024 * 1024}' in content
        assert f'app_memory_total_bytes {16 * 1024 * 1024 * 1024}' in content
        assert 'app_disk_percent 40.0' in content

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_metrics_unhealthy(self, mock_psutil, mock_mongo, client):
        """Test health metrics endpoint when unhealthy"""
        mock_mongo.is_connected.return_value = False

        mock_psutil.cpu_percent.return_value = 85.0
        mock_memory = MagicMock()
        mock_memory.percent = 90.0
        mock_memory.used = 14 * 1024 * 1024 * 1024
        mock_memory.total = 16 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 90 * 1024 * 1024 * 1024
        mock_disk.total = 100 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk

        response = client.get('/health-metrics')

        assert response.status_code == 200  # Metrics endpoint returns 200 even when unhealthy
        assert response.mimetype == 'text/plain'

        content = response.get_data(as_text=True)
        assert 'app_health_status 0' in content
        assert 'app_database_status 0' in content
        assert 'app_cpu_percent 85.0' in content

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_metrics_with_uptime(self, mock_psutil, mock_mongo, client, app):
        """Test health metrics with uptime calculation"""
        mock_mongo.is_connected.return_value = True

        mock_psutil.cpu_percent.return_value = 40.0
        mock_memory = MagicMock()
        mock_memory.percent = 55.0
        mock_memory.used = 6 * 1024 * 1024 * 1024
        mock_memory.total = 12 * 1024 * 1024 * 1024
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 60 * 1024 * 1024 * 1024
        mock_disk.total = 200 * 1024 * 1024 * 1024
        mock_psutil.disk_usage.return_value = mock_disk

        import time
        with app.app_context():
            app.start_time = time.time() - 300  # 5 minutes ago

            response = client.get('/health-metrics')

            assert response.status_code == 200
            content = response.get_data(as_text=True)

            # Check uptime is approximately 300 seconds (allow for small timing variations)
            assert 'app_uptime_seconds 29' in content or 'app_uptime_seconds 30' in content

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_metrics_exception(self, mock_psutil, mock_mongo, client):
        """Test health metrics endpoint when exception occurs"""
        mock_mongo.is_connected.side_effect = Exception("Metrics error")

        response = client.get('/health-metrics')

        assert response.status_code == 503
        assert response.mimetype == 'text/plain'

        content = response.get_data(as_text=True)
        assert 'app_health_status 0' in content
        assert 'app_error' in content

    @patch('app.routes.health.mongo_manager')
    @patch('app.routes.health.psutil')
    def test_health_metrics_psutil_exception(self, mock_psutil, mock_mongo, client):
        """Test health metrics when psutil raises exception"""
        mock_mongo.is_connected.return_value = True
        mock_psutil.cpu_percent.side_effect = Exception("System monitoring error")

        response = client.get('/health-metrics')

        assert response.status_code == 503
        content = response.get_data(as_text=True)
        assert 'app_health_status 0' in content
        assert 'System monitoring error' in content