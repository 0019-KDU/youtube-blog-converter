from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import datetime
import logging
import os
import threading
import atexit

logger = logging.getLogger(__name__)

class MongoDBConnectionManager:
    """Singleton MongoDB connection manager for proper resource handling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDBConnectionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.client = None
            self.db = None
            self._mongodb_uri = None
            self._mongodb_db_name = None
            self._connection_pool_size = 50
            self._max_idle_time_ms = 30000
            self._initialized = True
            
            # Register cleanup on exit
            atexit.register(self.close_connection)
    
    def get_connection(self):
        """Get or create MongoDB connection"""
        if self.client is None:
            self._connect()
        return self.client, self.db
    
    def _connect(self):
        """Establish MongoDB connection with proper configuration"""
        try:
            logger.info("Establishing MongoDB connection...")
            
            self._mongodb_uri = os.getenv('MONGODB_URI')
            self._mongodb_db_name = os.getenv('MONGODB_DB_NAME', 'youtube_blog_db')
            
            if not self._mongodb_uri:
                raise ValueError("MONGODB_URI environment variable not set")
            
            # Configure connection with proper pooling and timeouts
            self.client = MongoClient(
                self._mongodb_uri,
                maxPoolSize=self._connection_pool_size,
                minPoolSize=5,
                maxIdleTimeMS=self._max_idle_time_ms,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                retryWrites=True,
                w='majority'
            )
            
            # Get database
            self.db = self.client[self._mongodb_db_name]
            
            # Test connection
            self.client.admin.command('ping')
            # Remove emoji for Windows compatibility
            logger.info(f"MongoDB connected successfully to database: {self._mongodb_db_name}")
            
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.close_connection()
            raise
    
    def close_connection(self):
        """Close MongoDB connection safely"""
        try:
            if self.client:
                logger.info("Closing MongoDB connection...")
                self.client.close()
                self.client = None
                self.db = None
                logger.info("MongoDB connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {str(e)}")
    
    def get_database(self):
        """Get database instance"""
        client, db = self.get_connection()
        return db
    
    def get_collection(self, collection_name):
        """Get collection instance"""
        db = self.get_database()
        return db[collection_name]
    
    def is_connected(self):
        """Check if MongoDB is connected"""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False
    
    def reconnect(self):
        """Force reconnection to MongoDB"""
        self.close_connection()
        self._connect()

# Global connection manager instance
mongo_manager = MongoDBConnectionManager()

class BaseModel:
    """Base model class with common MongoDB operations"""
    
    def __init__(self, collection_name):
        self.collection_name = collection_name
        self._ensure_connection()
    
    def _ensure_connection(self):
        """Ensure MongoDB connection is available"""
        try:
            if not mongo_manager.is_connected():
                mongo_manager.reconnect()
        except Exception as e:
            logger.error(f"Failed to ensure MongoDB connection: {str(e)}")
            raise
    
    def get_collection(self):
        """Get MongoDB collection with connection check"""
        try:
            self._ensure_connection()
            return mongo_manager.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection {self.collection_name}: {str(e)}")
            raise
    
    def __del__(self):
        """Destructor - no need to close connection as it's managed by singleton"""
        pass

