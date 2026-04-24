"""Chat route handlers."""
import json
import uuid
from flask import Blueprint, request, jsonify, Response, stream_with_context, session
from models.memory import MemoryManager
from services.streaming import StreamingService
from utils.validators import validate_message


def create_chat_blueprint(streaming_service: StreamingService, bedrock_client,
                         memory_config, max_message_length: int, max_short_term: int,
                         limiter=None, chat_limit: str = "20 per minute"):
    """
    Create and configure the chat blueprint.

    Args:
        streaming_service: Streaming service instance
        bedrock_client: Boto3 Bedrock client
        memory_config: Memory configuration
        max_message_length: Maximum message length
        max_short_term: Maximum short-term history size
        limiter: Flask-Limiter instance (optional, applies rate limit to /chat only)
        chat_limit: Rate limit string for the /chat endpoint

    Returns:
        Configured Flask blueprint
    """
    chat_bp = Blueprint('chat', __name__)

    @chat_bp.route("/chat", methods=["POST"])
    def chat():
        """Handle chat message and stream response."""
        # Validate message
        user_message, error = validate_message(request.json, max_message_length)
        if error:
            return jsonify(error[0]), error[1]
        
        # Assign a stable session ID (persists in the flask-session cookie)
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        sid = session["session_id"]
        
        # Initialize memory manager
        memory = MemoryManager(sid, memory_config.memory_dir, bedrock_client, memory_config.summary_model)
        
        # Load long-term memory from disk
        long_term_summary = memory.load_longterm()
        
        # Short-term memory: last MAX_SHORT_TERM messages in session
        if "history" not in session:
            session["history"] = []
        
        session["history"].append({"role": "user", "content": user_message})
        
        # Trim short-term history BEFORE snapshotting
        if len(session["history"]) > max_short_term:
            session["history"] = session["history"][-max_short_term:]
        session.modified = True
        
        # Snapshot for the generator (session object unavailable inside generator)
        messages_snapshot = list(session["history"])
        long_term_snapshot = long_term_summary
        user_message_snapshot = user_message
        sid_snapshot = sid
        
        def generate_and_capture():
            """Stream response to browser, capture full reply, trigger background summary."""
            assistant_reply = ""
            
            for chunk in streaming_service.stream_with_fallback(messages_snapshot, long_term_snapshot):
                # Track the full assistant reply
                if chunk.startswith("data: "):
                    try:
                        payload = json.loads(chunk[6:])
                        if payload.get("type") == "token":
                            assistant_reply += payload.get("text", "")
                    except Exception:
                        pass
                yield chunk
            
            # Persist assistant reply to short-term history
            if assistant_reply:
                session["history"].append({"role": "assistant", "content": assistant_reply})
                if len(session["history"]) > max_short_term:
                    session["history"] = session["history"][-max_short_term:]
                session.modified = True
                
                # Fire-and-forget background thread for long-term summarization
                # Reuse the already-created memory manager (captured via closure)
                memory.generate_summary_async(
                    long_term_snapshot,
                    user_message_snapshot,
                    assistant_reply
                )
        
        return Response(
            stream_with_context(generate_and_capture()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )

    # Apply rate limit only to the /chat view, not to /clear
    if limiter:
        chat = limiter.limit(chat_limit)(chat)

    @chat_bp.route("/clear", methods=["POST"])
    def clear_history():
        """Reset short-term AND long-term memory for the current session."""
        session.pop("history", None)
        sid = session.get("session_id")
        if sid:
            memory = MemoryManager(sid, memory_config.memory_dir, bedrock_client)
            memory.delete_longterm()
        return jsonify({"status": "cleared"})
    
    return chat_bp
