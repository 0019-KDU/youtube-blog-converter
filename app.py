import os
import re
import sys
import io
import uuid
import logging
import logging.handlers
import time
import datetime
import gc
import json
import tempfile
from pathlib import Path
from cachelib import FileSystemCache
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify, g
from flask_session import Session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, decode_token
from werkzeug.security import generate_password_hash, check_password_hash

# Custom JSON formatter for Loki
class LokiJSONFormatter(logging.Formatter):
    """Enhanced JSON formatter optimized for Loki ingestion"""
    
    def format(self, record):
        # Base log entry structure
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "thread_id": record.thread,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add Flask request context if available
        try:
            from flask import has_request_context, request, g
            if has_request_context():
                log_entry.update({
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'request_id': getattr(g, 'request_id', None)
                })
        except:
            pass
        
        # Add custom fields from extra
        for key in ['user_id', 'youtube_url', 'blog_generation_time', 'status_code', 'word_count', 'blog_post_id']:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():
    """Configure application logging optimized for Loki"""
    
    # Determine log directory
    log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    log_format = os.getenv('LOG_FORMAT', 'json').lower()
    
    if os.getenv('TESTING') == 'true' or os.getenv('FLASK_ENV') == 'testing':
        log_dir = Path(tempfile.gettempdir()) / 'flask-app-test-logs'
    elif log_to_file:
        log_dir = Path('/var/log/flask-app')
    else:
        log_dir = None
    
    # Create formatters
    if log_format == 'json':
        json_formatter = LokiJSONFormatter()
        console_formatter = LokiJSONFormatter()
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        json_formatter = LokiJSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handlers if enabled
    if log_dir:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Main application log
            app_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'app.log',
                maxBytes=50*1024*1024,  # 50MB
                backupCount=10
            )
            app_handler.setFormatter(json_formatter)
            app_handler.setLevel(logging.INFO)
            root_logger.addHandler(app_handler)
            
            # Error log
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'error.log',
                maxBytes=50*1024*1024,  # 50MB
                backupCount=10
            )
            error_handler.setFormatter(json_formatter)
            error_handler.setLevel(logging.ERROR)
            root_logger.addHandler(error_handler)
            
            # Access log
            access_handler = logging.handlers.RotatingFileHandler(
                log_dir / 'access.log',
                maxBytes=50*1024*1024,  # 50MB
                backupCount=10
            )
            access_handler.setFormatter(json_formatter)
            access_handler.setLevel(logging.INFO)
            
            access_logger = logging.getLogger('access')
            access_logger.addHandler(access_handler)
            access_logger.propagate = False
            
            print(f"✅ File logging enabled: {log_dir}")
            
        except PermissionError:
            print(f"⚠️ Cannot create log directory {log_dir}. Using console logging only.")
            access_logger = logging.getLogger('access')
            access_logger.propagate = False
    else:
        access_logger = logging.getLogger('access')
        access_logger.propagate = False
    
    return access_logger

# Initialize logging
try:
    access_logger = setup_logging()
    print("✅ Logging system initialized")
except Exception as e:
    logging.basicConfig(level=logging.INFO)
    access_logger = logging.getLogger('access')
    print(f"⚠️ Fallback logging enabled: {e}")

logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("Environment variables loaded from .env file")
else:
    load_dotenv()

# Initialize Flask app
app = Flask(__name__)

def get_secret_key():
    """Get Flask secret key from environment"""
    secret_key = os.getenv('JWT_SECRET_KEY') or os.getenv('FLASK_SECRET_KEY')
    
    if not secret_key:
        logger.warning("No Flask secret key found in environment variables")
        import secrets
        secret_key = secrets.token_hex(32)
        logger.warning("Generated temporary secret key")
    
    return secret_key

app.secret_key = get_secret_key()

