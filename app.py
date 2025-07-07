import os
import re
import sys
import io
import uuid
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify
from flask_session import Session

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
    secret_key = os.getenv('FLASK_SECRET_KEY')
    
    if not secret_key:
        logger.warning("No Flask secret key found in environment variables!")
        import secrets
        secret_key = secrets.token_hex(32)
        logger.warning(f"Generated temporary key for session")
    
    return secret_key

app.secret_key = get_secret_key()

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

# Import application components
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from src.main import generate_blog_from_youtube
    from src.tool import PDFGeneratorTool
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

@app.route('/')
def index():
    """Render the main form page"""
    try:
        session.clear()
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Index page error: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog with enhanced error handling"""
    start_time = time.time()
    
    try:
        youtube_url = request.form.get('youtube_url', '').strip()
        language = request.form.get('language', 'en')
        
        if not youtube_url:
            return render_template('index.html', error="YouTube URL is required"), 400
        
        # Validate URL format
        if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', youtube_url):
            return render_template('index.html', error="Please enter a valid YouTube URL"), 400
        
        logger.info(f"Starting blog generation for URL: {youtube_url}")
        
        # Generate blog content with enhanced error handling
        try:
            blog_content = generate_blog_from_youtube(youtube_url, language)
        except Exception as gen_error:
            logger.error(f"Blog generation failed: {str(gen_error)}")
            error_msg = f"Failed to generate blog: {str(gen_error)}"
            return render_template('index.html', error=error_msg), 500
        
        # Check if generation was successful
        if not blog_content or len(blog_content) < 100:
            error_msg = "Failed to generate blog content. Please try with a different video."
            return render_template('index.html', error=error_msg), 500
        
        # Check for error responses
        if blog_content.startswith("ERROR:"):
            error_msg = blog_content.replace("ERROR:", "").strip()
            return render_template('index.html', error=error_msg), 500
        
        # Generate unique ID for content
        content_id = str(uuid.uuid4())
        
        # Store in session
        session[content_id] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url,
            'generation_time': time.time() - start_time,
            'timestamp': time.time()
        }
        session['content_id'] = content_id
        
        duration = time.time() - start_time
        logger.info(f"Blog generated successfully in {duration:.2f}s")
        return redirect(url_for('results'))
        
    except Exception as e:
        logger.error(f"Blog generation failed: {str(e)}", exc_info=True)
        error_msg = f"Error generating blog: {str(e)}"
        return render_template('index.html', error=error_msg), 500

@app.route('/results')
def results():
    """Show generated blog content with enhanced display"""
    try:
        content_id = session.get('content_id')
        if not content_id:
            return redirect(url_for('index'))
        
        result_data = session.get(content_id, {})
        if not result_data:
            return redirect(url_for('index'))
        
        # Extract video info for display
        youtube_url = result_data.get('youtube_url', '')
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', youtube_url)
        video_id = video_id_match.group(1) if video_id_match else 'unknown'
        
        # Calculate content stats
        blog_content = result_data.get('blog_content', '')
        word_count = len(blog_content.split())
        char_count = len(blog_content)
        
        return render_template('results.html', 
                             blog_content=blog_content,
                             youtube_url=youtube_url,
                             video_id=video_id,
                             generation_time=result_data.get('generation_time', 0),
                             word_count=word_count,
                             char_count=char_count)
    except Exception as e:
        logger.error(f"Results page error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download')
def download_pdf():
    """Generate and download PDF with enhanced error handling"""
    try:
        content_id = session.get('content_id')
        if not content_id:
            return redirect(url_for('index'))
        
        result_data = session.get(content_id, {})
        if not result_data or 'blog_content' not in result_data:
            return redirect(url_for('index'))
        
        blog_content = result_data['blog_content']
        youtube_url = result_data.get('youtube_url', '')
        
        # Extract video ID for filename
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', youtube_url)
        safe_name = f"blog_{video_id_match.group(1)}.pdf" if video_id_match else "blog_article.pdf"
        
        # Generate PDF
        pdf_generator = PDFGeneratorTool()
        pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
        
        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        logger.info(f"PDF generated successfully: {safe_name}")
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=safe_name,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
        
        # Fallback to text file
        try:
            content_id = session.get('content_id')
            result_data = session.get(content_id, {})
            blog_content = result_data.get('blog_content', 'Content not available')
            
            mem_file = io.BytesIO(blog_content.encode('utf-8'))
            mem_file.seek(0)
            return send_file(
                mem_file,
                as_attachment=True,
                download_name='blog_article.txt',
                mimetype='text/plain'
            )
        except Exception as fallback_error:
            logger.error(f"Fallback download failed: {str(fallback_error)}")
            return redirect(url_for('results'))

@app.route('/api/status')
def api_status():
    """API endpoint to check application status"""
    try:
        # Check environment variables
        openai_key = bool(os.getenv('OPENAI_API_KEY'))
        
        status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'environment': {
                'openai_configured': openai_key,
                'session_dir_exists': os.path.exists(app.config['SESSION_FILE_DIR'])
            }
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/validate-url', methods=['POST'])
def validate_youtube_url():
    """API endpoint to validate YouTube URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'valid': False, 'message': 'URL is required'})
        
        # Check URL format
        if not re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be)/', url):
            return jsonify({'valid': False, 'message': 'Invalid YouTube URL format'})
        
        # Extract video ID
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
        if not video_id_match:
            return jsonify({'valid': False, 'message': 'Could not extract video ID'})
        
        video_id = video_id_match.group(1)
        
        return jsonify({
            'valid': True, 
            'video_id': video_id,
            'message': 'Valid YouTube URL'
        })
        
    except Exception as e:
        logger.error(f"URL validation failed: {str(e)}")
        return jsonify({'valid': False, 'message': 'Validation error'}), 500

@app.route('/clear-session')
def clear_session():
    """Clear current session and redirect to home"""
    try:
        session.clear()
        logger.info("Session cleared successfully")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Session clear failed: {str(e)}")
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('index.html', error="Internal server error occurred"), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors"""
    logger.warning("Request entity too large")
    return render_template('index.html', error="Request too large"), 413

@app.before_request
def before_request():
    """Log all requests for debugging"""
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")

@app.after_request
def after_request(response):
    """Log response status"""
    logger.info(f"Response: {response.status_code} for {request.path}")
    return response

def cleanup_old_sessions():
    """Clean up old session files"""
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        if os.path.exists(session_dir):
            current_time = time.time()
            for filename in os.listdir(session_dir):
                file_path = os.path.join(session_dir, filename)
                if os.path.isfile(file_path):
                    # Remove files older than 24 hours
                    if current_time - os.path.getmtime(file_path) > 86400:
                        os.remove(file_path)
                        logger.info(f"Removed old session file: {filename}")
    except Exception as e:
        logger.error(f"Session cleanup failed: {str(e)}")

def get_env_var(name, default=None):
    """Get environment variable with fallback"""
    return os.getenv(name) or default

if __name__ == '__main__':
    # Create session directory
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        logger.info(f"Created session directory: {session_dir}")
    
    # Clean up old sessions on startup
    cleanup_old_sessions()
    
    # Configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = get_env_var('FLASK_DEBUG', 'False').lower() == 'true'
    host = get_env_var('FLASK_HOST', '0.0.0.0')
    
    # Validate required environment variables
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not found in environment variables!")
        logger.error("Please set your OpenAI API key before running the application")
        sys.exit(1)
    
    logger.info(f"Starting application on {host}:{port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Session directory: {session_dir}")
    
    try:
        app.run(host=host, port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)
