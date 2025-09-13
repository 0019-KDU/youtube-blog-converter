import datetime
from unittest.mock import MagicMock, Mock, patch

from bson import ObjectId


class TestDatabaseOperations:
    """Integration tests for database operations"""

    def test_user_crud_operations(self, mock_mongodb_globally):
        """Test complete CRUD operations for users"""
        with patch('app.models.user.mongo_manager') as mock_manager:
            mock_collection = Mock()
            mock_manager.get_collection.return_value = mock_collection

            from app.models.user import User

            user = User()

            # Test create - Mock sequence: first call returns None (no existing
            # user), second call returns the created user
            created_user = {
                '_id': ObjectId(),
                'username': 'testuser',
                'email': 'test@example.com',
                'password_hash': 'hashed',
                'created_at': datetime.datetime.now(datetime.UTC),
                'updated_at': datetime.datetime.now(datetime.UTC),
                'is_active': True
            }
            # First call: no existing user, second call: return created user
            mock_collection.find_one.side_effect = [None, created_user]
            mock_collection.insert_one.return_value.inserted_id = created_user['_id']

            result = user.create_user(
                'testuser', 'test@example.com', 'password123')
            assert result['success'] is True

    def test_blog_post_crud_operations(self, mock_mongodb_globally):
        """Test complete CRUD operations for blog posts"""
        from app.models.user import BlogPost

        user_id = ObjectId()
        post_id = ObjectId()

        with patch.object(BlogPost, 'get_collection') as mock_collection:
            mock_coll = Mock()
            mock_collection.return_value = mock_coll

            blog_post = BlogPost()

            # Test create
            mock_coll.insert_one.return_value.inserted_id = post_id
            result = blog_post.create_post(
                user_id=str(user_id),
                youtube_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                title='Test Post',
                content='# Test\n\nContent',
                video_id='dQw4w9WgXcQ'
            )
            assert result is not None
            assert '_id' in result

            # Test read
            mock_coll.find_one.return_value = {
                '_id': post_id,
                'user_id': str(user_id),
                'title': 'Test Post',
                'content': '# Test\n\nContent'
            }
            result = blog_post.get_post_by_id(str(post_id), str(user_id))
            assert result is not None
            assert result['title'] == 'Test Post'

            # Test get user posts - Create proper mock cursor
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.skip.return_value = [
                {'_id': post_id, 'user_id': str(user_id), 'title': 'Test Post'}
            ]
            mock_coll.find.return_value = mock_cursor

            result = blog_post.get_user_posts(str(user_id))
            assert len(result) == 1
            assert result[0]['title'] == 'Test Post'

            # Test delete
            mock_coll.delete_one.return_value.deleted_count = 1
            result = blog_post.delete_post(str(post_id), str(user_id))
            assert result is True

            # Test count
            mock_coll.count_documents.return_value = 5
            result = blog_post.get_posts_count(str(user_id))
            assert result == 5

    def test_database_connection_error_handling(self, mock_mongodb_globally):
        """Test database connection error handling"""
        from app.models.user import User

        with patch.object(User, 'get_collection') as mock_collection:
            mock_collection.side_effect = Exception("Connection failed")

            user = User()
            result = user.create_user(
                'testuser', 'test@example.com', 'password123')

            assert result['success'] is False
            assert 'error' in result['message'].lower()