# JWT Configuration
app.config['JWT_SECRET_KEY'] = get_secret_key()
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(
    seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
)

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'cachelib'
app.config['SESSION_CACHELIB'] = FileSystemCache(
    cache_dir='./.flask_session/', 
    threshold=500, 
    default_timeout=300
)
app.config['SESSION_PERMANENT'] = False

Session(app)
jwt = JWTManager(app)

# Add GA configuration
app.config['GA_MEASUREMENT_ID'] = os.getenv('GA_MEASUREMENT_ID', '')

# Make config available in templates
@app.context_processor
def inject_config():
    return dict(config=app.config)

# Import application components
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from src.main import generate_blog_from_youtube
    from src.tool import PDFGeneratorTool
    from auth.models import User, BlogPost
    from auth.routes import auth_bp
    logger.info("✅ Application modules imported successfully")
except ImportError as e:
    logger.error(f"❌ Module import failed: {str(e)}")
    raise

# Register authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Enhanced request middleware for structured logging
@app.before_request
def log_request():
    """Enhanced request logging with structured data"""
    request_id = str(uuid.uuid4())
    g.request_id = request_id
    g.start_time = time.time()
    
    # Log request with structured data
    logger.info(
        "Request started",
        extra={
            'event_type': 'request_start',
            'request_id': request_id,
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_type': request.content_type,
            'content_length': request.content_length
        }
    )

@app.after_request
def log_response(response):
    """Enhanced response logging with performance metrics"""
    duration = time.time() - getattr(g, 'start_time', time.time())
    
    logger.info(
        "Request completed",
        extra={
            'event_type': 'request_end',
            'request_id': getattr(g, 'request_id', 'unknown'),
            'status_code': response.status_code,
            'content_length': response.content_length,
            'duration_ms': round(duration * 1000, 2),
            'response_size': len(response.get_data()) if hasattr(response, 'get_data') else None
        }
    )
    return response

# Cleanup functions remain the same as your original code
def cleanup_com_objects():
    """Cleanup COM objects on Windows to prevent Win32 exceptions"""
    try:
        if sys.platform.startswith('win'):
            try:
                import pythoncom
                pythoncom.CoUninitialize()
                pythoncom.CoInitialize()
            except ImportError:
                pass
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"COM cleanup warning: {str(e)}")

def cleanup_memory():
    """Force garbage collection and memory cleanup"""
    try:
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")
        gc.collect()
        if hasattr(gc, 'set_debug'):
            gc.set_debug(0)
    except Exception as e:
        logger.debug(f"Memory cleanup warning: {str(e)}")

def cleanup_database_connections(model_objects):
    """Cleanup database model objects"""
    try:
        if isinstance(model_objects, list):
            for obj in model_objects:
                if obj:
                    obj = None
        elif model_objects:
            model_objects = None
    except Exception as e:
        logger.debug(f"Database cleanup warning: {str(e)}")

def full_cleanup(*args):
    """Comprehensive cleanup function"""
    try:
        cleanup_database_connections(args)
        cleanup_com_objects()
        cleanup_memory()
    except Exception as e:
        logger.warning(f"Full cleanup warning: {str(e)}")

def cleanup_after_generation():
    """Helper function to clean up resources after blog generation"""
    try:
        for _ in range(3):
            gc.collect()
        if sys.platform.startswith('win'):
            cleanup_com_objects()
        cleanup_memory()
    except Exception as e:
        logger.warning(f"Resource cleanup warning: {str(e)}")

# Utility functions remain the same as your original code
def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r"youtube\.com/watch\?v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"youtube\.com/embed/([^?]+)",
        r"youtube\.com/v/([^?]+)",
        r"youtube\.com/shorts/([^?]+)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_current_user():
    """Get current user from various authentication sources"""
    user_model = None
    try:
        token = None
        
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            token = session.get('access_token')
        
        if not token:
            user_id = session.get('user_id')
            if user_id:
                user_model = User()
                current_user = user_model.get_user_by_id(user_id)
                if current_user:
                    return current_user
        
        if token:
            try:
                decoded_token = decode_token(token)
                current_user_id = decoded_token.get('sub')
                
                if current_user_id:
                    user_model = User()
                    current_user = user_model.get_user_by_id(current_user_id)
                    return current_user
            except Exception as e:
                logger.warning(f"Token validation failed: {e}")
                session.pop('access_token', None)
        
        return None
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return None
    finally:
        if user_model:
            user_model = None

