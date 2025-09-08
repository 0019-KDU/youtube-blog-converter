import os
import sys
import time
import logging
from pathlib import Path

# Ensure the app directory is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def setup_environment():
    """Setup environment variables and basic logging"""
    from dotenv import load_dotenv
    
    # Load environment variables
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded .env from: {env_path}")
    else:
        load_dotenv()
        print("Loaded .env from default location")
    
    # Setup basic logging
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_environment():
    """Validate required environment variables"""
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key',
        'SUPADATA_API_KEY': 'Supadata API key', 
        'MONGODB_URI': 'MongoDB connection URI',
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    optional_vars = {
        'LOKI_URL': 'Loki server URL for logging',
        'GA_MEASUREMENT_ID': 'Google Analytics measurement ID'
    }
    
    logger = logging.getLogger(__name__)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        print(f"\nERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these environment variables and try again.")
        sys.exit(1)
    
    # Log optional missing vars as warnings
    missing_optional = [var for var in optional_vars.keys() if not os.getenv(var)]
    if missing_optional:
        logger.warning(f"Missing optional environment variables: {', '.join(missing_optional)}")
        for var in missing_optional:
            logger.warning(f"  - {var}: {optional_vars[var]}")
    
    logger.info("Environment validation completed successfully")

def create_application():
    """Create and configure the Flask application"""
    from app import create_app
    
    app = create_app()
    
    # Set application start time for uptime calculation
    app.start_time = time.time()
    
    logger = logging.getLogger(__name__)
    logger.info("Flask application created successfully")
    
    return app

def main():
    """Main application entry point"""
    print("YouTube Blog Generator - Starting Application")
    print("=" * 60)
    
    try:
        # Setup environment
        setup_environment()
        logger = logging.getLogger(__name__)
        
        # Validate environment
        validate_environment()
        
        # Create application
        app = create_application()
        
        # Configuration
        port = int(os.environ.get('PORT', 5000))
        debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        host = os.getenv('FLASK_HOST', '0.0.0.0')
        
        # Pre-startup verification
        logger.info("\n=== Pre-startup Verification ===")
        logger.info(f"Secret key set: {bool(app.secret_key)}")
        logger.info(f"Secret key length: {len(app.secret_key) if app.secret_key else 0}")
        logger.info(f"JWT configured: {bool(app.config.get('JWT_SECRET_KEY'))}")
        logger.info("Production-ready modular structure loaded")
        logger.info("Prometheus metrics enabled on /metrics endpoint")
        logger.info("Enhanced logging configured")
        logger.info(f"Loki URL: {os.getenv('LOKI_URL', 'NOT_SET')}")
        
        logger.info(f"\nStarting application on {host}:{port}")
        logger.info(f"Debug mode: {debug_mode}")
        logger.info("=" * 60 + "\n")
        
        # Start the application
        app.run(host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
        
    except KeyboardInterrupt:
        logger.info("\nApplication stopped by user")
        print("\nApplication stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        print(f"\nERROR: Failed to start application: {str(e)}")
        sys.exit(1)
    finally:
        try:
            # Cleanup
            logger.info("Application shutdown cleanup completed")
        except Exception:
            pass

if __name__ == '__main__':
    main()
    