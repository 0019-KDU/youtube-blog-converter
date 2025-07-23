import os
import re
import sys
import io
import uuid
import logging
import time
import datetime
import gc
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify
from flask_session import Session
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, decode_token
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("Loaded environment variables from .env file")
else:
    load_dotenv()

# Initialize Flask app
app = Flask(__name__)

def get_secret_key():
    """Get Flask secret key from environment"""
    secret_key = os.getenv('JWT_SECRET_KEY') or os.getenv('FLASK_SECRET_KEY')
    
    if not secret_key:
        logger.warning("No Flask secret key found in environment variables!")
        import secrets
        secret_key = secrets.token_hex(32)
        logger.warning(f"Generated temporary key for session")
    
    return secret_key

app.secret_key = get_secret_key()

# JWT Configuration
app.config['JWT_SECRET_KEY'] = get_secret_key()
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(
    seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
)

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# Initialize JWT
jwt = JWTManager(app)

# Import application components
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from src.main import generate_blog_from_youtube
    from src.tool import PDFGeneratorTool
    from auth.models import User, BlogPost
    from auth.routes import auth_bp
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

# Register authentication blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

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
                pass  # pythoncom not available
            except Exception:
                pass  # Ignore COM cleanup errors
    except Exception as e:
        logger.debug(f"COM cleanup warning: {str(e)}")

def cleanup_memory():
    """Force garbage collection and memory cleanup"""
    try:
        # Force garbage collection
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")
        
        # Clear any remaining cycles
        gc.collect()
        
        # Reset debug flags
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
        # Cleanup database objects
        cleanup_database_connections(args)
        
        # Cleanup COM objects
        cleanup_com_objects()
        
        # Cleanup memory
        cleanup_memory()
        
    except Exception as e:
        logger.warning(f"Full cleanup warning: {str(e)}")