# Context processor and template functions remain the same
@app.context_processor
def inject_user():
    """Inject current user into all templates"""
    current_user = get_current_user()
    return dict(
        current_user=current_user,
        user_logged_in=current_user is not None
    )

@app.template_global()
def format_date(date_obj=None):
    """Format date for template use"""
    if date_obj is None:
        date_obj = datetime.datetime.utcnow()
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except:
            return date_obj
    
    return date_obj.strftime('%b %d, %Y')

@app.template_global() 
def moment(date_obj=None):
    """Moment.js style date formatting"""
    class MockMoment:
        def __init__(self, date):
            self.date = date
            
        def format(self, format_str):
            if not self.date:
                return datetime.datetime.now().strftime('%b %d, %Y')
            
            if isinstance(self.date, str):
                try:
                    self.date = datetime.datetime.fromisoformat(self.date.replace('Z', '+00:00'))
                except:
                    return self.date
            
            format_map = {
                'MMM DD, YYYY': '%b %d, %Y',
                'YYYY-MM-DD': '%Y-%m-%d',
                'MM/DD/YYYY': '%m/%d/%Y'
            }
            
            python_format = format_map.get(format_str, '%b %d, %Y')
            return self.date.strftime(python_format)
    
    return MockMoment(date_obj)

@app.template_filter('nl2br')
def nl2br_filter(text):
    """Convert newlines to HTML line breaks"""
    if text is None:
        return ''
    return text.replace('\n', '<br>')

# Routes remain mostly the same but with enhanced logging
@app.route('/')
def index():
    """Render the main landing page"""
    try:
        logger.info("Index page accessed", extra={'event_type': 'page_view', 'page': 'index'})
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Index page error: {str(e)}", extra={'event_type': 'error', 'page': 'index'})
        return f"Error loading page: {str(e)}", 500

