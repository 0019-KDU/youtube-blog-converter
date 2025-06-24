import os
import sys
import io
from flask import Flask, render_template, request, send_file, redirect, url_for, session

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import application components
from src.main import generate_blog_from_youtube
from src.tool import PDFTool

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

@app.route('/', methods=['GET'])
def index():
    """Render the main form page"""
    # Clear any previous session data
    session.pop('result_data', None)
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
        
        # Store in session
        session['result_data'] = {
            'blog_content': blog_content,
            'youtube_url': youtube_url
        }
        
        return redirect(url_for('results'))
    
    except Exception as e:
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/results', methods=['GET'])
def results():
    """Show generated blog content"""
    result_data = session.get('result_data', {})
    if not result_data:
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                           blog_content=result_data['blog_content'],
                           youtube_url=result_data['youtube_url'])

@app.route('/download', methods=['GET'])
def download_pdf():
    """Generate and download the PDF on demand"""
    result_data = session.get('result_data', {})
    
    # Validate session data
    if not result_data or 'blog_content' not in result_data or 'youtube_url' not in result_data:
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
        session.pop('result_data', None)
        return response
        
    except Exception as e:
        return render_template('error.html', error=f"PDF generation failed: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)