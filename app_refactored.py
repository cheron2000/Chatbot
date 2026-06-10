"""
ORACLE AI Chat Application - Refactored Version

A Flask-based AI chatbot with AWS Bedrock integration, featuring:
- Dual memory system (short-term + long-term)
- Model fallback (Claude + NVIDIA)
- Real-time streaming responses
- Token analytics
"""
# CRITICAL: Load .env FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from config import config
from services.bedrock import BedrockService
from services.streaming import StreamingService
from routes.main import main_bp
from routes.chat import create_chat_blueprint
from routes.editor import editor_bp


def create_app():
    """Application factory pattern."""
    app = Flask(__name__)
    
    # ── Validate SECRET_KEY ──
    if config.secret_key == "dev-secret-change-in-prod":
        import warnings
        warnings.warn(
            "⚠️  WARNING: Using default SECRET_KEY! Set SECRET_KEY environment variable in production.",
            RuntimeWarning,
            stacklevel=2
        )
    
    # ── Session config (server-side filesystem sessions) ──
    app.config["SECRET_KEY"] = config.secret_key
    app.config["SESSION_TYPE"] = config.session_type
    app.config["SESSION_FILE_DIR"] = os.path.join(
        os.path.dirname(__file__), 
        config.session_file_dir
    )
    app.config["SESSION_PERMANENT"] = config.session_permanent
    Session(app)
    
    # ── Rate limiter (in-memory, per IP) ──
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[config.rate_limit.default_limit],
        storage_uri="memory://"
    )
    
    # ── Initialize services ──
    bedrock_service = BedrockService(config.bedrock)
    streaming_service = StreamingService(
        bedrock_service,
        config.bedrock.models,
        config.max_tokens
    )
    
    # ── Initialize vector memory ──
    vector_memory = None
    if config.memory.enable_vector_memory:
        from models.vector_memory import VectorMemory
        vector_memory = VectorMemory(persist_directory=config.memory.vector_db_dir)
        print(f"[VECTOR] Initialized vector memory at {config.memory.vector_db_dir}")
    
    # ── Register blueprints ──
    app.register_blueprint(main_bp)
    
    chat_bp = create_chat_blueprint(
        streaming_service=streaming_service,
        bedrock_client=bedrock_service.client,
        memory_config=config.memory,
        max_message_length=config.max_message_length,
        max_short_term=config.memory.max_short_term,
        vector_memory=vector_memory,
        limiter=limiter,
        chat_limit=config.rate_limit.chat_limit,
        enable_prompt_enhancement=config.enable_prompt_enhancement,
        enable_infiltration_mode=config.enable_infiltration_mode,
        infiltration_auto_block=config.infiltration_auto_block
    )

    app.register_blueprint(chat_bp)
    app.register_blueprint(editor_bp)
    
    return app


if __name__ == "__main__":
    app = create_app()
    # Threaded=True is important for SSE to work correctly
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