@app.route('/generate-page')
def generate_page():
    """Render the generate blog page"""
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning("Unauthenticated access to generate page", extra={'event_type': 'auth_required'})
            return redirect(url_for('auth.login'))
        
        logger.info(
            "Generate page accessed", 
            extra={
                'event_type': 'page_view', 
                'page': 'generate',
                'user_id': current_user['_id']
            }
        )
        return render_template('generate.html')
    except Exception as e:
        logger.error(f"Generate page error: {str(e)}", extra={'event_type': 'error', 'page': 'generate'})
        return render_template('error.html', error=f"Error loading generate page: {str(e)}"), 500

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog with enhanced logging"""
    start_time = time.time()
    blog_model = None
    user_model = None
    request_id = getattr(g, 'request_id', 'unknown')
    
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                'Unauthorized blog generation attempt', 
                extra={'event_type': 'auth_failed', 'request_id': request_id}
            )
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        youtube_url = request.form.get('youtube_url', '').strip()
        language = request.form.get('language', 'en')
        
        logger.info(
            'Blog generation started',
            extra={
                'event_type': 'blog_generation_start',
                'request_id': request_id,
                'user_id': current_user['_id'],
                'youtube_url': youtube_url,
                'language': language
            }
        )
        
        if not youtube_url:
            logger.warning(
                'Empty YouTube URL provided', 
                extra={'event_type': 'validation_error', 'request_id': request_id}
            )
            return jsonify({'success': False, 'message': 'YouTube URL is required'}), 400
        
        # Validate URL format
        if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', youtube_url):
            logger.warning(
                'Invalid YouTube URL format',
                extra={'event_type': 'validation_error', 'request_id': request_id, 'youtube_url': youtube_url}
            )
            return jsonify({'success': False, 'message': 'Please enter a valid YouTube URL'}), 400
        
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            logger.warning(
                'Could not extract video ID',
                extra={'event_type': 'validation_error', 'request_id': request_id, 'youtube_url': youtube_url}
            )
            return jsonify({'success': False, 'message': 'Invalid YouTube URL'}), 400
        
        # Generate blog content
        blog_content = None
        try:
            logger.info(
                'Starting blog content generation',
                extra={'event_type': 'content_generation_start', 'request_id': request_id, 'video_id': video_id}
            )
            blog_content = generate_blog_from_youtube(youtube_url, language)
        except Exception as gen_error:
            logger.error(
                'Blog generation failed',
                extra={
                    'event_type': 'content_generation_error',
                    'request_id': request_id,
                    'video_id': video_id,
                    'error': str(gen_error)
                },
                exc_info=True
            )
            return jsonify({'success': False, 'message': f'Failed to generate blog: {str(gen_error)}'}), 500
        finally:
            cleanup_after_generation()
        
        # Check if generation was successful
        if not blog_content or len(blog_content) < 100:
            logger.error(
                'Blog generation produced insufficient content',
                extra={
                    'event_type': 'content_generation_insufficient',
                    'request_id': request_id,
                    'content_length': len(blog_content) if blog_content else 0
                }
            )
            return jsonify({'success': False, 'message': 'Failed to generate blog content. Please try with a different video.'}), 500
        
        # Check for error responses
        if blog_content.startswith("ERROR:"):
            error_msg = blog_content.replace("ERROR:", "").strip()
            logger.error(
                'Blog generation returned error',
                extra={'event_type': 'content_generation_error', 'request_id': request_id, 'error': error_msg}
            )
            return jsonify({'success': False, 'message': error_msg}), 500
        
        # Extract title from content
        title_match = re.search(r'^#\s+(.+)$', blog_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "YouTube Blog Post"
        
        # Save blog post to database
        blog_model = BlogPost()
        blog_post = blog_model.create_post(
            user_id=current_user['_id'],
            youtube_url=youtube_url,
            title=title,
            content=blog_content,
            video_id=video_id
        )
        
        if not blog_post:
            logger.error(
                'Failed to save blog post to database',
                extra={'event_type': 'database_error', 'request_id': request_id}
            )
            return jsonify({'success': False, 'message': 'Failed to save blog post'}), 500
        
        generation_time = time.time() - start_time
        word_count = len(blog_content.split())
        
        logger.info(
            'Blog generation completed successfully',
            extra={
                'event_type': 'blog_generation_success',
                'request_id': request_id,
                'user_id': current_user['_id'],
                'blog_post_id': str(blog_post['_id']),
                'blog_generation_time': generation_time,
                'word_count': word_count,
                'title': title,
                'video_id': video_id
            }
        )
        
        # Store in session for PDF generation
        session['current_blog'] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url,
            'video_id': video_id,
            'title': title,
            'generation_time': generation_time,
            'post_id': str(blog_post['_id']),
            'word_count': word_count
        }
        
        return jsonify({
            'success': True,
            'blog_content': blog_content,
            'generation_time': f"{generation_time:.1f}s",
            'word_count': word_count,
            'title': title,
            'video_id': video_id
        })
        
    except Exception as e:
        logger.error(
            'Unexpected error in blog generation',
            extra={'event_type': 'unexpected_error', 'request_id': request_id},
            exc_info=True
        )
        return jsonify({'success': False, 'message': f'Error generating blog: {str(e)}'}), 500
    
    finally:
        try:
            full_cleanup(blog_model, user_model)
        except Exception as cleanup_error:
            logger.warning(
                'Cleanup error',
                extra={'event_type': 'cleanup_warning', 'request_id': request_id, 'error': str(cleanup_error)}
            )

# Additional routes remain the same with similar logging enhancements...
# [Include all your other routes here with similar logging patterns]

@app.route('/dashboard')
def dashboard():
    """User dashboard with enhanced logging"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        
        if not current_user:
            session.clear()
            logger.warning("Dashboard access denied - no valid user session", extra={'event_type': 'auth_failed'})
            return redirect(url_for('auth.login'))
        
        logger.info(
            "Dashboard accessed",
            extra={
                'event_type': 'page_view',
                'page': 'dashboard',
                'user_id': current_user['_id'],
                'username': current_user.get('username', 'Unknown')
            }
        )
        
        blog_model = BlogPost()
        posts = blog_model.get_user_posts(current_user['_id'])
        
        logger.info(
            "Dashboard data loaded",
            extra={
                'event_type': 'dashboard_loaded',
                'user_id': current_user['_id'],
                'post_count': len(posts)
            }
        )
        
        return render_template('dashboard.html', user=current_user, posts=posts)
        
    except Exception as e:
        logger.error(
            "Dashboard error",
            extra={'event_type': 'dashboard_error'},
            exc_info=True
        )
        session.clear()
        return redirect(url_for('auth.login'))
    finally:
        if blog_model:
            blog_model = None

