"""Chat route handlers."""
import json
import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, stream_with_context, session
from models.memory import MemoryManager
from models.vector_memory import VectorMemory
from services.streaming import StreamingService
from utils.validators import validate_message
from utils.prompt_enhancer import enhance_user_prompt
from utils.attack_detector import get_detector
from utils.injection_tester import get_injection_tester
from utils.search_detector import should_skip_search
from services.websearch import web_search
from models.user_profile import load_profile, build_system_prompt, update_profile_async, delete_profile
from utils.file_processor import process_file
from routes.editor import EDITOR_SYSTEM_PROMPT, extract_json_proposal

EDITOR_TRIGGERS = [
    # --- Code / file direct references ---
    "change the code", "edit the code", "modify the code",
    "update the code", "fix the code", "refactor the code",
    "in index.html", "in chat.py", "in the codebase",
    "to the codebase", "edit index", "modify index",
    "in style.css", "in editor.py", "in bedrock.py",

    # --- Theme / visual ---
    "make the theme", "change the theme", "set the theme",
    "make it look", "make it dark", "make it light",
    "make it white", "make it black", "make it blue",
    "dark mode", "light mode", "add dark mode", "add light mode",
    "redesign", "restyle", "overhaul",

    # --- Background / colors ---
    "change the background", "make the background",
    "set background to", "set the background",
    "background color", "change the color", "change colors",
    "modify color", "text color", "font color",
    "change the font", "change font",

    # --- CSS / style ---
    "change the style", "modify the style", "adjust the style",
    "update the css", "edit the css",
    "adjust layout", "modify layout", "change layout",
    "adjust the", "tweak the",

    # --- UI elements ---
    "add a button", "add a feature", "remove the",
    "hide the", "show the",
    "change the header", "change the footer", "change the navbar",
    "update the ui", "update the html",
    "make the chat", "make the sidebar", "make the input",
]


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
        # Extract image if provided
        image_b64 = request.json.get("image_b64", "")
        image_mime = request.json.get("image_mime", "image/jpeg")

        # Extract file context if provided (text from PDF/code files)
        file_context = request.json.get("file_context", "")

        # Validate message
        user_message, error = validate_message(request.json, max_message_length)
        if error:
            return jsonify(error[0]), error[1]

        # Check if developer mode is enabled
        developer_mode = session.get("developer_mode", False)
        
        # Only detect editor requests if developer mode is enabled
        is_editor_request = False
        if developer_mode:
            is_editor_request = any(t in user_message.lower() for t in EDITOR_TRIGGERS)
        
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
        
        # Web search: only if enabled by user via toggle
        web_context = ""
        web_search_enabled = request.json.get("web_search", False)
        if web_search_enabled and not should_skip_search(user_message):
            print(f"[SEARCH] Fetching web context for: {user_message[:80]}")
            web_context = web_search(user_message)

        # Enhance prompt — skip enhancement for editor requests to preserve intent
        enhancement_result = enhance_user_prompt(user_message, enable_prompt_enhancement and not is_editor_request)
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
        
        # Add user message to history (store original, not enhanced)
        session["history"].append({"role": "user", "content": user_message})
        
        # Trim short-term history BEFORE snapshotting
        if len(session["history"]) > max_short_term:
            session["history"] = session["history"][-max_short_term:]
        session.modified = True
        
        # Load user profile and build behavior instructions
        user_profile = load_profile(sid)
        profile_prompt = build_system_prompt(user_profile)

        # Detect if user wants to edit code — inject editor system prompt + file contents
        if is_editor_request:
            print(f"[EDITOR] Detected code edit request")
            # Read project files dynamically and inject their contents so AI can write exact old strings
            editor_file_context = ""
            FILE_CAP = 15000  # characters per file
            EDITABLE_EXTS = {".py", ".html", ".css", ".js", ".md"}
            SKIP_DIRS = {"__pycache__", ".git", ".vscode", ".kiro",
                         "backups", "node_modules", "vector_db", "memory",
                         "user_profiles", "analysis", "achivementfolder"}
            project_root = os.path.dirname(os.path.dirname(__file__))

            # Always-load core files first (most relevant for UI/theme changes)
            priority_files = [
                "templates/index.html",
                "style.css",
                "routes/chat.py",
                "routes/editor.py",
                "services/bedrock.py",
                "services/code_editor.py",
                "config.py",
            ]

            # Detect if user mentions a specific file — load it first
            msg_lower = user_message.lower()
            detected_files = []
            for root_dir, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in EDITABLE_EXTS:
                        continue
                    if fname.lower() in msg_lower:
                        rel = os.path.relpath(
                            os.path.join(root_dir, fname), project_root
                        ).replace("\\", "/")
                        if rel not in detected_files:
                            detected_files.append(rel)

            # Build ordered file list: detected → priority → rest
            ordered_files = list(detected_files)
            for f in priority_files:
                if f not in ordered_files:
                    ordered_files.append(f)

            # Add remaining project files
            for root_dir, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for fname in files:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in EDITABLE_EXTS:
                        continue
                    rel = os.path.relpath(
                        os.path.join(root_dir, fname), project_root
                    ).replace("\\", "/")
                    if rel not in ordered_files:
                        ordered_files.append(rel)

            loaded_count = 0
            for rel_path in ordered_files:
                abs_path = os.path.join(project_root, rel_path)
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        content = f.read()[:FILE_CAP]
                    editor_file_context += f"\n\n[Current content of {rel_path}]\n```\n{content}\n```"
                    loaded_count += 1
                except Exception:
                    pass

            if editor_file_context:
                file_context = (file_context + editor_file_context) if file_context else editor_file_context
                print(f"[EDITOR] Injected {len(editor_file_context)} chars from {loaded_count} files")
        elif developer_mode and any(t in user_message.lower() for t in EDITOR_TRIGGERS):
            # Editor request detected but developer mode is OFF
            print(f"[EDITOR] Code edit request detected but developer mode is OFF - treating as normal chat")

        # Combine contexts
        combined_context = long_term_summary
        if vector_context:
            combined_context = f"{long_term_summary}\n\n{vector_context}" if long_term_summary else vector_context
        
        # IMPORTANT: Web search results should be prioritized and explicitly marked
        if web_context:
            web_instruction = (
                "\n\n⚠️ CRITICAL: The user has enabled web search. "
                "You MUST use the following CURRENT web search results to answer the question. "
                "These results contain the most up-to-date information from the internet. "
                "DO NOT rely on your training data for facts that can be found in these search results. "
                "Always cite the sources provided in the search results.\n\n"
            )
            combined_context = f"{combined_context}{web_instruction}{web_context}" if combined_context else f"{web_instruction}{web_context}"
            print(f"[SEARCH] Injecting web context ({len(web_context)} chars) with priority instructions")
        
        if file_context:
            combined_context = f"{combined_context}\n\n{file_context}" if combined_context else file_context
            print(f"[FILE] Injecting file context ({len(file_context)} chars)")
        if profile_prompt:
            combined_context = f"{profile_prompt}\n\n{combined_context}" if combined_context else profile_prompt
            print(f"[PROFILE] Injecting profile for session {sid[:8]}\u2026")
        if is_editor_request:
            combined_context = f"{EDITOR_SYSTEM_PROMPT}\n\n{combined_context}" if combined_context else EDITOR_SYSTEM_PROMPT
        
        # Snapshot for the generator (session object unavailable inside generator)
        messages_snapshot = list(session["history"])
        # For editor requests, prepend the system prompt directly into the user message
        if is_editor_request and messages_snapshot and messages_snapshot[-1]["role"] == "user":
            messages_snapshot[-1] = {
                "role": "user",
                "content": f"{EDITOR_SYSTEM_PROMPT}\n\nUser request: {enhanced_message}"
            }
        elif messages_snapshot and messages_snapshot[-1]["role"] == "user":
            messages_snapshot[-1] = {"role": "user", "content": enhanced_message}
        long_term_snapshot = combined_context
        user_message_snapshot = user_message
        sid_snapshot = sid
        
        def generate_and_capture():
            """Stream response to browser, capture full reply, trigger background summary."""
            # Notify frontend that web search was used
            if web_context:
                yield f"data: {json.dumps({'type': 'search_used', 'query': user_message[:80]})}\n\n"
            assistant_reply = ""
            
            for chunk in streaming_service.stream_with_fallback(messages_snapshot, long_term_snapshot, image_b64, image_mime):
                # Track the full assistant reply
                if chunk.startswith("data: "):
                    try:
                        payload = json.loads(chunk[6:])
                        if payload.get("type") == "token":
                            assistant_reply += payload.get("text", "")
                        elif payload.get("type") == "done":
                            # Check for editor proposal BEFORE emitting done
                            if is_editor_request:
                                proposal = extract_json_proposal(assistant_reply)
                                if proposal:
                                    yield f"data: {json.dumps({'type': 'editor_proposal', 'ai_response': assistant_reply})}\n\n"
                                    print(f"[EDITOR] Proposal detected with {len(proposal.get('changes', []))} changes")
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
                
                # Update user profile in background
                update_profile_async(sid_snapshot, list(session.get("history", [])))

                # Fire-and-forget background thread for long-term summarization
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
            delete_profile(sid)
            
            # Clear vector memory
            if vector_memory:
                deleted_count = vector_memory.delete_session(sid)
                print(f"[VECTOR] Deleted {deleted_count} messages from vector database")
        
        print(f"[CLEAR] Conversation memory cleared for session {sid[:8] if sid else 'unknown'}...")
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
    
    @chat_bp.route("/developer/toggle", methods=["POST"])
    def toggle_developer():
        """Toggle developer mode (code editing) on/off."""
        current = session.get("developer_mode", False)
        session["developer_mode"] = not current
        
        status = "enabled" if session["developer_mode"] else "disabled"
        print(f"[DEVELOPER] Mode {status}")
        
        return jsonify({
            "developer_mode": session["developer_mode"],
            "status": status
        })
    
    @chat_bp.route("/developer/status", methods=["GET"])
    def developer_status():
        """Get current developer mode status."""
        return jsonify({
            "enabled": session.get("developer_mode", False),
            "available": True
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
    
    @chat_bp.route("/upload", methods=["POST"])
    def upload_file():
        """Process uploaded file and return extracted content."""
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        f = request.files["file"]
        filename = f.filename
        mime = f.content_type or "application/octet-stream"
        file_bytes = f.read()

        result = process_file(filename, mime, file_bytes)

        if result["type"] == "error":
            return jsonify({"error": result["content"]}), 400

        print(f"[FILE] Processed: {filename} ({mime}, {len(file_bytes)} bytes)")
        return jsonify(result)

    return chat_bp
