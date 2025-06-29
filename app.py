import os
import sys
import io
import uuid
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the path to the .env file in the project root
env_path = Path(__file__).resolve().parent / '.env'
logger.info(f"Loading environment from: {env_path}")

if env_path.exists():
    logger.info(".env file found, loading environment variables")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(".env file not found, falling back to system environment")
    load_dotenv()  # Fallback to default loading

# Debug: Check OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
logger.info(f"OPENAI_API_KEY loaded: {'Yes' if api_key else 'No'}")

# Now create the Flask app
from flask import Flask, render_template, request, send_file, redirect, url_for, session
from flask_session import Session

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'

# Initialize Flask-Session extension
Session(app)

# Import application components after environment is loaded
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from src.main import generate_blog_from_youtube
    from src.tool import PDFTool
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

@app.route('/', methods=['GET'])
def index():
    """Render the main form page"""
    session.clear()
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog"""
    youtube_url = request.form['youtube_url']
    language = request.form.get('language', 'en')
    
    if not youtube_url:
        return render_template('index.html', error="YouTube URL is required")
    
    try:
        # Generate blog content
        blog_content = generate_blog_from_youtube(youtube_url, language)
        
        # Generate unique ID for content
        content_id = str(uuid.uuid4())
        
        # Store in session
        session[content_id] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url
        }
        session['content_id'] = content_id
        
        return redirect(url_for('results'))
    
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/results', methods=['GET'])
def results():
    """Show generated blog content"""
    content_id = session.get('content_id')
    if not content_id:
        return redirect(url_for('index'))
    
    result_data = session.get(content_id, {})
    if not result_data:
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                           blog_content=result_data['blog_content'],
                           youtube_url=result_data['youtube_url'])

@app.route('/download', methods=['GET'])
def download_pdf():
    """Generate and download the PDF"""
    content_id = session.get('content_id')
    if not content_id:
        return redirect(url_for('index'))
    
    result_data = session.get(content_id, {})
    if not result_data:
        return redirect(url_for('index'))
    
    try:
        # Generate in-memory PDF
        pdf_tool = PDFTool()
        pdf_bytes = pdf_tool.generate_pdf_bytes(result_data['blog_content'])
        
        # Create in-memory file
        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name='blog_article.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        return render_template('error.html', error=f"PDF generation failed: {str(e)}")

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)