def cleanup_after_generation():
    """Helper function to clean up resources after blog generation"""
    try:
        # Force garbage collection multiple times for better cleanup
        for _ in range(3):
            gc.collect()
        
        # Platform-specific cleanup
        if sys.platform.startswith('win'):
            cleanup_com_objects()
        
        # Additional memory management
        cleanup_memory()
                
    except Exception as e:
        logger.warning(f"Resource cleanup warning: {str(e)}")

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
                # Clear invalid token
                session.pop('access_token', None)
        
        return None
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return None
    finally:
        # Cleanup user model
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
            
            # Convert moment.js format to Python strftime
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
def index():
    """Render the main landing page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Index page error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/generate-page')
def generate_page():
    """Render the generate blog page with left/right layout"""
    try:
        current_user = get_current_user()
        if not current_user:
            return redirect(url_for('auth.login'))
        
        return render_template('generate.html')
    except Exception as e:
        logger.error(f"Generate page error: {str(e)}")
        return render_template('error.html', 
                             error=f"Error loading generate page: {str(e)}"), 500

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog - returns JSON for AJAX"""
    start_time = time.time()
    blog_model = None
    user_model = None
    
    try:
        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Get form data
        youtube_url = request.form.get('youtube_url', '').strip()
        language = request.form.get('language', 'en')
        
        if not youtube_url:
            return jsonify({'success': False, 'message': 'YouTube URL is required'}), 400
        
        # Validate URL format
        if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', youtube_url):
            return jsonify({'success': False, 'message': 'Please enter a valid YouTube URL'}), 400
        
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({'success': False, 'message': 'Invalid YouTube URL'}), 400
        
        logger.info(f"Starting blog generation for URL: {youtube_url} by user: {current_user['username']}")
        
        # Generate blog content with proper error handling
        blog_content = None
        try:
            blog_content = generate_blog_from_youtube(youtube_url, language)
        except Exception as gen_error:
            logger.error(f"Blog generation failed: {str(gen_error)}")
            return jsonify({'success': False, 'message': f'Failed to generate blog: {str(gen_error)}'}), 500
        finally:
            # Force cleanup after generation to prevent Win32 exceptions
            cleanup_after_generation()
        
        # Check if generation was successful
        if not blog_content or len(blog_content) < 100:
            return jsonify({'success': False, 'message': 'Failed to generate blog content. Please try with a different video.'}), 500
        
        # Check for error responses
        if blog_content.startswith("ERROR:"):
            error_msg = blog_content.replace("ERROR:", "").strip()
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
            logger.error("Failed to save blog post to database")
            return jsonify({'success': False, 'message': 'Failed to save blog post'}), 500
        
        # Store in session for PDF generation
        session['current_blog'] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url,
            'video_id': video_id,
            'title': title,
            'generation_time': time.time() - start_time,
            'post_id': str(blog_post['_id']),
            'word_count': len(blog_content.split())
        }
        
        duration = time.time() - start_time
        logger.info(f"Blog generated successfully in {duration:.2f}s for user: {current_user['username']}")
        
        # Return JSON response for AJAX
        return jsonify({
            'success': True,
            'blog_content': blog_content,
            'generation_time': f"{duration:.1f}s",
            'word_count': len(blog_content.split()),
            'title': title,
            'video_id': video_id
        })
        
    except Exception as e:
        logger.error(f"Blog generation failed: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Error generating blog: {str(e)}'}), 500
    
    finally:
        # Comprehensive cleanup to prevent memory leaks and Win32 exceptions
        try:
            full_cleanup(blog_model, user_model)
        except Exception as cleanup_error:
            logger.warning(f"Final cleanup warning: {str(cleanup_error)}")

@app.route('/download')
def download_pdf():
    """Generate and download PDF"""
    pdf_generator = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            return redirect(url_for('auth.login'))
        
        blog_data = session.get('current_blog')
        if not blog_data:
            return jsonify({'success': False, 'message': 'No blog data found'}), 404
        
        blog_content = blog_data['blog_content']
        title = blog_data['title']
        
        # Clean filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:50]
        filename = f"{safe_title}_blog.pdf"
        
        logger.info(f"Generating PDF: {filename} for user: {current_user['username']}")
        
        # Generate PDF with proper cleanup
        try:
            pdf_generator = PDFGeneratorTool()
            pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
        finally:
            # Cleanup PDF generator immediately after use
            if pdf_generator:
                pdf_generator = None
            cleanup_after_generation()
        
        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        logger.info(f"PDF generated successfully: {filename} ({len(pdf_bytes)} bytes)")
        
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'PDF generation failed: {str(e)}'
        }), 500
    finally:
        # Final cleanup for PDF generation
        full_cleanup(pdf_generator)

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        
        if not current_user:
            session.clear()
            logger.warning("Dashboard access denied - no valid user session")
            return redirect(url_for('auth.login'))
        
        logger.info(f"Dashboard accessed by user: {current_user.get('username', 'Unknown')}")
        
        blog_model = BlogPost()
        posts = blog_model.get_user_posts(current_user['_id'])
        
        return render_template('dashboard.html', 
                             user=current_user, 
                             posts=posts)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        session.clear()
        return redirect(url_for('auth.login'))
    finally:
        # Cleanup blog model
        if blog_model:
            blog_model = None

@app.route('/delete-post/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    """Delete a blog post"""
    blog_model = None
    
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        blog_model = BlogPost()
        success = blog_model.delete_post(post_id, current_user['_id'])
        
        if success:
            return jsonify({'success': True, 'message': 'Post deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Post not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        # Cleanup blog model
        if blog_model:
            blog_model = None

@app.route('/contact')
def contact():
    """Contact page"""
    try:
        return render_template('contact.html')
    except Exception as e:
        logger.error(f"Contact page error: {str(e)}")
        return render_template('error.html', 
                             error=f"Error loading contact page: {str(e)}"), 500

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access"""
    return redirect(url_for('auth.login'))

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('error.html', error="Internal server error"), 500

# Application shutdown cleanup
@app.teardown_appcontext
def cleanup_app_context(error):
    """Cleanup resources on app context teardown"""
    try:
        cleanup_memory()
    except Exception as e:
        logger.debug(f"App context cleanup warning: {str(e)}")

if __name__ == '__main__':
    # Create session directory
    session_dir = app.config['SESSION_FILE_DIR']
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
    
    logger.info(f"Starting application on {host}:{port}")
    
    try:
        app.run(host=host, port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)
    finally:
        # Final cleanup on application shutdown
        try:
            full_cleanup()
            logger.info("Application shutdown cleanup completed")
        except Exception as e:
            logger.warning(f"Shutdown cleanup warning: {str(e)}")
