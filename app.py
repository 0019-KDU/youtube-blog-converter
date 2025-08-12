import os
import re
import sys
import io
import uuid
import time
import datetime
import gc
import json
import tempfile
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify, g, Response, has_app_context
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, decode_token
from werkzeug.security import generate_password_hash, check_password_hash

# Prometheus metrics imports
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST
import psutil
import threading
from functools import wraps

# Load environment variables FIRST - before any Flask operations
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded .env from: {env_path}")
else:
    load_dotenv()
    print("Loaded .env from default location")

# ========== LOKI HANDLER IMPLEMENTATION ==========
import requests
from queue import Queue, Empty

class LokiHandler(logging.Handler):
    """Custom Loki handler for Flask application logs"""
    
    def __init__(self, loki_url, tags=None, timeout=5, batch_size=100, flush_interval=5):
        super().__init__()
        self.loki_url = loki_url.rstrip('/') + '/loki/api/v1/push'
        self.tags = tags or {}
        self.timeout = timeout
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Batch processing
        self.log_queue = Queue()
        self.batch_thread = threading.Thread(target=self._batch_sender, daemon=True)
        self.batch_thread.start()
    
    def emit(self, record):
        """Emit a log record to Loki"""
        try:
            # Format the record
            log_entry = self.format(record)
            
            # Create timestamp in nanoseconds
            timestamp = str(int(time.time() * 1_000_000_000))
            
            # Prepare labels
            labels = dict(self.tags)
            labels.update({
                'level': record.levelname.lower(),
                'logger': record.name,
                'filename': record.filename,
                'function': record.funcName,
                'application': 'flask-blog-app'
            })
            
            # Add extra labels from record
            if hasattr(record, 'request_id'):
                labels['request_id'] = record.request_id
            if hasattr(record, 'user_id'):
                labels['user_id'] = record.user_id
            if hasattr(record, 'endpoint'):
                labels['endpoint'] = record.endpoint
            if hasattr(record, 'error_type'):
                labels['error_type'] = record.error_type
            
            # Create Loki entry
            loki_entry = {
                'streams': [{
                    'stream': labels,
                    'values': [[timestamp, log_entry]]
                }]
            }
            
            # Add to queue for batch processing
            self.log_queue.put(loki_entry)
            
        except Exception as e:
            # Don't let logging errors break the application
            print(f"Loki handler error: {e}")
    
    def _batch_sender(self):
        """Background thread to send logs in batches"""
        batch = []
        last_flush = time.time()
        
        while True:
            try:
                # Try to get log entry with timeout
                try:
                    entry = self.log_queue.get(timeout=1)
                    batch.append(entry)
                except Empty:
                    pass
                
                # Check if we should flush the batch
                should_flush = (
                    len(batch) >= self.batch_size or 
                    (batch and time.time() - last_flush >= self.flush_interval)
                )
                
                if should_flush and batch:
                    self._send_batch(batch)
                    batch = []
                    last_flush = time.time()
                    
            except Exception as e:
                print(f"Batch sender error: {e}")
                batch = []  # Clear batch on error
    
    def _send_batch(self, batch):
        """Send a batch of log entries to Loki"""
        if not batch:
            return
            
        try:
            # Merge all streams
            merged_streams = {}
            for entry in batch:
                for stream in entry['streams']:
                    stream_key = json.dumps(stream['stream'], sort_keys=True)
                    if stream_key not in merged_streams:
                        merged_streams[stream_key] = {
                            'stream': stream['stream'],
                            'values': []
                        }
                    merged_streams[stream_key]['values'].extend(stream['values'])
            
            # Create final payload
            payload = {
                'streams': list(merged_streams.values())
            }
            
            # Send to Loki
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                self.loki_url, 
                data=json.dumps(payload), 
                headers=headers, 
                timeout=self.timeout
            )
            
            if response.status_code != 204:
                print(f"Loki push failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Failed to send logs to Loki: {e}")

class LokiJsonFormatter(logging.Formatter):
    """JSON formatter for Loki with structured data"""
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            'timestamp': datetime.datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'filename': record.filename,
            'lineno': record.lineno,
            'function': record.funcName,
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra attributes
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'message', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = str(value)
        
        return json.dumps(log_entry)

