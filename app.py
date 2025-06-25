# app.py
import os
import sys
import io
import uuid
from flask import Flask, render_template, request, send_file, redirect, url_for, session
from flask_session import Session

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import application components
from src.main import generate_blog_from_youtube
from src.tool import PDFTool

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = False  # Disable signer to avoid bytes issue
Session(app)

@app.route('/', methods=['GET'])
def index():
    """Render the main form page"""
    # Clear any previous session data
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
        content_id = str(uuid.uuid4())  # Ensure it's a string
        
        # Store in server-side session
        session[content_id] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url
        }
        
        # Store only ID in client-side cookie
        session['content_id'] = content_id
        
        return redirect(url_for('results'))
    
    except Exception as e:
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/results', methods=['GET'])
def results():
    """Show generated blog content"""
    content_id = session.get('content_id')
    if not content_id:
        return redirect(url_for('index'))
    
    # Ensure content_id is string
    content_id = str(content_id)
    
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
    
    # Ensure content_id is string
    content_id = str(content_id)
    
    result_data = session.get(content_id, {})
    if not result_data:
        return redirect(url_for('index'))
    
    try:
        # Generate in-memory PDF
        pdf_tool = PDFTool()
        pdf_bytes = pdf_tool.generate_pdf_bytes(result_data['blog_content'])
        
        # Create in-memory file
        response = send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name='blog_article.pdf',
            mimetype='application/pdf'
        )
        
        # Clear session after download
        session.pop(content_id, None)
        session.pop('content_id', None)
        return response
        
    except Exception as e:
        return render_template('error.html', error=f"PDF generation failed: {str(e)}")

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    if not os.path.exists(app.config['SESSION_FILE_DIR']):
        os.makedirs(app.config['SESSION_FILE_DIR'])
    
    app.run(host='0.0.0.0', port=5000, debug=True)