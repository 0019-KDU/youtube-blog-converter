import datetime
import os
import pytest
from unittest.mock import MagicMock, Mock, patch

from bson import ObjectId

# Ensure app directory is in path before any imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.user import BlogPost


class TestBlogPost:
    """Comprehensive test suite for BlogPost model"""

    @pytest.fixture
    def blog_post_model(self):
        """Create BlogPost model instance for testing"""
        return BlogPost()

    @pytest.fixture
    def sample_blog_post_data(self):
        """Sample blog post data for testing"""
        return {
            'user_id': ObjectId(),
            'youtube_url': 'https://youtube.com/watch?v=dQw4w9WgXcQ',
            'title': 'Test Blog Post Title',
            'content': 'This is a comprehensive test blog post content that demonstrates various features and functionality of our blogging system.',
            'video_id': 'dQw4w9WgXcQ'
        }

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing"""
        return ObjectId()

    @pytest.fixture
    def sample_post_id(self):
        """Sample post ID for testing"""
        return ObjectId()

    def test_blog_post_initialization(self, blog_post_model):
        """Test BlogPost model initialization"""
        assert blog_post_model.collection_name == "blog_posts"
        assert hasattr(blog_post_model, 'get_collection')

    @pytest.mark.unit
    def test_create_post_success(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test successful blog post creation"""
        # Ensure clean mock state
        mock_mongodb_globally['reset']()

        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test creation
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )

        # Assertions
        assert result is not None
        assert result['title'] == sample_blog_post_data['title']
        assert result['content'] == sample_blog_post_data['content']
        assert result['youtube_url'] == sample_blog_post_data['youtube_url']
        assert result['video_id'] == sample_blog_post_data['video_id']
        assert 'word_count' in result
        assert result['word_count'] == len(sample_blog_post_data['content'].split())
        assert 'created_at' in result
        assert 'updated_at' in result
        assert '_id' in result
        assert 'user_id' in result

        # Verify collection was called with correct data
        mock_collection.insert_one.assert_called_once()
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args['title'] == sample_blog_post_data['title']
        assert call_args['content'] == sample_blog_post_data['content']

    @pytest.mark.unit
    def test_create_post_with_string_user_id(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test blog post creation with string user ID"""
        # Ensure clean mock state
        mock_mongodb_globally['reset']()

        # Configure mock with complete isolation
        mock_collection = mock_mongodb_globally['collection']

        # Setup mock response
        post_id = ObjectId()
        mock_result = Mock()
        mock_result.inserted_id = post_id
        mock_collection.insert_one.return_value = mock_result

        # Test with string user_id
        string_user_id = str(sample_blog_post_data['user_id'])
        result = blog_post_model.create_post(
            user_id=string_user_id,
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )

        # More robust assertions with detailed error messages
        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), f"Result should be dict, got {type(result)}"
        assert 'user_id' in result, f"Result missing 'user_id' key: {result}"
        assert result['user_id'] == string_user_id, f"Expected user_id={string_user_id}, got {result.get('user_id')}"
        assert '_id' in result, f"Result missing '_id' key: {result}"
        assert 'title' in result, f"Result missing 'title' key: {result}"
        assert 'content' in result, f"Result missing 'content' key: {result}"

        # Verify insert was called once
        mock_collection.insert_one.assert_called_once()

    @pytest.mark.unit
    def test_create_post_database_error(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test blog post creation with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.insert_one.side_effect = Exception("Database connection error")

        # Test creation with error
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )

        # Should return None on error
        assert result is None

    @pytest.mark.unit
    def test_create_post_insert_failure(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test blog post creation when insert fails"""
        # Configure mock to return None inserted_id
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = None
        mock_collection.insert_one.return_value = mock_result

        # Test creation
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )

        # Should return None when insert fails
        assert result is None

    @pytest.mark.unit
    def test_get_user_posts_success(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test successful retrieval of user posts"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        sample_posts = [
            {
                '_id': ObjectId(),
                'user_id': sample_user_id,
                'title': 'First Post',
                'content': 'First post content',
                'created_at': datetime.datetime.now(datetime.UTC)
            },
            {
                '_id': ObjectId(),
                'user_id': sample_user_id,
                'title': 'Second Post',
                'content': 'Second post content',
                'created_at': datetime.datetime.now(datetime.UTC)
            }
        ]

        # Configure the mock chain
        mock_find = Mock()
        mock_sort = Mock()
        mock_limit = Mock()
        mock_skip = Mock()

        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = mock_sort
        mock_sort.limit.return_value = mock_limit
        mock_limit.skip.return_value = sample_posts

        # Test retrieval
        result = blog_post_model.get_user_posts(sample_user_id)

        # Assertions
        assert len(result) == 2
        assert all(isinstance(str(post['_id']), str) for post in result)
        assert all(isinstance(str(post['user_id']), str) for post in result)
        assert result[0]['title'] == 'First Post'
        assert result[1]['title'] == 'Second Post'

        # Verify correct method calls
        mock_collection.find.assert_called_once_with({'user_id': sample_user_id})
        mock_find.sort.assert_called_once_with('created_at', -1)
        mock_sort.limit.assert_called_once_with(50)
        mock_limit.skip.assert_called_once_with(0)

    @pytest.mark.unit
    def test_get_user_posts_with_pagination(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test retrieval of user posts with pagination parameters"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_find = Mock()
        mock_sort = Mock()
        mock_limit = Mock()
        mock_skip = Mock()

        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = mock_sort
        mock_sort.limit.return_value = mock_limit
        mock_limit.skip.return_value = []

        # Test with custom pagination
        result = blog_post_model.get_user_posts(sample_user_id, limit=10, skip=5)

        # Verify pagination parameters
        mock_sort.limit.assert_called_once_with(10)
        mock_limit.skip.assert_called_once_with(5)

    @pytest.mark.unit
    def test_get_user_posts_with_string_id(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test retrieval of user posts with string user ID"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_find = Mock()
        mock_sort = Mock()
        mock_limit = Mock()
        mock_skip = Mock()

        mock_collection.find.return_value = mock_find
        mock_find.sort.return_value = mock_sort
        mock_sort.limit.return_value = mock_limit
        mock_limit.skip.return_value = []

        # Test with string user_id
        string_user_id = str(sample_user_id)
        result = blog_post_model.get_user_posts(string_user_id)

        # Verify ObjectId conversion
        mock_collection.find.assert_called_once_with({'user_id': sample_user_id})

    @pytest.mark.unit
    def test_get_user_posts_database_error(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test get_user_posts with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.find.side_effect = Exception("Database error")

        # Test retrieval with error
        result = blog_post_model.get_user_posts(sample_user_id)

        # Should return empty list on error
        assert result == []

    @pytest.mark.unit
    def test_get_post_by_id_success(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test successful retrieval of post by ID"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        sample_post = {
            '_id': sample_post_id,
            'user_id': sample_user_id,
            'title': 'Test Post',
            'content': 'Test content',
            'created_at': datetime.datetime.now(datetime.UTC)
        }
        mock_collection.find_one.return_value = sample_post

        # Test retrieval
        result = blog_post_model.get_post_by_id(sample_post_id)

        # Assertions
        assert result is not None
        assert isinstance(result['_id'], str)
        assert isinstance(result['user_id'], str)
        assert result['title'] == 'Test Post'
        mock_collection.find_one.assert_called_once_with({'_id': sample_post_id})

    @pytest.mark.unit
    def test_get_post_by_id_with_user_id(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test retrieval of post by ID with user ID filter"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        sample_post = {
            '_id': sample_post_id,
            'user_id': sample_user_id,
            'title': 'Test Post',
            'content': 'Test content'
        }
        mock_collection.find_one.return_value = sample_post

        # Test retrieval with user_id
        result = blog_post_model.get_post_by_id(sample_post_id, sample_user_id)

        # Verify query includes user_id
        expected_query = {'_id': sample_post_id, 'user_id': sample_user_id}
        mock_collection.find_one.assert_called_once_with(expected_query)

    @pytest.mark.unit
    def test_get_post_by_id_with_string_ids(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test retrieval of post by ID with string IDs"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.find_one.return_value = None

        # Test with string IDs
        string_post_id = str(sample_post_id)
        string_user_id = str(sample_user_id)
        result = blog_post_model.get_post_by_id(string_post_id, string_user_id)

        # Verify ObjectId conversion
        expected_query = {'_id': sample_post_id, 'user_id': sample_user_id}
        mock_collection.find_one.assert_called_once_with(expected_query)

    @pytest.mark.unit
    def test_get_post_by_id_not_found(self, blog_post_model, sample_post_id, mock_mongodb_globally):
        """Test retrieval of non-existent post"""
        # Configure mock to return None
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.find_one.return_value = None

        # Test retrieval
        result = blog_post_model.get_post_by_id(sample_post_id)

        # Should return None
        assert result is None

    @pytest.mark.unit
    def test_get_post_by_id_database_error(self, blog_post_model, sample_post_id, mock_mongodb_globally):
        """Test get_post_by_id with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.find_one.side_effect = Exception("Database error")

        # Test retrieval with error
        result = blog_post_model.get_post_by_id(sample_post_id)

        # Should return None on error
        assert result is None

    @pytest.mark.unit
    def test_update_post_success(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test successful post update"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        # Test update
        update_data = {'title': 'Updated Title', 'content': 'Updated content'}
        result = blog_post_model.update_post(sample_post_id, sample_user_id, update_data)

        # Assertions
        assert result is True
        
        # Verify update_one was called correctly
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        
        # Check query
        query = call_args[0][0]
        assert query['_id'] == sample_post_id
        assert query['user_id'] == sample_user_id
        
        # Check update data includes timestamp
        update_dict = call_args[0][1]['$set']
        assert 'updated_at' in update_dict
        assert update_dict['title'] == 'Updated Title'
        assert update_dict['content'] == 'Updated content'

    @pytest.mark.unit
    def test_update_post_with_string_ids(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test post update with string IDs"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        # Test with string IDs
        string_post_id = str(sample_post_id)
        string_user_id = str(sample_user_id)
        update_data = {'title': 'Updated Title'}
        result = blog_post_model.update_post(string_post_id, string_user_id, update_data)

        # Verify ObjectId conversion
        call_args = mock_collection.update_one.call_args[0][0]
        assert call_args['_id'] == sample_post_id
        assert call_args['user_id'] == sample_user_id

    @pytest.mark.unit
    def test_update_post_no_changes(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test post update when no documents are modified"""
        # Configure mock to return 0 modified count
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result

        # Test update
        update_data = {'title': 'Updated Title'}
        result = blog_post_model.update_post(sample_post_id, sample_user_id, update_data)

        # Should return False when no documents modified
        assert result is False

    @pytest.mark.unit
    def test_update_post_database_error(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test post update with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.update_one.side_effect = Exception("Database error")

        # Test update with error
        update_data = {'title': 'Updated Title'}
        result = blog_post_model.update_post(sample_post_id, sample_user_id, update_data)

        # Should return False on error
        assert result is False

    @pytest.mark.unit
    def test_delete_post_success(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test successful post deletion"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        # Test deletion
        result = blog_post_model.delete_post(sample_post_id, sample_user_id)

        # Assertions
        assert result is True
        
        # Verify delete_one was called correctly
        expected_query = {'_id': sample_post_id, 'user_id': sample_user_id}
        mock_collection.delete_one.assert_called_once_with(expected_query)

    @pytest.mark.unit
    def test_delete_post_with_string_ids(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test post deletion with string IDs"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result

        # Test with string IDs
        string_post_id = str(sample_post_id)
        string_user_id = str(sample_user_id)
        result = blog_post_model.delete_post(string_post_id, string_user_id)

        # Verify ObjectId conversion
        expected_query = {'_id': sample_post_id, 'user_id': sample_user_id}
        mock_collection.delete_one.assert_called_once_with(expected_query)

    @pytest.mark.unit
    def test_delete_post_not_found(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test deletion of non-existent post"""
        # Configure mock to return 0 deleted count
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result

        # Test deletion
        result = blog_post_model.delete_post(sample_post_id, sample_user_id)

        # Should return False when no documents deleted
        assert result is False

    @pytest.mark.unit
    def test_delete_post_database_error(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test post deletion with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.delete_one.side_effect = Exception("Database error")

        # Test deletion with error
        result = blog_post_model.delete_post(sample_post_id, sample_user_id)

        # Should return False on error
        assert result is False

    @pytest.mark.unit
    def test_get_posts_count_success(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test successful retrieval of posts count"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.count_documents.return_value = 5

        # Test count retrieval
        result = blog_post_model.get_posts_count(sample_user_id)

        # Assertions
        assert result == 5
        mock_collection.count_documents.assert_called_once_with({'user_id': sample_user_id})

    @pytest.mark.unit
    def test_get_posts_count_with_string_id(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test posts count with string user ID"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.count_documents.return_value = 3

        # Test with string user_id
        string_user_id = str(sample_user_id)
        result = blog_post_model.get_posts_count(string_user_id)

        # Verify ObjectId conversion
        mock_collection.count_documents.assert_called_once_with({'user_id': sample_user_id})

    @pytest.mark.unit
    def test_get_posts_count_database_error(self, blog_post_model, sample_user_id, mock_mongodb_globally):
        """Test get_posts_count with database error"""
        # Configure mock to raise exception
        mock_collection = mock_mongodb_globally['collection']
        mock_collection.count_documents.side_effect = Exception("Database error")

        # Test count with error
        result = blog_post_model.get_posts_count(sample_user_id)

        # Should return 0 on error
        assert result == 0

    @pytest.mark.unit
    def test_word_count_calculation(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test that word count is calculated correctly"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test with specific content
        content = "This is a test content with exactly ten words here"
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=content,
            video_id=sample_blog_post_data['video_id']
        )

        # Verify word count
        assert result['word_count'] == 10

    @pytest.mark.unit
    def test_timestamps_added_on_creation(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test that timestamps are added during post creation"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test creation
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )

        # Verify timestamps exist and are datetime objects
        assert 'created_at' in result
        assert 'updated_at' in result
        assert isinstance(result['created_at'], datetime.datetime)
        assert isinstance(result['updated_at'], datetime.datetime)

    @pytest.mark.unit
    def test_updated_timestamp_added_on_update(self, blog_post_model, sample_post_id, sample_user_id, mock_mongodb_globally):
        """Test that updated timestamp is added during post update"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result

        # Test update
        update_data = {'title': 'Updated Title'}
        blog_post_model.update_post(sample_post_id, sample_user_id, update_data)

        # Verify updated_at timestamp was added
        call_args = mock_collection.update_one.call_args[0][1]['$set']
        assert 'updated_at' in call_args
        assert isinstance(call_args['updated_at'], datetime.datetime)

    @pytest.mark.integration
    def test_end_to_end_blog_post_lifecycle(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test complete blog post lifecycle: create, read, update, delete"""
        mock_collection = mock_mongodb_globally['collection']
        post_id = ObjectId()
        user_id = sample_blog_post_data['user_id']

        # Mock create
        mock_result = Mock()
        mock_result.inserted_id = post_id
        mock_collection.insert_one.return_value = mock_result

        # Test create
        created_post = blog_post_model.create_post(
            user_id=user_id,
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=sample_blog_post_data['content'],
            video_id=sample_blog_post_data['video_id']
        )
        assert created_post is not None

        # Mock read
        mock_collection.find_one.return_value = {
            '_id': post_id,
            'user_id': user_id,
            'title': sample_blog_post_data['title'],
            'content': sample_blog_post_data['content']
        }

        # Test read
        retrieved_post = blog_post_model.get_post_by_id(post_id, user_id)
        assert retrieved_post is not None
        assert retrieved_post['title'] == sample_blog_post_data['title']

        # Mock update
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_collection.update_one.return_value = mock_update_result

        # Test update
        update_success = blog_post_model.update_post(
            post_id, user_id, {'title': 'Updated Title'}
        )
        assert update_success is True

        # Mock delete
        mock_delete_result = Mock()
        mock_delete_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_delete_result

        # Test delete
        delete_success = blog_post_model.delete_post(post_id, user_id)
        assert delete_success is True

    @pytest.mark.unit
    def test_invalid_object_id_handling(self, blog_post_model, mock_mongodb_globally):
        """Test handling of invalid ObjectId strings"""
        mock_collection = mock_mongodb_globally['collection']
        
        # Test with invalid ObjectId format - should return None, not raise exception
        result = blog_post_model.get_post_by_id("invalid_id")
        
        # Should return None when ObjectId is invalid
        assert result is None
        
        # Verify that find_one was not called due to ObjectId validation failure
        mock_collection.find_one.assert_not_called()


    @pytest.mark.unit  
    def test_empty_content_handling(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test handling of empty content"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test with empty content
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content="",
            video_id=sample_blog_post_data['video_id']
        )

        # Should handle empty content gracefully
        assert result is not None
        assert result['word_count'] == 0

    @pytest.mark.unit
    def test_large_content_handling(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test handling of large content"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test with large content
        large_content = " ".join(["word"] * 10000)  # 10000 words
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=large_content,
            video_id=sample_blog_post_data['video_id']
        )

        # Should handle large content
        assert result is not None
        assert result['word_count'] == 10000

    @pytest.mark.unit
    def test_special_characters_in_content(self, blog_post_model, sample_blog_post_data, mock_mongodb_globally):
        """Test handling of special characters in content"""
        # Configure mock
        mock_collection = mock_mongodb_globally['collection']
        mock_result = Mock()
        mock_result.inserted_id = ObjectId()
        mock_collection.insert_one.return_value = mock_result

        # Test with special characters
        special_content = "Test with émojis 🚀 and spéciål chàracters! @#$%^&*()"
        result = blog_post_model.create_post(
            user_id=sample_blog_post_data['user_id'],
            youtube_url=sample_blog_post_data['youtube_url'],
            title=sample_blog_post_data['title'],
            content=special_content,
            video_id=sample_blog_post_data['video_id']
        )

        # Should handle special characters
        assert result is not None
        assert result['content'] == special_content