# ========== BASIC LOGGING CONFIGURATION (BEFORE FLASK) ==========
def setup_basic_logging():
    """Setup basic logging before Flask app initialization"""
    
    # Create logs directory
    log_dir = Path('/var/log/flask-app')
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fall back to local directory if /var/log is not writable
        log_dir = Path('./logs')
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set log level from environment
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    
    # Simple formatter for initial setup
    basic_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(filename)s:%(lineno)d'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(basic_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for application logs (if directory exists)
    if log_dir.exists():
        app_log_file = log_dir / 'app.log'
        app_handler = RotatingFileHandler(
            app_log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        app_handler.setLevel(log_level)
        app_handler.setFormatter(basic_formatter)
        root_logger.addHandler(app_handler)
    
    # Set specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    print("Basic logging configuration completed")
    return root_logger

# Setup basic logging before creating Flask app
logger = setup_basic_logging()

def get_secret_key():
    """Get Flask secret key from environment with guaranteed fallback"""
    # Try multiple environment variable names
    secret_key = (
        os.getenv('JWT_SECRET_KEY') or 
        os.getenv('FLASK_SECRET_KEY') or 
        os.getenv('SECRET_KEY')
    )
    
    if not secret_key:
        logger.warning("No Flask secret key found in environment variables!")
        logger.warning("Checked: JWT_SECRET_KEY, FLASK_SECRET_KEY, SECRET_KEY")
        
        # Generate a secure random key
        import secrets
        secret_key = secrets.token_urlsafe(32)
        logger.info("Generated secure temporary secret key")
        logger.warning("For production, set JWT_SECRET_KEY in your environment variables")
        
        # Save to environment for consistency
        os.environ['JWT_SECRET_KEY'] = secret_key
    else:
        logger.info("Secret key loaded successfully from environment")
    
    # Ensure minimum length
    if len(secret_key) < 16:
        logger.warning("Secret key too short, generating secure replacement")
        import secrets
        secret_key = secrets.token_urlsafe(32)
        os.environ['JWT_SECRET_KEY'] = secret_key
    
    return secret_key

# Get the secret key BEFORE creating Flask app
SECRET_KEY = get_secret_key()
logger.info(f"Secret key length: {len(SECRET_KEY)} characters")

# Initialize Flask app
app = Flask(__name__)

# Set secret key IMMEDIATELY after Flask app creation
app.secret_key = SECRET_KEY
logger.info("Flask secret key set successfully")

# Verify secret key is accessible
if not app.secret_key:
    raise RuntimeError("Failed to set Flask secret key!")

# ========== ENHANCED LOGGING CONFIGURATION WITH LOKI (AFTER FLASK) ==========
def setup_enhanced_logging_with_loki():
    """Setup enhanced logging with Loki integration"""
    
    # Get your DigitalOcean droplet IP from environment
    loki_url = os.getenv('LOKI_URL', 'http://YOUR_DROPLET_IP:3100')  # Replace with actual IP
    
    # Determine log directory based on environment
    shared_log_path = os.getenv('SHARED_LOG_PATH', '/shared-logs')
    log_dir = Path(shared_log_path) if os.path.exists(shared_log_path) else Path('./logs')
    
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set log level from environment
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Keep existing console handler
    console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
    
    # Loki handler for centralized logging
    try:
        loki_handler = LokiHandler(
            loki_url=loki_url,
            tags={
                'application': 'flask-blog-app',
                'environment': os.getenv('FLASK_ENV', 'production'),
                'service': 'web-app'
            }
        )
        loki_handler.setLevel(log_level)
        loki_handler.setFormatter(LokiJsonFormatter())
        root_logger.addHandler(loki_handler)
        logger.info(f"Loki handler configured successfully: {loki_url}")
    except Exception as e:
        logger.error(f"Failed to configure Loki handler: {e}")
    
    # Enhanced JSON logs for local file storage (backup)
    json_log_file = log_dir / 'app.json'
    json_handler = RotatingFileHandler(
        json_log_file,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=5
    )
    json_handler.setLevel(log_level)
    json_handler.setFormatter(LokiJsonFormatter())
    root_logger.addHandler(json_handler)
    
    # Enhanced access logs
    access_log_file = log_dir / 'access.log'
    access_handler = RotatingFileHandler(
        access_log_file,
        maxBytes=50*1024*1024,
        backupCount=5
    )
    access_handler.setLevel(logging.INFO)
    access_formatter = logging.Formatter(
        '%(asctime)s - %(remote_addr)s - "%(method)s %(url)s %(protocol)s" %(status_code)s %(response_size)s "%(user_agent)s" %(duration_ms)sms'
    )
    access_handler.setFormatter(access_formatter)
    
    # Create access logger
    access_logger = logging.getLogger('access')
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    
    logger.info(f"Enhanced logging with Loki configured - Log directory: {log_dir}")
    return root_logger

# JWT Configuration
app.config['JWT_SECRET_KEY'] = SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(
    seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
)

# Optimized session configuration to prevent large cookies
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_COOKIE_SIZE'] = 4000  # Stay well under the 4093 byte limit

logger.info("Using Flask's built-in session management with size optimization")

# Initialize JWT
try:
    jwt = JWTManager(app)
    logger.info("JWT Manager initialized successfully")
except Exception as e:
    logger.error(f"Error initializing JWT: {e}")
    raise

# Add GA configuration
app.config['GA_MEASUREMENT_ID'] = os.getenv('GA_MEASUREMENT_ID', '')

# In-memory storage for large session data (temporary solution)
# In production, use Redis or database storage
app.temp_storage = {}

# ========== PROMETHEUS METRICS SETUP ==========
# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Application metrics
http_requests_total = Counter(
    'flask_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    'flask_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

blog_generation_requests = Counter(
    'blog_generation_requests_total',
    'Total blog generation requests',
    ['status'],
    registry=REGISTRY
)

blog_generation_duration = Histogram(
    'blog_generation_duration_seconds',
    'Blog generation duration in seconds',
    registry=REGISTRY
)

active_users = Gauge(
    'active_users',
    'Number of active users',
    registry=REGISTRY
)

youtube_urls_processed = Counter(
    'youtube_urls_processed_total',
    'Total YouTube URLs processed',
    ['status'],
    registry=REGISTRY
)

openai_tokens_used = Counter(
    'openai_tokens_used_total',
    'Total OpenAI tokens used',
    registry=REGISTRY
)

pdf_downloads = Counter(
    'pdf_downloads_total',
    'Total PDF downloads',
    registry=REGISTRY
)

database_operations = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'collection', 'status'],
    registry=REGISTRY
)

# System metrics
cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'CPU usage percentage',
    registry=REGISTRY
)

memory_usage = Gauge(
    'system_memory_usage_bytes',
    'Memory usage in bytes',
    registry=REGISTRY
)

memory_usage_percent = Gauge(
    'system_memory_usage_percent',
    'Memory usage percentage',
    registry=REGISTRY
)

disk_usage = Gauge(
    'system_disk_usage_percent',
    'Disk usage percentage',
    registry=REGISTRY
)

# User activity metrics
user_sessions = Gauge(
    'user_sessions_active',
    'Number of active user sessions',
    registry=REGISTRY
)

blog_posts_created = Counter(
    'blog_posts_created_total',
    'Total blog posts created',
    registry=REGISTRY
)

user_registrations = Counter(
    'user_registrations_total',
    'Total user registrations',
    ['status'],
    registry=REGISTRY
)

user_logins = Counter(
    'user_logins_total',
    'Total user login attempts',
    ['status'],
    registry=REGISTRY
)

# Error metrics
application_errors = Counter(
    'application_errors_total',
    'Total application errors',
    ['error_type'],
    registry=REGISTRY
)

api_errors = Counter(
    'api_errors_total',
    'Total API errors',
    ['api', 'error_type'],
    registry=REGISTRY
)

# Log metrics for Loki integration
log_entries_total = Counter(
    'log_entries_total',
    'Total log entries by level',
    ['level', 'logger'],
    registry=REGISTRY
)