class User(BaseModel):
    """User model with improved connection management"""
    
    def __init__(self):
        super().__init__('users')
        logger.debug("User model initialized")
    
    def create_user(self, username, email, password):
        """Create a new user"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Check if user already exists
            existing_user = collection.find_one({
                "$or": [{"email": email}, {"username": username}]
            })
            
            if existing_user:
                return {
                    'success': False,
                    'message': 'User with this email or username already exists'
                }
            
            # Hash password
            hashed_password = generate_password_hash(password)
            
            # Create user document
            user_data = {
                'username': username,
                'email': email,
                'password_hash': hashed_password,
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'is_active': True
            }
            
            # Insert user
            result = collection.insert_one(user_data)
            
            if result.inserted_id:
                # Get the created user
                user = collection.find_one({'_id': result.inserted_id})
                
                if user:
                    # Convert ObjectId to string and remove sensitive data
                    user['_id'] = str(user['_id'])
                    user.pop('password_hash', None)
                    logger.info(f"User created successfully: {username}")
                    
                    return {
                        'success': True,
                        'user': user,
                        'message': 'User created successfully'
                    }
            
            return {
                'success': False,
                'message': 'Failed to create user'
            }
            
        except Exception as e:
            logger.error(f"Create user error: {str(e)}")
            return {
                'success': False,
                'message': f'Database error: {str(e)}'
            }
        finally:
            collection = None
    
    def authenticate_user(self, email, password):
        """Authenticate user with email and password"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Find user by email
            user = collection.find_one({'email': email})
            
            if user and check_password_hash(user['password_hash'], password):
                # Convert ObjectId to string and remove sensitive data
                user['_id'] = str(user['_id'])
                user.pop('password_hash', None)
                logger.info(f"User authenticated successfully: {email}")
                return user
            
            logger.warning(f"Authentication failed for: {email}")
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None
        finally:
            collection = None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert string ID to ObjectId if needed
            if isinstance(user_id, str):
                try:
                    user_id = ObjectId(user_id)
                except Exception:
                    logger.error(f"Invalid ObjectId format: {user_id}")
                    return None
            
            user = collection.find_one({'_id': user_id})
            
            if user:
                # Convert ObjectId to string and remove sensitive data
                user['_id'] = str(user['_id'])
                user.pop('password_hash', None)
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Get user by ID error: {str(e)}")
            return None
        finally:
            collection = None
    
    def update_user(self, user_id, update_data):
        """Update user information"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert string ID to ObjectId if needed
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.datetime.utcnow()
            
            result = collection.update_one(
                {'_id': user_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Update user error: {str(e)}")
            return False
        finally:
            collection = None

class BlogPost(BaseModel):
    """BlogPost model with improved connection management"""
    
    def __init__(self):
        super().__init__('blog_posts')
        logger.debug("BlogPost model initialized")
    
    def create_post(self, user_id, youtube_url, title, content, video_id):
        """Create a new blog post"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert user_id to ObjectId if it's a string
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            post_data = {
                'user_id': user_id,
                'youtube_url': youtube_url,
                'title': title,
                'content': content,
                'video_id': video_id,
                'word_count': len(content.split()),
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow()
            }
            
            result = collection.insert_one(post_data)
            
            if result.inserted_id:
                # Convert ObjectIds to strings
                post_data['_id'] = str(result.inserted_id)
                post_data['user_id'] = str(post_data['user_id'])
                logger.info(f"Blog post created successfully: {title}")
                return post_data
            
            return None
            
        except Exception as e:
            logger.error(f"Create blog post error: {str(e)}")
            return None
        finally:
            collection = None
    
    def get_user_posts(self, user_id, limit=50, skip=0):
        """Get all posts for a user with pagination"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert user_id to ObjectId if it's a string
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            posts = list(
                collection.find({'user_id': user_id})
                .sort('created_at', -1)
                .limit(limit)
                .skip(skip)
            )
            
            # Convert ObjectIds to strings
            for post in posts:
                post['_id'] = str(post['_id'])
                post['user_id'] = str(post['user_id'])
            
            return posts
            
        except Exception as e:
            logger.error(f"Get user posts error: {str(e)}")
            return []
        finally:
            collection = None
    
    def get_post_by_id(self, post_id, user_id=None):
        """Get a specific post by ID"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert IDs to ObjectId if they're strings
            if isinstance(post_id, str):
                post_id = ObjectId(post_id)
            
            query = {'_id': post_id}
            if user_id:
                if isinstance(user_id, str):
                    user_id = ObjectId(user_id)
                query['user_id'] = user_id
            
            post = collection.find_one(query)
            
            if post:
                # Convert ObjectIds to strings
                post['_id'] = str(post['_id'])
                post['user_id'] = str(post['user_id'])
                return post
            
            return None
            
        except Exception as e:
            logger.error(f"Get post by ID error: {str(e)}")
            return None
        finally:
            collection = None
    
    def update_post(self, post_id, user_id, update_data):
        """Update a blog post"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert IDs to ObjectId if they're strings
            if isinstance(post_id, str):
                post_id = ObjectId(post_id)
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.datetime.utcnow()
            
            result = collection.update_one(
                {'_id': post_id, 'user_id': user_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Update blog post error: {str(e)}")
            return False
        finally:
            collection = None
    
    def delete_post(self, post_id, user_id):
        """Delete a blog post"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert IDs to ObjectId if they're strings
            if isinstance(post_id, str):
                post_id = ObjectId(post_id)
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            result = collection.delete_one({
                '_id': post_id,
                'user_id': user_id
            })
            
            if result.deleted_count > 0:
                logger.info(f"Blog post deleted successfully: {post_id}")
                return True
            else:
                logger.warning(f"No blog post found to delete: {post_id}")
                return False
            
        except Exception as e:
            logger.error(f"Delete blog post error: {str(e)}")
            return False
        finally:
            collection = None
    
    def get_posts_count(self, user_id):
        """Get total count of posts for a user"""
        collection = None
        try:
            collection = self.get_collection()
            
            # Convert user_id to ObjectId if it's a string
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            count = collection.count_documents({'user_id': user_id})
            return count
            
        except Exception as e:
            logger.error(f"Get posts count error: {str(e)}")
            return 0
        finally:
            collection = None

# Cleanup function for graceful shutdown
def cleanup_mongodb_connections():
    """Cleanup MongoDB connections on application shutdown"""
    try:
        if mongo_manager and hasattr(mongo_manager, 'close_connection'):
            mongo_manager.close_connection()
            logger.info("MongoDB connections cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during MongoDB cleanup: {str(e)}")

# Register cleanup function
atexit.register(cleanup_mongodb_connections)
