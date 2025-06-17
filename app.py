import os
import sys
from flask import Flask, render_template, request, send_file, redirect, url_for

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

app = Flask(__name__)

# Global variable to store results between requests
result_data = {}

@app.route('/', methods=['GET'])
def index():
    """Render the main form page"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog"""
    global result_data
    
    youtube_url = request.form['youtube_url']
    
    if not youtube_url:
        return render_template('index.html', error="YouTube URL is required")
    
    try:
        # Generate blog content and PDF
        from src.main import generate_blog_from_youtube
        blog_content, pdf_path = generate_blog_from_youtube(youtube_url)
        
        # Store results for display and download
        result_data = {
            'blog_content': blog_content,
            'pdf_path': pdf_path,
            'youtube_url': youtube_url
        }
        
        return redirect(url_for('results'))
    
    except Exception as e:
        return render_template('index.html', error=f"Error: {str(e)}")

@app.route('/results', methods=['GET'])
def results():
    """Show generated blog content"""
    global result_data
    if not result_data:
        return redirect(url_for('index'))
    
    return render_template('results.html', 
                           blog_content=result_data['blog_content'],
                           youtube_url=result_data['youtube_url'])

@app.route('/download', methods=['GET'])
def download_pdf():
    """Download the generated PDF"""
    global result_data
    if not result_data or not os.path.exists(result_data['pdf_path']):
        return redirect(url_for('index'))
    
    return send_file(
        result_data['pdf_path'],
        as_attachment=True,
        download_name='blog_article.pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Fixed this line