# System metrics collection thread
def collect_system_metrics():
    """Collect system metrics periodically"""
    while True:
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.used)
            memory_usage_percent.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage.set((disk.used / disk.total) * 100)
            
            # Active sessions (estimate from temp storage)
            user_sessions.set(len(app.temp_storage))
            
            time.sleep(30)  # Collect every 30 seconds
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            time.sleep(30)

# Start system metrics collection thread
metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
metrics_thread.start()

# Enhanced logging filter to track log metrics (context-aware)
class ContextAwareLogMetricsFilter(logging.Filter):
    """Filter to track log metrics for Prometheus with context awareness"""
    
    def filter(self, record):
        # Track log entries by level
        log_entries_total.labels(
            level=record.levelname,
            logger=record.name
        ).inc()
        
        # Add context information to log records safely
        if has_app_context():
            try:
                if not hasattr(record, 'request_id'):
                    record.request_id = getattr(g, 'request_id', 'no-request')
                
                if not hasattr(record, 'user_id'):
                    record.user_id = getattr(g, 'user_id', 'anonymous')
                
                if not hasattr(record, 'endpoint'):
                    record.endpoint = request.endpoint if request else 'unknown'
            except:
                record.request_id = 'no-request'
                record.user_id = 'anonymous'
                record.endpoint = 'unknown'
        else:
            record.request_id = 'no-request'
            record.user_id = 'anonymous'
            record.endpoint = 'unknown'
            
        return True

# Setup enhanced logging with Flask context
with app.app_context():
    setup_enhanced_logging_with_loki()
    
    # Add the metrics filter to all handlers
    metrics_filter = ContextAwareLogMetricsFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(metrics_filter)

