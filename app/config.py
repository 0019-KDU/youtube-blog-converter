import datetime
import os
from pathlib import Path

from dotenv import load_dotenv


class Config:
    """Base configuration class"""

    # Load environment variables
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Security
    SECRET_KEY = (
        os.getenv("JWT_SECRET_KEY")
        or os.getenv("FLASK_SECRET_KEY")
        or os.getenv("SECRET_KEY")
    )
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400))
    )

    # Session configuration
    SESSION_PERMANENT = False
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_COOKIE_SIZE = 4000

    # Database
    MONGODB_URI = os.getenv("MONGODB_URI")

    # External APIs
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY")

    # Analytics
    GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "")

    # Monitoring
    LOKI_URL = os.getenv("LOKI_URL", "http://YOUR_DROPLET_IP:3100")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    SHARED_LOG_PATH = os.getenv("SHARED_LOG_PATH", "/shared-logs")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG = False
    FLASK_ENV = "production"
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    FLASK_ENV = "testing"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
