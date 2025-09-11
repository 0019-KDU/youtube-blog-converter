import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch


class TestLoadPerformance:
    """Performance tests for load handling"""

    def test_concurrent_user_registrations(self, client):
        """Test multiple concurrent user registrations"""
        def register_user(index):
            with patch('app.models.user.User') as mock_user_class:
                mock_user = Mock()
                mock_user.create_user.return_value = {
                    'success': True,
                    'user': {
                        '_id': f'user_{index}',
                        'username': f'testuser_{index}',
                        'email': f'test{index}@example.com'
                    }
                }
                mock_user_class.return_value = mock_user

                start_time = time.time()
                response = client.post('/auth/register', data={
                    'username': f'testuser_{index}',
                    'email': f'test{index}@example.com',
                    'password': 'password123'
                })
                end_time = time.time()

                return {
                    'status_code': response.status_code,
                    'duration': end_time - start_time,
                    'index': index
                }

        # Test with 10 concurrent registrations
        num_users = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_user, i)
                       for i in range(num_users)]
            results = [future.result() for future in as_completed(futures)]

        # Verify all registrations completed
        assert len(results) == num_users

        # Check response times are reasonable (under 5 seconds each)
        for result in results:
            assert result['status_code'] in [200, 302]
            assert result['duration'] < 5.0

        # Calculate average response time
        avg_duration = sum(result['duration']
                           for result in results) / len(results)
        print(f"Average registration time: {avg_duration:.3f} seconds")

        # Ensure average response time is under 2 seconds
        assert avg_duration < 2.0

    def test_concurrent_blog_generations(self, client):
        """Test multiple concurrent blog generations"""
        def generate_blog(index):
            with patch('app.services.auth_service.AuthService.get_current_user') as mock_auth, \
                    patch('app.services.blog_service.generate_blog_from_youtube') as mock_generate, \
                    patch('app.models.user.BlogPost') as mock_blog_class, \
                    patch('app.utils.security.store_large_data') as mock_store:

                mock_auth.return_value = {
                    '_id': f'user_{index}',
                    'username': f'testuser_{index}',
                    'email': f'test{index}@example.com'
                }

                # Simulate variable generation time
                time.sleep(0.1 + (index % 3) * 0.05)
                mock_generate.return_value = f'# Blog Post {index}\n\nThis is generated content for blog {index}.'

                mock_blog = Mock()
                mock_blog.create_post.return_value = {
                    '_id': f'post_{index}',
                    'title': f'Blog Post {index}',
                    'content': f'# Blog Post {index}\n\nContent...',
                    'user_id': f'user_{index}'
                }
                mock_blog_class.return_value = mock_blog

                mock_store.return_value = f'storage_key_{index}'

                start_time = time.time()
                response = client.post(
                    '/generate',
                    data={
                        'youtube_url': f'https://www.youtube.com/watch?v=test{index}',
                        'language': 'en'})
                end_time = time.time()

                return {
                    'status_code': response.status_code,
                    'duration': end_time - start_time,
                    'index': index,
                    'success': response.status_code == 200
                }

        # Test with 5 concurrent blog generations
        num_generations = 5
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_blog, i)
                       for i in range(num_generations)]
            results = [future.result() for future in as_completed(futures)]

        # Verify all generations completed successfully
        assert len(results) == num_generations
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) >= num_generations * \
            0.8  # At least 80% success rate

        # Check response times
        for result in successful_results:
            assert result['duration'] < 10.0  # Under 10 seconds

        avg_duration = sum(
            result['duration'] for result in successful_results) / len(successful_results)
        print(f"Average blog generation time: {avg_duration:.3f} seconds")

    def test_dashboard_load_with_many_posts(self, client, authenticated_user):
        """Test dashboard performance with many blog posts"""
        # Generate mock data for many posts
        num_posts = 100
        mock_posts = [
            {
                '_id': f'post_{i}',
                'title': f'Blog Post {i}',
                'created_at': f'2024-01-{(i % 30) + 1:02d}T00:00:00',
                'word_count': 500 + i * 10,
                'youtube_url': f'https://www.youtube.com/watch?v=test{i}',
                'video_id': f'test{i}'
            }
            for i in range(num_posts)
        ]

        with patch('app.models.user.BlogPost') as mock_blog_class:
            mock_blog = Mock()
            mock_blog.get_user_posts.return_value = mock_posts
            mock_blog_class.return_value = mock_blog

            start_time = time.time()
            response = client.get('/dashboard')
            end_time = time.time()

            assert response.status_code == 200
            duration = end_time - start_time

            # Dashboard should load in under 3 seconds even with many posts
            assert duration < 3.0
            print(
                f"Dashboard load time with {num_posts} posts: {
                    duration:.3f} seconds")

            # Verify pagination or reasonable display
            response_text = response.get_data(as_text=True)
            # Should show at least first few posts
            assert 'Blog Post 0' in response_text or 'Blog Post 1' in response_text

    def test_api_rate_limiting_performance(self, client, authenticated_user):
        """Test API performance under rate limiting"""
        def make_api_request(index):
            start_time = time.time()
            response = client.get('/health')
            end_time = time.time()

            return {
                'status_code': response.status_code,
                'duration': end_time - start_time,
                'index': index
            }

        # Make many rapid requests
        num_requests = 20
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_api_request, i)
                       for i in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]

        # Some requests might be rate limited, but successful ones should be
        # fast
        successful_results = [r for r in results if r['status_code'] == 200]

        if successful_results:
            avg_duration = sum(
                r['duration'] for r in successful_results) / len(successful_results)
            assert avg_duration < 1.0  # Successful requests should be under 1 second
            print(f"Average API response time: {avg_duration:.3f} seconds")