# Health check with enhanced monitoring
@app.route('/health')
def health_check():
    """Enhanced health check endpoint"""
    try:
        from auth.models import mongo_manager
        db_connected = mongo_manager.is_connected()
        
        health_data = {
            'status': 'healthy' if db_connected else 'unhealthy',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'database': 'connected' if db_connected else 'disconnected',
            'version': '1.0.0',
            'logging': 'enabled'
        }
        
        status_code = 200 if db_connected else 503
        
        logger.info(
            "Health check performed",
            extra={
                'event_type': 'health_check',
                'status': health_data['status'],
                'database_status': health_data['database']
            }
        )
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(
            "Health check failed",
            extra={'event_type': 'health_check_error'},
            exc_info=True
        )
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'error': str(e)
        }), 503

# Error handlers with logging
@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    logger.warning("Unauthorized access attempt", extra={'event_type': 'unauthorized_access'})
    return redirect(url_for('auth.login'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(
        "Page not found", 
        extra={
            'event_type': 'page_not_found',
            'path': request.path,
            'method': request.method
        }
    )
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(
        "Internal server error",
        extra={'event_type': 'internal_server_error'},
        exc_info=True
    )
    return render_template('error.html', error="Internal server error"), 500

# Application cleanup
@app.teardown_appcontext
def cleanup_app_context(error):
    """Cleanup resources on app context teardown"""
    try:
        cleanup_memory()
    except Exception as e:
        logger.debug(f"App context cleanup warning: {str(e)}")

if __name__ == '__main__':
    # Create session directory
    session_dir = './.flask_session/'
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        logger.info(f"Created session directory: {session_dir}")
    
    # Configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Validate required environment variables
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key',
        'SUPADATA_API_KEY': 'Supadata API key',
        'MONGODB_URI': 'MongoDB connection URI',
        'JWT_SECRET_KEY': 'JWT secret key'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info(
        "Application starting",
        extra={
            'event_type': 'app_start',
            'host': host,
            'port': port,
            'debug': debug_mode,
            'log_format': os.getenv('LOG_FORMAT', 'json')
        }
    )
    
    try:
        app.run(host=host, port=port, debug=debug_mode)
    except Exception as e:
        logger.error(
            "Failed to start application",
            extra={'event_type': 'app_start_error'},
            exc_info=True
        )
        sys.exit(1)
    finally:
        try:
            full_cleanup()
            logger.info("Application shutdown cleanup completed")
        except Exception as e:
            logger.warning(f"Shutdown cleanup warning: {str(e)}")
