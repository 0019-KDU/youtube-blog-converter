import datetime
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, url_for
from flask_jwt_extended import JWTManager

logger = logging.getLogger(__name__)


def create_app():
    """Application factory pattern"""

    # Load environment variables
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Get the correct static and template paths
    app_dir = Path(__file__).resolve().parent  # app directory
    codebase_dir = app_dir.parent  # codebase directory
    static_dir = codebase_dir / "static"
    templates_dir = codebase_dir / "templates"
    # Create Flask app
    app = Flask(__name__, static_folder=str(static_dir),
                template_folder=str(templates_dir))

    # Configuration
    app.config["SECRET_KEY"] = (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
    )
    app.config["JWT_SECRET_KEY"] = app.config["SECRET_KEY"]
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    )

    # Session configuration
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_COOKIE_NAME"] = "session"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_COOKIE_SIZE"] = 4000

    # GA configuration
    app.config["GA_MEASUREMENT_ID"] = os.getenv("GA_MEASUREMENT_ID", "")

    # In-memory storage for large session data
    app.temp_storage = {}

    # Set application start time
    app.start_time = time.time()

    # Initialize JWT
    JWTManager(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.blog import blog_bp
    from app.routes.health import health_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(blog_bp)
    app.register_blueprint(health_bp)

    # Setup monitoring
    from app.monitoring.logging import setup_logging
    from app.monitoring.metrics import setup_metrics
    from app.monitoring.tracing import setup_tracing

    setup_metrics(app)
    setup_logging(app)
    setup_tracing(app)

    # Context processors
    from app.utils.security import inject_config, inject_user

    app.context_processor(inject_config)
    app.context_processor(inject_user)

    # Template helper functions
    @app.template_global()
    def format_date(date_obj=None):
        """Format date for template use"""
        import datetime

        if date_obj is None:
            date_obj = datetime.datetime.utcnow()

        if isinstance(date_obj, str):
            try:
                date_obj = datetime.datetime.fromisoformat(
                    date_obj.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                return date_obj

        return date_obj.strftime("%b %d, %Y")

    @app.template_global()
    def moment(date_obj=None):
        """Moment.js style date formatting"""
        import datetime

        class MockMoment:
            def __init__(self, date):
                self.date = date

            def format(self, format_str):
                if not self.date:
                    return datetime.datetime.now().strftime("%b %d, %Y")

                if isinstance(self.date, str):
                    try:
                        self.date = datetime.datetime.fromisoformat(
                            self.date.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        return self.date

                format_map = {
                    "MMM DD, YYYY": "%b %d, %Y",
                    "YYYY-MM-DD": "%Y-%m-%d",
                    "MM/DD/YYYY": "%m/%d/%Y",
                }

                python_format = format_map.get(format_str, "%b %d, %Y")
                return self.date.strftime(python_format)

        return MockMoment(date_obj)

    @app.template_filter("nl2br")
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if text is None:
            return ""
        return text.replace("\n", "<br>")

    # Error handlers
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized access"""
        logger.warning(
            f"Unauthorized access attempt from {request.remote_addr}")
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        logger.warning(f"404 error for {request.url}")
        return render_template("error.html", error="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return render_template(
            "error.html", error="Internal server error"), 500

    # Application cleanup
    @app.teardown_appcontext
    def cleanup_app_context(error):
        """Cleanup resources on app context teardown"""
        import gc

        try:
            gc.collect()
        except Exception:
            pass

    return app