# Decorators for metrics collection
def track_requests(f):
    """Decorator to track HTTP requests with enhanced Loki logging"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            
            # Extract status code
            if isinstance(response, tuple):
                status_code = str(response[1]) if len(response) > 1 else '200'
            elif hasattr(response, 'status_code'):
                status_code = str(response.status_code)
            else:
                status_code = '200'
            
            # Track metrics
            http_requests_total.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status_code=status_code
            ).inc()
            
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)
            
            # Enhanced access logging with Loki-friendly structure
            access_logger = logging.getLogger('access')
            access_logger.info(
                'Request completed',
                extra={
                    'event': 'request_completed',
                    'remote_addr': request.remote_addr,
                    'method': request.method,
                    'url': request.url,
                    'protocol': request.environ.get('SERVER_PROTOCOL', 'HTTP/1.1'),
                    'status_code': status_code,
                    'response_size': len(str(response)) if isinstance(response, str) else 0,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'duration_ms': round(duration * 1000, 2),
                    'endpoint': request.endpoint or 'unknown'
                }
            )
            
            return response
            
        except Exception as e:
            # Track error
            http_requests_total.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status_code='500'
            ).inc()
            
            application_errors.labels(error_type=type(e).__name__).inc()
            
            # Enhanced error logging for Loki
            logger.error(
                f"Request failed: {request.method} {request.url}",
                extra={
                    'event': 'request_failed',
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'endpoint': request.endpoint or 'unknown',
                    'method': request.method,
                    'url': request.url
                },
                exc_info=True
            )
            raise
    
    return decorated_function

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
    logger.info("All imports successful")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

# Register authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Request middleware with enhanced Loki logging
@app.before_request
def log_request():
    """Enhanced request logging with context for Loki"""
    request_id = str(uuid.uuid4())
    g.request_id = request_id
    g.start_time = time.time()
    g.user_id = 'anonymous'  # Will be updated if user is authenticated
    
    # Enhanced request logging with structured data for Loki
    logger.info(
        "Request started",
        extra={
            'event': 'request_started',
            'request_id': request_id,
            'method': request.method,
            'url': request.url,
            'path': request.path,
            'query_string': request.query_string.decode('utf-8'),
            'user_agent': request.headers.get('User-Agent', ''),
            'remote_addr': request.remote_addr,
            'content_type': request.content_type,
            'content_length': request.content_length,
            'endpoint': request.endpoint or 'unknown'
        }
    )

@app.after_request
def log_response(response):
    """Enhanced response logging with safe response size calculation for Loki"""
    duration = time.time() - getattr(g, 'start_time', time.time())
    request_id = getattr(g, 'request_id', 'unknown')
    
    # Safely calculate response size
    def get_safe_response_size(response):
        try:
            # Check if response has content_length (for static files and other responses)
            if hasattr(response, 'content_length') and response.content_length is not None:
                return response.content_length
            
            # For responses that support get_data() 
            if hasattr(response, 'get_data'):
                # Check if response is in direct passthrough mode
                if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                    return -1  # Indicate unknown size for passthrough responses
                
                try:
                    return len(response.get_data())
                except RuntimeError:
                    # Fallback for responses in passthrough mode
                    return -1
            
            # Fallback for other response types
            return 0
            
        except Exception:
            return 0
    
    response_size = get_safe_response_size(response)
    
    # Enhanced response logging for Loki
    logger.info(
        "Request completed",
        extra={
            'event': 'request_completed',
            'request_id': request_id,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'response_size': response_size,
            'content_type': getattr(response, 'content_type', 'unknown'),
            'method': request.method,
            'endpoint': request.endpoint or 'unknown',
            'success': response.status_code < 400
        }
    )
    
    return response

# Enhanced database operations tracking
def track_db_operation(operation, collection, func):
    """Track database operations with detailed logging"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            logger.debug(f"Database operation started: {operation} on {collection}")
            result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            database_operations.labels(
                operation=operation,
                collection=collection,
                status='success'
            ).inc()
            
            logger.info(
                f"Database operation completed successfully",
                extra={
                    'event': 'database_operation',
                    'operation': operation,
                    'collection': collection,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'success'
                }
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            database_operations.labels(
                operation=operation,
                collection=collection,
                status='error'
            ).inc()
            
            logger.error(
                f"Database operation failed",
                extra={
                    'event': 'database_error',
                    'operation': operation,
                    'collection': collection,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'error',
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise
    return wrapper

# ========== CLEANUP FUNCTIONS ==========
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
    except Exception:
        pass

def cleanup_memory():
    """Force garbage collection and memory cleanup"""
    try:
        collected = gc.collect()
        logger.debug(f"Garbage collection completed: {collected} objects collected")
        gc.collect()
        
        if hasattr(gc, 'set_debug'):
            gc.set_debug(0)
            
    except Exception:
        pass

def cleanup_database_connections(model_objects):
    """Cleanup database model objects"""
    try:
        if isinstance(model_objects, list):
            for obj in model_objects:
                if obj:
                    obj = None
        elif model_objects:
            model_objects = None
    except Exception:
        pass

def full_cleanup(*args):
    """Comprehensive cleanup function"""
    try:
        cleanup_database_connections(args)
        cleanup_com_objects()
        cleanup_memory()
    except Exception:
        pass

def cleanup_after_generation():
    """Helper function to clean up resources after blog generation"""
    try:
        for _ in range(3):
            gc.collect()
        
        if sys.platform.startswith('win'):
            cleanup_com_objects()
        
        cleanup_memory()
                
    except Exception:
        pass

# ========== SESSION MANAGEMENT FUNCTIONS ==========
def store_large_data(key, data, user_id=None):
    """Store large data outside of session to avoid cookie size limits"""
    storage_key = f"{user_id}_{key}" if user_id else key
    app.temp_storage[storage_key] = {
        'data': data,
        'timestamp': time.time()
    }
    # Clean old data (older than 1 hour)
    cleanup_old_storage()
    
    logger.debug(f"Stored large data with key: {storage_key}")
    return storage_key

def retrieve_large_data(key, user_id=None):
    """Retrieve large data from temporary storage"""
    storage_key = f"{user_id}_{key}" if user_id else key
    stored_item = app.temp_storage.get(storage_key)
    if stored_item:
        # Check if data is not too old (1 hour)
        if time.time() - stored_item['timestamp'] < 3600:
            logger.debug(f"Retrieved large data with key: {storage_key}")
            return stored_item['data']
        else:
            # Remove expired data
            app.temp_storage.pop(storage_key, None)
            logger.debug(f"Removed expired data with key: {storage_key}")
    return None

def cleanup_old_storage():
    """Clean up old temporary storage data"""
    current_time = time.time()
    expired_keys = []
    for key, item in app.temp_storage.items():
        if current_time - item['timestamp'] > 3600:  # 1 hour
            expired_keys.append(key)
    
    for key in expired_keys:
        app.temp_storage.pop(key, None)
    
    if expired_keys:
        logger.info(f"Cleaned up {len(expired_keys)} expired storage items")

# ========== UTILITY FUNCTIONS ==========
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
        
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Check session for token
        if not token:
            token = session.get('access_token')
        
        # Check user_id directly in session as fallback
        if not token:
            user_id = session.get('user_id')
            if user_id:
                user_model = User()
                current_user = user_model.get_user_by_id(user_id)
                if current_user:
                    g.user_id = str(current_user['_id'])
                    active_users.inc()
                    return current_user
        
        if token:
            try:
                decoded_token = decode_token(token)
                current_user_id = decoded_token.get('sub')
                
                if current_user_id:
                    user_model = User()
                    current_user = user_model.get_user_by_id(current_user_id)
                    if current_user:
                        g.user_id = str(current_user['_id'])
                        active_users.inc()
                        return current_user
            except Exception:
                session.pop('access_token', None)
        
        return None
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Error getting current user",
            extra={
                'event': 'user_authentication_error',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return None
    finally:
        if user_model:
            user_model = None

# Context processor to inject user into all templates
@app.context_processor
def inject_user():
    """Inject current user into all templates"""
    current_user = get_current_user()
    return dict(
        current_user=current_user,
        user_logged_in=current_user is not None
    )

# Template helper functions
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

# ========== ROUTES ==========
@app.route('/')
@track_requests
def index():
    """Render the main landing page"""
    try:
        logger.info(
            "Index page accessed", 
            extra={
                'event': 'page_access',
                'page': 'index'
            }
        )
        return render_template('index.html')
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Error loading index page", 
            extra={
                'event': 'page_error',
                'page': 'index',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return f"Error loading page: {str(e)}", 500

@app.route('/generate-page')
@track_requests
def generate_page():
    """Render the generate blog page with left/right layout"""
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                "Unauthorized access to generate page",
                extra={
                    'event': 'unauthorized_access',
                    'page': 'generate'
                }
            )
            return redirect(url_for('auth.login'))
        
        logger.info(
            f"Generate page accessed by user: {current_user['username']}",
            extra={
                'event': 'page_access',
                'page': 'generate',
                'user_id': current_user['_id'],
                'username': current_user['username']
            }
        )
        return render_template('generate.html')
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Error loading generate page",
            extra={
                'event': 'page_error',
                'page': 'generate',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return render_template('error.html', 
                             error=f"Error loading generate page: {str(e)}"), 500

@app.route('/generate', methods=['POST'])
@track_requests
def generate_blog():
    """Process YouTube URL and generate blog - returns JSON for AJAX with enhanced Loki logging"""
    start_time = time.time()
    blog_model = None
    user_model = None
    request_id = getattr(g, 'request_id', 'unknown')
    
    try:
        current_user = get_current_user()
        if not current_user:
            user_logins.labels(status='failed').inc()
            logger.warning(
                "Unauthorized blog generation attempt",
                extra={
                    'event': 'unauthorized_access',
                    'operation': 'blog_generation',
                    'remote_addr': request.remote_addr
                }
            )
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        youtube_url = request.form.get('youtube_url', '').strip()
        language = request.form.get('language', 'en')
        
        logger.info(
            "Blog generation started",
            extra={
                'event': 'blog_generation_started',
                'user_id': current_user['_id'],
                'username': current_user['username'],
                'youtube_url': youtube_url,
                'language': language,
                'operation': 'create_blog'
            }
        )
        
        if not youtube_url:
            blog_generation_requests.labels(status='failed').inc()
            logger.warning(
                "Blog generation failed: Empty YouTube URL",
                extra={
                    'event': 'validation_error',
                    'operation': 'blog_generation',
                    'error_type': 'empty_url',
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'YouTube URL is required'}), 400
        
        # Validate URL format
        if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', youtube_url):
            blog_generation_requests.labels(status='failed').inc()
            logger.warning(
                "Blog generation failed: Invalid URL format",
                extra={
                    'event': 'validation_error',
                    'operation': 'blog_generation',
                    'error_type': 'invalid_url_format',
                    'youtube_url': youtube_url,
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'Please enter a valid YouTube URL'}), 400
        
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            blog_generation_requests.labels(status='failed').inc()
            youtube_urls_processed.labels(status='invalid').inc()
            logger.warning(
                "Blog generation failed: Could not extract video ID",
                extra={
                    'event': 'video_id_extraction_failed',
                    'operation': 'blog_generation',
                    'youtube_url': youtube_url,
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'Invalid YouTube URL'}), 400
        
        youtube_urls_processed.labels(status='valid').inc()
        logger.info(
            "Video ID extracted successfully",
            extra={
                'event': 'video_id_extracted',
                'video_id': video_id,
                'youtube_url': youtube_url,
                'user_id': current_user['_id']
            }
        )
        
        # Track blog generation start
        generation_start = time.time()
        
        # Generate blog content
        blog_content = None
        try:
            logger.info(
                "Starting blog content generation",
                extra={
                    'event': 'content_generation_started',
                    'video_id': video_id,
                    'user_id': current_user['_id']
                }
            )
            blog_content = generate_blog_from_youtube(youtube_url, language)
            
            # Estimate tokens used (rough calculation)
            estimated_tokens = len(blog_content.split()) * 1.3  # Rough estimate
            openai_tokens_used.inc(estimated_tokens)
            
            logger.info(
                "Blog content generated successfully",
                extra={
                    'event': 'content_generation_completed',
                    'content_length': len(blog_content),
                    'estimated_tokens': int(estimated_tokens),
                    'video_id': video_id,
                    'user_id': current_user['_id']
                }
            )
            
        except Exception as gen_error:
            blog_generation_requests.labels(status='failed').inc()
            api_errors.labels(api='openai', error_type=type(gen_error).__name__).inc()
            logger.error(
                "Blog generation failed",
                extra={
                    'event': 'content_generation_failed',
                    'error_type': type(gen_error).__name__,
                    'error_message': str(gen_error),
                    'video_id': video_id,
                    'user_id': current_user['_id'],
                    'operation': 'blog_generation'
                },
                exc_info=True
            )
            return jsonify({'success': False, 'message': f'Failed to generate blog: {str(gen_error)}'}), 500
        finally:
            cleanup_after_generation()
        
        # Check if generation was successful
        if not blog_content or len(blog_content) < 100:
            blog_generation_requests.labels(status='failed').inc()
            logger.error(
                "Blog generation failed: Content too short or empty",
                extra={
                    'event': 'content_validation_failed',
                    'content_length': len(blog_content) if blog_content else 0,
                    'video_id': video_id,
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'Failed to generate blog content. Please try with a different video.'}), 500
        
        # Check for error responses
        if blog_content.startswith("ERROR:"):
            blog_generation_requests.labels(status='failed').inc()
            error_msg = blog_content.replace("ERROR:", "").strip()
            logger.error(
                "Blog generation error response",
                extra={
                    'event': 'content_generation_error',
                    'error_message': error_msg,
                    'video_id': video_id,
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': error_msg}), 500
        
        # Track successful generation
        generation_duration = time.time() - generation_start
        blog_generation_duration.observe(generation_duration)
        blog_generation_requests.labels(status='success').inc()
        
        # Extract title from content
        title_match = re.search(r'^#\s+(.+)$', blog_content, re.MULTILINE)
        title = title_match.group(1) if title_match else "YouTube Blog Post"
        
        logger.info(
            "Blog title extracted",
            extra={
                'event': 'title_extracted',
                'title': title,
                'video_id': video_id,
                'user_id': current_user['_id']
            }
        )
        
        # Save blog post to database with Loki logging
        blog_model = BlogPost()
        try:
            logger.info(
                "Saving blog post to database",
                extra={
                    'event': 'database_operation_started',
                    'operation': 'create_blog_post',
                    'user_id': current_user['_id']
                }
            )
            blog_post = blog_model.create_post(
                user_id=current_user['_id'],
                youtube_url=youtube_url,
                title=title,
                content=blog_content,
                video_id=video_id
            )
            
            database_operations.labels(
                operation='create',
                collection='blog_posts',
                status='success'
            ).inc()
            blog_posts_created.inc()
            
            logger.info(
                "Blog post saved successfully",
                extra={
                    'event': 'database_operation_completed',
                    'operation': 'create_blog_post',
                    'post_id': str(blog_post['_id']),
                    'user_id': current_user['_id'],
                    'title': title
                }
            )
        except Exception as db_error:
            database_operations.labels(
                operation='create',
                collection='blog_posts',
                status='error'
            ).inc()
            logger.error(
                "Database error creating blog post",
                extra={
                    'event': 'database_error',
                    'operation': 'create_blog_post',
                    'error_type': type(db_error).__name__,
                    'error_message': str(db_error),
                    'user_id': current_user['_id']
                },
                exc_info=True
            )
            raise
        
        if not blog_post:
            logger.error(
                "Failed to save blog post to database",
                extra={
                    'event': 'blog_post_save_failed',
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'Failed to save blog post'}), 500
        
        generation_time = time.time() - start_time
        word_count = len(blog_content.split())
        
        # Store large blog data in temporary storage instead of session
        blog_data = {
            'blog_content': blog_content,
            'youtube_url': youtube_url,
            'video_id': video_id,
            'title': title,
            'generation_time': generation_time,
            'post_id': str(blog_post['_id']),
            'word_count': word_count
        }
        
        # Store in temporary storage and keep only reference in session
        storage_key = store_large_data('current_blog', blog_data, str(current_user['_id']))
        
        # Store only the storage key in session (much smaller)
        session['blog_storage_key'] = storage_key
        session['blog_created'] = time.time()
        
        logger.info(
            "Blog generation completed successfully",
            extra={
                'event': 'blog_generation_completed',
                'user_id': current_user['_id'],
                'username': current_user['username'],
                'title': title,
                'word_count': word_count,
                'generation_time_seconds': generation_time,
                'post_id': str(blog_post['_id']),
                'success': True
            }
        )
        
        return jsonify({
            'success': True,
            'blog_content': blog_content,
            'generation_time': f"{generation_time:.1f}s",
            'word_count': word_count,
            'title': title,
            'video_id': video_id
        })
        
    except Exception as e:
        blog_generation_requests.labels(status='failed').inc()
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Unexpected error during blog generation",
            extra={
                'event': 'unexpected_error',
                'operation': 'blog_generation',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'request_id': request_id,
                'user_id': getattr(current_user, '_id', 'unknown') if 'current_user' in locals() else 'unknown'
            },
            exc_info=True
        )
        return jsonify({'success': False, 'message': f'Error generating blog: {str(e)}'}), 500
    
    finally:
        try:
            full_cleanup(blog_model, user_model)
        except Exception:
            pass

@app.route('/download')
@track_requests
def download_pdf():
    """Generate and download PDF"""
    pdf_generator = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                "Unauthorized PDF download attempt",
                extra={
                    'event': 'unauthorized_access',
                    'operation': 'pdf_download'
                }
            )
            return redirect(url_for('auth.login'))
        
        # Retrieve blog data from temporary storage
        storage_key = session.get('blog_storage_key')
        blog_data = None
        
        if storage_key:
            blog_data = retrieve_large_data('current_blog', str(current_user['_id']))
        
        if not blog_data:
            logger.warning(
                f"PDF download failed: No blog data found for user {current_user['username']}",
                extra={
                    'event': 'pdf_download_failed',
                    'error_type': 'no_data',
                    'user_id': current_user['_id']
                }
            )
            return jsonify({'success': False, 'message': 'No blog data found or expired'}), 404
        
        blog_content = blog_data['blog_content']
        title = blog_data['title']
        
        # Clean filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        filename = f"{safe_title}_blog.pdf"
        
        logger.info(
            f"PDF generation started for user {current_user['username']}: {title}",
            extra={
                'event': 'pdf_generation_started',
                'user_id': current_user['_id'],
                'title': title
            }
        )
        
        # Generate PDF with proper cleanup
        try:
            pdf_generator = PDFGeneratorTool()
            pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
            pdf_downloads.inc()
            logger.info(
                f"PDF download completed successfully for user {current_user['username']}: {filename}",
                extra={
                    'event': 'pdf_download_completed',
                    'user_id': current_user['_id'],
                    'file_name': filename  # Changed from 'filename' to 'file_name'
                }
            )
        finally:
            if pdf_generator:
                pdf_generator = None
            cleanup_after_generation()
        
        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        logger.info(
            f"PDF download completed successfully for user {current_user['username']}: {filename}",
            extra={
                'event': 'pdf_download_completed',
                'user_id': current_user['_id'],
                'file_name': filename
            }
        )
        
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "PDF generation failed",
            extra={
                'event': 'pdf_generation_error',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'user_id': getattr(current_user, '_id', 'unknown') if 'current_user' in locals() else 'unknown'
            },
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': f'PDF generation failed: {str(e)}'
        }), 500
    finally:
        full_cleanup(pdf_generator)

@app.route('/dashboard')
@track_requests
def dashboard():
    """User dashboard"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        
        if not current_user:
            logger.warning(
                "Unauthorized dashboard access",
                extra={
                    'event': 'unauthorized_access',
                    'page': 'dashboard'
                }
            )
            session.clear()
            return redirect(url_for('auth.login'))
        
        logger.info(
            f"Dashboard accessed by user: {current_user['username']}",
            extra={
                'event': 'page_access',
                'page': 'dashboard',
                'user_id': current_user['_id'],
                'username': current_user['username']
            }
        )
        
        blog_model = BlogPost()
        try:
            posts = blog_model.get_user_posts(current_user['_id'])
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='success'
            ).inc()
            logger.info(
                f"Retrieved {len(posts)} posts for user {current_user['username']}",
                extra={
                    'event': 'posts_retrieved',
                    'user_id': current_user['_id'],
                    'post_count': len(posts)
                }
            )
        except Exception as db_error:
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='error'
            ).inc()
            logger.error(
                "Database error retrieving posts",
                extra={
                    'event': 'database_error',
                    'operation': 'read_posts',
                    'error_type': type(db_error).__name__,
                    'error_message': str(db_error),
                    'user_id': current_user['_id']
                },
                exc_info=True
            )
            posts = []
        
        return render_template('dashboard.html', 
                             user=current_user, 
                             posts=posts)
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Dashboard error",
            extra={
                'event': 'dashboard_error',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        session.clear()
        return redirect(url_for('auth.login'))
    finally:
        if blog_model:
            blog_model = None

@app.route('/delete-post/<post_id>', methods=['DELETE'])
@track_requests
def delete_post(post_id):
    """Delete a blog post"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized post deletion attempt for post {post_id}",
                extra={
                    'event': 'unauthorized_access',
                    'operation': 'delete_post',
                    'post_id': post_id
                }
            )
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        logger.info(
            f"Post deletion requested by user {current_user['username']}: {post_id}",
            extra={
                'event': 'post_deletion_started',
                'user_id': current_user['_id'],
                'post_id': post_id
            }
        )
        
        blog_model = BlogPost()
        try:
            success = blog_model.delete_post(post_id, current_user['_id'])
            database_operations.labels(
                operation='delete',
                collection='blog_posts',
                status='success' if success else 'error'
            ).inc()
        except Exception as db_error:
            database_operations.labels(
                operation='delete',
                collection='blog_posts',
                status='error'
            ).inc()
            logger.error(
                "Database error deleting post",
                extra={
                    'event': 'database_error',
                    'operation': 'delete_post',
                    'error_type': type(db_error).__name__,
                    'error_message': str(db_error),
                    'user_id': current_user['_id'],
                    'post_id': post_id
                },
                exc_info=True
            )
            raise
        
        if success:
            logger.info(
                f"Post deleted successfully by user {current_user['username']}: {post_id}",
                extra={
                    'event': 'post_deletion_completed',
                    'user_id': current_user['_id'],
                    'post_id': post_id
                }
            )
            return jsonify({'success': True, 'message': 'Post deleted successfully'})
        else:
            logger.warning(
                f"Post not found for deletion: {post_id}",
                extra={
                    'event': 'post_deletion_failed',
                    'error_type': 'not_found',
                    'user_id': current_user['_id'],
                    'post_id': post_id
                }
            )
            return jsonify({'success': False, 'message': 'Post not found'}), 404
            
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            f"Error deleting post {post_id}",
            extra={
                'event': 'post_deletion_error',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'post_id': post_id
            },
            exc_info=True
        )
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if blog_model:
            blog_model = None

@app.route('/contact')
@track_requests
def contact():
    """Contact page"""
    try:
        logger.info(
            "Contact page accessed",
            extra={
                'event': 'page_access',
                'page': 'contact'
            }
        )
        return render_template('contact.html')
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Error loading contact page",
            extra={
                'event': 'page_error',
                'page': 'contact',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return render_template('error.html', 
                             error=f"Error loading contact page: {str(e)}"), 500

@app.route('/get-post/<post_id>')
@track_requests
def get_post(post_id):
    """Get a specific blog post for viewing"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized post access attempt for post {post_id}",
                extra={
                    'event': 'unauthorized_access',
                    'operation': 'get_post',
                    'post_id': post_id
                }
            )
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        logger.info(
            f"Post retrieval requested by user {current_user['username']}: {post_id}",
            extra={
                'event': 'post_retrieval_started',
                'user_id': current_user['_id'],
                'post_id': post_id
            }
        )
        
        blog_model = BlogPost()
        try:
            post = blog_model.get_post_by_id(post_id, current_user['_id'])
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='success'
            ).inc()
        except Exception as db_error:
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='error'
            ).inc()
            logger.error(
                "Database error retrieving post",
                extra={
                    'event': 'database_error',
                    'operation': 'get_post',
                    'error_type': type(db_error).__name__,
                    'error_message': str(db_error),
                    'user_id': current_user['_id'],
                    'post_id': post_id
                },
                exc_info=True
            )
            raise
        
        if post:
            logger.info(
                f"Post retrieved successfully: {post_id}",
                extra={
                    'event': 'post_retrieval_completed',
                    'user_id': current_user['_id'],
                    'post_id': post_id
                }
            )
            return jsonify({
                'success': True,
                'post': post
            })
        else:
            logger.warning(
                f"Post not found: {post_id}",
                extra={
                    'event': 'post_retrieval_failed',
                    'error_type': 'not_found',
                    'user_id': current_user['_id'],
                    'post_id': post_id
                }
            )
            return jsonify({'success': False, 'message': 'Post not found'}), 404
            
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            f"Error retrieving post {post_id}",
            extra={
                'event': 'post_retrieval_error',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'post_id': post_id
            },
            exc_info=True
        )
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if blog_model:
            blog_model = None

@app.route('/download-post/<post_id>')
@track_requests
def download_post_pdf(post_id):
    """Download PDF for a specific blog post"""
    pdf_generator = None
    blog_model = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            logger.warning(
                f"Unauthorized PDF download attempt for post {post_id}",
                extra={
                    'event': 'unauthorized_access',
                    'operation': 'download_post_pdf',
                    'post_id': post_id
                }
            )
            return redirect(url_for('auth.login'))
        
        logger.info(
            f"PDF download requested by user {current_user['username']} for post: {post_id}",
            extra={
                'event': 'post_pdf_download_started',
                'user_id': current_user['_id'],
                'post_id': post_id
            }
        )
        
        blog_model = BlogPost()
        try:
            post = blog_model.get_post_by_id(post_id, current_user['_id'])
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='success'
            ).inc()
        except Exception as db_error:
            database_operations.labels(
                operation='read',
                collection='blog_posts',
                status='error'
            ).inc()
            logger.error(
                "Database error retrieving post for PDF",
                extra={
                    'event': 'database_error',
                    'operation': 'get_post_for_pdf',
                    'error_type': type(db_error).__name__,
                    'error_message': str(db_error),
                    'user_id': current_user['_id'],
                    'post_id': post_id
                },
                exc_info=True
            )
            raise
        
        if not post:
            logger.warning(
                f"Post not found for PDF download: {post_id}",
                extra={
                    'event': 'post_pdf_download_failed',
                    'error_type': 'not_found',
                    'user_id': current_user['_id'],
                    'post_id': post_id
                }
            )
            return jsonify({'success': False, 'message': 'Post not found'}), 404
        
        blog_content = post['content']
        title = post['title']
        
        # Clean filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        filename = f"{safe_title}_blog.pdf"
        
        logger.info(
            f"PDF generation started for post {post_id}: {title}",
            extra={
                'event': 'post_pdf_generation_started',
                'user_id': current_user['_id'],
                'post_id': post_id,
                'title': title
            }
        )
        
        # Generate PDF
        try:
            pdf_generator = PDFGeneratorTool()
            pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
            pdf_downloads.inc()
            logger.info(
                f"PDF generated successfully for post {post_id}: {len(pdf_bytes)} bytes",
                extra={
                    'event': 'post_pdf_generation_completed',
                    'user_id': current_user['_id'],
                    'post_id': post_id,
                    'file_size': len(pdf_bytes)
                }
            )
        finally:
            if pdf_generator:
                pdf_generator = None
            cleanup_after_generation()
        
        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        logger.info(
            f"PDF download completed for post {post_id} by user {current_user['username']}",
            extra={
                'event': 'post_pdf_download_completed',
                'user_id': current_user['_id'],
                'post_id': post_id,
                'file_name': filename  # Changed from 'filename' to 'file_name'
            }
    )
        
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            f"PDF generation failed for post {post_id}",
            extra={
                'event': 'post_pdf_generation_error',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'post_id': post_id
            },
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': f'PDF generation failed: {str(e)}'
        }), 500
    finally:
        if blog_model:
            blog_model = None
        full_cleanup(pdf_generator, blog_model)

# ========== METRICS ENDPOINT ==========
@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        return "Error generating metrics", 500

# Health check endpoint for monitoring
@app.route('/health')
@track_requests
def health_check():
    """Health check endpoint with detailed system information"""
    try:
        from auth.models import mongo_manager
        
        # Check database connection
        db_connected = mongo_manager.is_connected()
        
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data = {
            'status': 'healthy' if db_connected else 'unhealthy',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'database': 'connected' if db_connected else 'disconnected',
            'secret_key_set': bool(app.secret_key),
            'temp_storage_items': len(app.temp_storage),
            'loki_url': os.getenv('LOKI_URL', 'not_configured'),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': round((disk.used / disk.total) * 100, 2),
                'disk_free_gb': round(disk.free / (1024**3), 2)
            },
            'application': {
                'version': '1.0.0',
                'environment': os.getenv('FLASK_ENV', 'production'),
                'uptime_seconds': int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
            }
        }
        
        status_code = 200 if db_connected else 503
        
        # Enhanced health check logging for Loki
        logger.info(
            "Health check performed",
            extra={
                'event': 'health_check',
                'status': health_data['status'],
                'database': health_data['database'],
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'loki_configured': bool(os.getenv('LOKI_URL'))
            }
        )
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(
            "Health check error",
            extra={
                'event': 'health_check_error',
                'error_type': type(e).__name__,
                'error_message': str(e)
            },
            exc_info=True
        )
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'error': str(e),
            'secret_key_set': bool(app.secret_key)
        }), 503

# Add this new route for Prometheus health metrics
@app.route('/health-metrics')
@track_requests
def health_metrics():
    """Prometheus-compatible health metrics endpoint"""
    try:
        from auth.models import mongo_manager
        
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check database connection
        db_connected = mongo_manager.is_connected()
        
        # Generate Prometheus metrics format
        metrics = []
        
        # Health status (1 = healthy, 0 = unhealthy)
        health_status = 1 if db_connected else 0
        metrics.append(f'azure_app_health_status {health_status}')
        
        # Database status (1 = connected, 0 = disconnected)
        db_status = 1 if db_connected else 0
        metrics.append(f'azure_app_database_status {db_status}')
        
        # System metrics
        metrics.append(f'azure_app_cpu_percent {cpu_percent}')
        metrics.append(f'azure_app_memory_percent {memory.percent}')
        metrics.append(f'azure_app_memory_used_bytes {memory.used}')
        metrics.append(f'azure_app_memory_total_bytes {memory.total}')
        metrics.append(f'azure_app_disk_percent {round((disk.used / disk.total) * 100, 2)}')
        metrics.append(f'azure_app_disk_used_bytes {disk.used}')
        metrics.append(f'azure_app_disk_total_bytes {disk.total}')
        
        # Application metrics
        metrics.append(f'azure_app_temp_storage_items {len(app.temp_storage)}')
        metrics.append(f'azure_app_uptime_seconds {int(time.time() - app.start_time) if hasattr(app, "start_time") else 0}')
        
        # Join all metrics
        response_text = '\n'.join(metrics) + '\n'
        
        return Response(response_text, mimetype='text/plain')
        
    except Exception as e:
        application_errors.labels(error_type=type(e).__name__).inc()
        logger.error(f"Health metrics error: {e}", exc_info=True)
        # Return error metric
        error_response = f'azure_app_health_status 0\nazure_app_error {{error="{str(e)}"}} 1\n'
        return Response(error_response, mimetype='text/plain'), 503

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    application_errors.labels(error_type='401_Unauthorized').inc()
    logger.warning(
        f"Unauthorized access attempt from {request.remote_addr}",
        extra={
            'event': 'unauthorized_access',
            'remote_addr': request.remote_addr,
            'url': request.url
        }
    )
    return redirect(url_for('auth.login'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    application_errors.labels(error_type='404_NotFound').inc()
    logger.warning(
        f"404 error for {request.url}",
        extra={
            'event': '404_error',
            'url': request.url,
            'method': request.method
        }
    )
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    application_errors.labels(error_type='500_InternalError').inc()
    logger.error(
        f"Internal server error: {error}",
        extra={
            'event': '500_error',
            'error_message': str(error),
            'url': request.url,
            'method': request.method
        },
        exc_info=True
    )
    return render_template('error.html', error="Internal server error"), 500

# Application shutdown cleanup
@app.teardown_appcontext
def cleanup_app_context(error):
    """Cleanup resources on app context teardown"""
    try:
        cleanup_memory()
    except Exception:
        pass

if __name__ == '__main__':
    # Set application start time for uptime calculation
    app.start_time = time.time()
    
    # Verify everything is set up correctly before starting
    logger.info("\n=== Pre-startup Verification ===")
    logger.info(f"Secret key set: {bool(app.secret_key)}")
    logger.info(f"Secret key length: {len(app.secret_key) if app.secret_key else 0}")
    logger.info(f"JWT configured: {bool(app.config.get('JWT_SECRET_KEY'))}")
    logger.info("Using Flask's built-in sessions with size optimization")
    logger.info("Prometheus metrics enabled on /metrics endpoint")
    logger.info("Enhanced logging configured for Loki integration")
    logger.info(f"Loki URL: {os.getenv('LOKI_URL', 'NOT_SET')}")
    
    # Configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    # Validate required environment variables
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key',
        'SUPADATA_API_KEY': 'Supadata API key',
        'MONGODB_URI': 'MongoDB connection URI',
        'LOKI_URL': 'Loki server URL (format: http://YOUR_DROPLET_IP:3100)'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        if 'LOKI_URL' in [var.split(' ')[0] for var in missing_vars]:
            logger.warning("Loki integration will be disabled without LOKI_URL")
    
    logger.info(f"\nStarting application on {host}:{port}")
    logger.info("=================================\n")
    
    try:
        app.run(host=host, port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            full_cleanup()
            logger.info("Application shutdown cleanup completed")
        except Exception:
            pass
