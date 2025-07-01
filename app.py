# app.py
import os
import re
import sys
import io
import uuid
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, redirect, url_for, session
from flask_session import Session
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from prometheus_client import start_http_server, Counter, Histogram
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logger.info("Loaded environment variables from .env file")
else:
    logger.warning(".env file not found, using system environment variables")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Configure server-side sessions
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

# Global variables for metrics
REQUEST_COUNT = None
REQUEST_LATENCY = None

# OpenTelemetry Initialization
def init_telemetry(app):
    """Initialize OpenTelemetry with proper error handling"""
    global REQUEST_COUNT, REQUEST_LATENCY
    
    try:
        # Set resource attributes - Fixed the Resource creation
        resource = Resource(attributes={
            "service.name": "blog-generator",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "production")
        })
        
        # Tracing setup
        trace.set_tracer_provider(TracerProvider(resource=resource))
        
        # Only set up OTLP if endpoint is configured
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True
            )
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            logger.info(f"OTLP tracing configured for endpoint: {otlp_endpoint}")
        else:
            logger.info("OTLP_ENDPOINT not set, skipping OTLP tracing setup")
        
        # Instrument Flask
        FlaskInstrumentor().instrument_app(app)

        # Metrics setup
        try:
            start_http_server(8000)
            REQUEST_COUNT = Counter(
                'http_requests_total',
                'Total HTTP Requests',
                ['method', 'endpoint', 'status_code']
            )
            REQUEST_LATENCY = Histogram(
                'http_request_duration_seconds',
                'HTTP Request Duration',
                ['endpoint']
            )
            logger.info("Prometheus metrics server started on port 8000")
        except Exception as metrics_error:
            logger.warning(f"Failed to start metrics server: {metrics_error}")

        # Logging setup - only if OTLP endpoint is configured
        if otlp_endpoint:
            try:
                logger_provider = LoggerProvider(resource=resource)
                set_logger_provider(logger_provider)
                otlp_log_exporter = OTLPLogExporter(
                    endpoint=otlp_endpoint,
                    insecure=True
                )
                logger_provider.add_log_record_processor(
                    BatchLogRecordProcessor(otlp_log_exporter)
                )
                handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
                
                # Configure root logger
                root_logger = logging.getLogger()
                root_logger.addHandler(handler)
                root_logger.setLevel(logging.INFO)
                logger.info("OTLP logging configured")
            except Exception as logging_error:
                logger.warning(f"Failed to configure OTLP logging: {logging_error}")
        
        logger.info("Telemetry initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Telemetry initialization failed: {str(e)}")
        # Continue without telemetry rather than crashing
        logger.info("Continuing without full telemetry setup")

# Initialize telemetry
init_telemetry(app)

# Import application components after environment is loaded
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from src.main import generate_blog_from_youtube
    from src.tool import PDFGeneratorTool
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    raise

# Metrics middleware
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if REQUEST_LATENCY and REQUEST_COUNT:
        try:
            latency = time.time() - request.start_time
            REQUEST_LATENCY.labels(request.path).observe(latency)
            REQUEST_COUNT.labels(
                request.method, 
                request.path, 
                response.status_code
            ).inc()
        except Exception as e:
            logger.warning(f"Metrics recording failed: {e}")
    return response

@app.route('/', methods=['GET'])
def index():
    """Render the main form page"""
    session.clear()
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_blog():
    """Process YouTube URL and generate blog"""
    logger = logging.getLogger(__name__)
    logger.info("Starting blog generation")
    
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
        
        logger.info("Blog generated successfully")
        return redirect(url_for('results'))
    
    except Exception as e:
        logger.error(f"Blog generation failed: {str(e)}", exc_info=True)
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
    logger = logging.getLogger(__name__)
    logger.info("Generating PDF download")
    
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
    
    try:
        # Generate PDF with validation
        pdf_generator = PDFGeneratorTool()
        pdf_bytes = pdf_generator.generate_pdf_bytes(blog_content)
        
        # Create in-memory file
        mem_file = io.BytesIO()
        mem_file.write(pdf_bytes)
        mem_file.seek(0)
        
        logger.info("PDF generated successfully")
        return send_file(
            mem_file,
            as_attachment=True,
            download_name=safe_name,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}", exc_info=True)
        
        # Generate a simple fallback PDF
        try:
            mem_file = io.BytesIO()
            p = canvas.Canvas(mem_file, pagesize=letter)
            p.setFont("Helvetica", 12)
            
            # Add title
            p.drawString(100, 750, "Blog Article")
            p.drawString(100, 730, f"Based on YouTube video: {youtube_url}")
            p.line(100, 725, 500, 725)
            
            # Add content (first 2000 characters)
            y_position = 700
            text = blog_content[:2000]
            text_object = p.beginText(100, y_position)
            text_object.setFont("Helvetica", 10)
            text_object.textLines(text)
            p.drawText(text_object)
            
            # Save PDF
            p.showPage()
            p.save()
            
            mem_file.seek(0)
            logger.warning("Used fallback PDF method")
            return send_file(
                mem_file,
                as_attachment=True,
                download_name=safe_name,
                mimetype='application/pdf'
            )
            
        except Exception as fallback_error:
            logger.critical(f"Fallback PDF failed: {str(fallback_error)}")
            
            # Return as text file as last resort
            mem_file = io.BytesIO(blog_content.encode('utf-8'))
            mem_file.seek(0)
            return send_file(
                mem_file,
                as_attachment=True,
                download_name=safe_name.replace('.pdf', '.txt'),
                mimetype='text/plain'
            )

if __name__ == '__main__':
    # Create session directory if it doesn't exist
    session_dir = app.config['SESSION_FILE_DIR']
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)