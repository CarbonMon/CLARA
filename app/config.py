import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-development-only'
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Application configuration
    APP_TITLE = "Clinical Research Analysis Tool"
    OPENAI_MODELS = {
        "gpt-4o": "GPT-4o",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-3.5-turbo": "GPT-3.5 Turbo"
    }
    CLAUDE_MODELS = {
        "claude-3-opus-20240229": "Claude 3 Opus",
        "claude-3-sonnet-20240229": "Claude 3 Sonnet",
        "claude-3-haiku-20240307": "Claude 3 Haiku"
    }
    DEFAULT_OPENAI_MODEL = "gpt-4o"
    DEFAULT_CLAUDE_MODEL = "claude-3-haiku-20240307"
    MAX_PUBMED_RESULTS = 400
    DEFAULT_PUBMED_RESULTS = 20
    SUPPORTED_LANGUAGES = {
        'English': 'eng',
        'French': 'fra',
        'Arabic': 'ara',
        'Spanish': 'spa',
    }
    
    # NCBI Credentials - from environment or to be set via UI
    NCBI_EMAIL = os.environ.get('NCBI_EMAIL')
    NCBI_API_KEY = os.environ.get('NCBI_API_KEY')
