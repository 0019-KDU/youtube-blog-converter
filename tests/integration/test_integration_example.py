import pytest
import requests
from app import app
from auth.models import User
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestYoutubeBlogIntegration:
    """Integration tests for YouTube to blog conversion workflow"""

    def test_complete_blog_generation_workflow(self, client, mock_mongo_connection):
        """Test the complete workflow from YouTube URL to blog generation"""
        # Mock user authentication
        with client.session_transaction() as sess:
            sess["access_token"] = "test_token"
            sess["user_id"] = "test_user_id"

        # Mock the transcript and blog generation
        with patch("src.tool.get_transcript_from_url") as mock_transcript, patch(
            "src.tool.generate_blog_from_transcript"
        ) as mock_blog:

            mock_transcript.return_value = "Sample transcript content about AI tools"
            mock_blog.return_value = "# AI Tools Blog\n\nThis is generated content"

            # Mock MongoDB save operation
            mock_mongo_connection["collection"].insert_one.return_value = Mock(
                inserted_id="test_blog_id"
            )

            # Test the complete workflow
            response = client.post(
                "/generate",
                data={
                    "youtube_url": "https://www.youtube.com/watch?v=test123",
                    "style": "technical",
                },
            )

            # Verify the workflow completed successfully
            assert response.status_code == 200
            mock_transcript.assert_called_once()
            mock_blog.assert_called_once()

    def test_user_registration_and_blog_generation(self, client, mock_mongo_connection):
        """Test user registration followed by blog generation"""
        # Mock user registration
        mock_mongo_connection["collection"].find_one.return_value = None
        mock_mongo_connection["collection"].insert_one.return_value = Mock(
            inserted_id="new_user_id"
        )

        # Register a new user
        response = client.post(
            "/auth/register",
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
            },
        )

        assert response.status_code == 302  # Redirect after successful registration

        # Login and generate blog
        with patch("src.tool.get_transcript_from_url") as mock_transcript, patch(
            "src.tool.generate_blog_from_transcript"
        ) as mock_blog:

            mock_transcript.return_value = "Sample content"
            mock_blog.return_value = "# Generated Blog"

            # Mock login
            mock_mongo_connection["collection"].find_one.return_value = {
                "_id": "new_user_id",
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
            }

            login_response = client.post(
                "/auth/login", data={"username": "testuser", "password": "testpass123"}
            )

            assert login_response.status_code == 302

            # Generate blog
            blog_response = client.post(
                "/generate",
                data={
                    "youtube_url": "https://www.youtube.com/watch?v=test456",
                    "style": "casual",
                },
            )

            assert blog_response.status_code == 200

    def test_database_operations_integration(self, mock_mongo_connection):
        """Test database operations integration"""
        from auth.models import User, BlogPost

        # Test user creation and retrieval
        user_data = {
            "username": "integrationuser",
            "email": "integration@test.com",
            "password_hash": "hashed_password",
        }

        # Mock user creation
        mock_mongo_connection["collection"].find_one.return_value = None
        mock_mongo_connection["collection"].insert_one.return_value = Mock(
            inserted_id="integration_user_id"
        )

        user = User.create_user(user_data)
        assert user is not None

        # Test blog post creation
        blog_data = {
            "user_id": "integration_user_id",
            "title": "Integration Test Blog",
            "content": "# Test Content",
            "youtube_url": "https://www.youtube.com/watch?v=integration",
            "video_id": "integration",
        }

        mock_mongo_connection["collection"].insert_one.return_value = Mock(
            inserted_id="integration_blog_id"
        )

        blog = BlogPost.create_blog_post(blog_data)
        assert blog is not None

    @pytest.mark.slow
    def test_api_rate_limiting_integration(self, client):
        """Test API rate limiting behavior"""
        # This would test actual rate limiting if implemented
        with client.session_transaction() as sess:
            sess["access_token"] = "test_token"
            sess["user_id"] = "test_user_id"

        # Make multiple requests to test rate limiting
        responses = []
        for i in range(5):
            response = client.get("/dashboard")
            responses.append(response.status_code)

        # All requests should succeed in test environment
        assert all(status == 200 for status in responses)
