"""Chat route handlers."""
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context, session
from models.memory import MemoryManager
from models.vector_memory import VectorMemory, HybridMemory
from services.streaming import StreamingService
from utils.validators import validate_message
from utils.prompt_enhancer import enhance_user_prompt
from utils.attack_detector import get_detector
from utils.injection_tester import get_injection_tester


def create_chat_blueprint(streaming_service: StreamingService, bedrock_client,
                         memory_config, max_message_length: int, max_short_term: int,
                         vector_memory: VectorMemory = None,
                         limiter=None, chat_limit: str = "20 per minute",
                         enable_prompt_enhancement: bool = True,
                         enable_infiltration_mode: bool = True,
                         infiltration_auto_block: bool = False):
    """
    Create and configure the chat blueprint.

    Args:
        streaming_service: Streaming service instance
        bedrock_client: Boto3 Bedrock client
        memory_config: Memory configuration
        max_message_length: Maximum message length
        max_short_term: Maximum short-term history size
        vector_memory: Vector memory instance (optional)
        limiter: Flask-Limiter instance (optional, applies rate limit to /chat only)
        chat_limit: Rate limit string for the /chat endpoint
        enable_prompt_enhancement: Enable automatic prompt improvement
        enable_infiltration_mode: Enable infiltration mode for security testing
        infiltration_auto_block: Auto-block detected attacks

    Returns:
        Configured Flask blueprint
    """
    chat_bp = Blueprint('chat', __name__)
    
    # Initialize attack detector
    attack_detector = get_detector() if enable_infiltration_mode else None

    @chat_bp.route("/chat", methods=["POST"])
    def chat():
        """Handle chat message and stream response."""
        # Validate message
        user_message, error = validate_message(request.json, max_message_length)
        if error:
            return jsonify(error[0]), error[1]
        
        # Check infiltration mode
        infiltration_mode = session.get("infiltration_mode", False)
        attack_result = None
        
        # Detect attacks if infiltration mode is enabled
        if infiltration_mode and attack_detector:
            attack_result = attack_detector.detect(user_message, enable_blocking=infiltration_auto_block)
            
            # Log attack detection
            if attack_result.is_attack:
                print(f"[INFILTRATION] Attack detected: {attack_result.details}")
                print(f"[INFILTRATION] Severity: {attack_result.severity.upper()}")
                print(f"[INFILTRATION] Confidence: {attack_result.confidence:.0%}")
                print(f"[INFILTRATION] Should block: {attack_result.should_block}")
                
                # Save to session for frontend display
                session["last_attack"] = {
                    "message": user_message[:100],
                    "types": attack_result.attack_types,
                    "severity": attack_result.severity,
                    "confidence": attack_result.confidence,
                    "details": attack_result.details,
                    "blocked": attack_result.should_block,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Block if configured
                if attack_result.should_block:
                    return jsonify({
                        "error": "Attack detected and blocked",
                        "attack_info": {
                            "types": attack_result.attack_types,
                            "severity": attack_result.severity,
                            "confidence": attack_result.confidence,
                            "details": attack_result.details
                        }
                    }), 403
        
        # Enhance prompt for better AI responses
        enhancement_result = enhance_user_prompt(user_message, enable_prompt_enhancement)
        enhanced_message = enhancement_result['enhanced']
        was_enhanced = enhancement_result['was_enhanced']
        
        # Log enhancement for debugging
        if was_enhanced:
            print(f"[PROMPT] Enhanced {enhancement_result['type']} request")
            print(f"[PROMPT] Original: {user_message[:100]}...")
            print(f"[PROMPT] Enhanced: {enhanced_message[:100]}...")
        
        # Assign a stable session ID (persists in the flask-session cookie)
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        sid = session["session_id"]
        
        # Initialize memory manager
        memory = MemoryManager(sid, memory_config.memory_dir, bedrock_client)
        
        # Load long-term memory from disk
        long_term_summary = memory.load_longterm()
        
        # Vector memory: semantic search through conversation history
        vector_context = ""
        if vector_memory:
            relevant_messages = vector_memory.search_similar(
                enhanced_message, session_id=sid, n_results=3
            )
            if relevant_messages:
                context_parts = ["[Relevant past context]"]
                for msg in relevant_messages:
                    role = msg['metadata'].get('role', 'unknown')
                    content = msg['content'][:150]
                    context_parts.append(f"{role}: {content}...")
                vector_context = "\n".join(context_parts)
                print(f"[VECTOR] Found {len(relevant_messages)} relevant messages")
        
        # Short-term memory: last MAX_SHORT_TERM messages in session
        if "history" not in session:
            session["history"] = []
        
        # Add enhanced message to history (AI sees enhanced version)
        session["history"].append({"role": "user", "content": enhanced_message})
        
        # Trim short-term history BEFORE snapshotting
        if len(session["history"]) > max_short_term:
            session["history"] = session["history"][-max_short_term:]
        session.modified = True
        
        # Combine contexts
        combined_context = long_term_summary
        if vector_context:
            combined_context = f"{long_term_summary}\n\n{vector_context}" if long_term_summary else vector_context
        
        # Snapshot for the generator (session object unavailable inside generator)
        messages_snapshot = list(session["history"])
        long_term_snapshot = combined_context
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
                
                # Save to vector memory for semantic search
                if vector_memory:
                    vector_memory.add_message(sid_snapshot, "user", user_message_snapshot)
                    vector_memory.add_message(sid_snapshot, "assistant", assistant_reply)
                    print(f"[VECTOR] Saved messages to vector database")
                
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
        session.pop("last_attack", None)  # Clear attack history too
        sid = session.get("session_id")
        if sid:
            memory = MemoryManager(sid, memory_config.memory_dir, bedrock_client)
            memory.delete_longterm()
            
            # Clear vector memory
            if vector_memory:
                deleted_count = vector_memory.delete_session(sid)
                print(f"[VECTOR] Deleted {deleted_count} messages from vector database")
        
        return jsonify({"status": "cleared"})
    
    @chat_bp.route("/infiltration/toggle", methods=["POST"])
    def toggle_infiltration():
        """Toggle infiltration mode on/off."""
        if not enable_infiltration_mode:
            return jsonify({"error": "Infiltration mode is disabled"}), 403
        
        current = session.get("infiltration_mode", False)
        session["infiltration_mode"] = not current
        
        status = "enabled" if session["infiltration_mode"] else "disabled"
        print(f"[INFILTRATION] Mode {status}")
        
        return jsonify({
            "infiltration_mode": session["infiltration_mode"],
            "status": status
        })
    
    @chat_bp.route("/infiltration/status", methods=["GET"])
    def infiltration_status():
        """Get current infiltration mode status and last attack info."""
        if not enable_infiltration_mode:
            return jsonify({"enabled": False, "available": False})
        
        return jsonify({
            "enabled": session.get("infiltration_mode", False),
            "available": True,
            "auto_block": infiltration_auto_block,
            "last_attack": session.get("last_attack")
        })
    
    @chat_bp.route("/infiltration/test", methods=["POST"])
    def test_injections():
        """
        Automatically test multiple injection techniques on a base query.
        
        Request body:
        {
            "base_query": "how to crack wifi password",
            "test_all": true  // If false, stops after first success
        }
        
        Returns:
        {
            "results": [...],
            "summary": {...}
        }
        """
        if not enable_infiltration_mode:
            return jsonify({"error": "Infiltration mode is disabled"}), 403
        
        if not session.get("infiltration_mode", False):
            return jsonify({"error": "Infiltration mode is not enabled. Enable it first."}), 400
        
        data = request.json
        base_query = data.get("base_query", "").strip()
        test_all = data.get("test_all", True)
        
        if not base_query:
            return jsonify({"error": "base_query is required"}), 400
        
        # Get injection tester
        tester = get_injection_tester()
        
        # Generate all injection variations
        injections = tester.generate_injections(base_query)
        
        print(f"\n[INJECTION TEST] Starting automated test for: '{base_query}'")
        print(f"[INJECTION TEST] Testing {len(injections)} injection techniques...")
        
        # Test each injection
        results = []
        successful_count = 0
        
        for injection in injections:
            print(f"\n[INJECTION TEST] #{injection['id']}: {injection['name']}")
            
            # Simulate sending the message and getting response
            # In a real scenario, this would call the AI
            # For now, we'll return the injection data for frontend to test
            results.append({
                "id": injection["id"],
                "name": injection["name"],
                "description": injection["description"],
                "query": injection["query"],
                "tested": False,  # Frontend will test these
            })
            
            # If not testing all, stop after first success
            if not test_all and successful_count > 0:
                print(f"[INJECTION TEST] Stopping after first successful bypass")
                break
        
        return jsonify({
            "base_query": base_query,
            "total_injections": len(results),
            "injections": results,
            "test_all": test_all
        })
    
    return chat_bp
