"""Chat route handlers."""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from models.memory import MemoryManager
from models.user_profile import (
    build_system_prompt,
    delete_profile,
    load_profile,
    update_profile_async,
)
from models.vector_memory import VectorMemory
from routes.editor import EDITOR_SYSTEM_PROMPT, extract_json_proposal
from services.streaming import StreamingService
from services.websearch import web_search
from utils.attack_detector import get_detector
from utils.file_processor import process_file
from utils.injection_tester import get_injection_tester
from utils.prompt_enhancer import enhance_user_prompt
from utils.search_detector import should_skip_search
from utils.validators import validate_message

EDITOR_TRIGGERS = [
    # --- Code / file direct references ---
    "change the code",
    "edit the code",
    "modify the code",
    "update the code",
    "fix the code",
    "refactor the code",
    "in index.html",
    "in chat.py",
    "in the codebase",
    "to the codebase",
    "edit index",
    "modify index",
    "in style.css",
    "in editor.py",
    "in bedrock.py",
    # --- Theme / visual ---
    "make the theme",
    "change the theme",
    "set the theme",
    "make it look",
    "make it dark",
    "make it light",
    "make it white",
    "make it black",
    "make it blue",
    "dark mode",
    "light mode",
    "add dark mode",
    "add light mode",
    "redesign",
    "restyle",
    "overhaul",
    # --- Background / colors ---
    "change the background",
    "make the background",
    "set background to",
    "set the background",
    "background color",
    "change the color",
    "change colors",
    "modify color",
    "text color",
    "font color",
    "change the font",
    "change font",
    # --- CSS / style ---
    "change the style",
    "modify the style",
    "adjust the style",
    "update the css",
    "edit the css",
    "adjust layout",
    "modify layout",
    "change layout",
    "adjust the",
    "tweak the",
    # --- UI elements ---
    "add a button",
    "add a feature",
    "remove the",
    "hide the",
    "show the",
    "change the header",
    "change the footer",
    "change the navbar",
    "update the ui",
    "update the html",
    "make the chat",
    "make the sidebar",
    "make the input",
]


def create_chat_blueprint(
    streaming_service: StreamingService,
    bedrock_client,
    memory_config,
    max_message_length: int,
    max_short_term: int,
    vector_memory: Optional[VectorMemory] = None,
    limiter=None,
    chat_limit: str = "20 per minute",
    enable_prompt_enhancement: bool = True,
    enable_infiltration_mode: bool = True,
    infiltration_auto_block: bool = False,
    enable_developer_mode: bool = False,
):
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
        enable_developer_mode: Enable developer mode for code editing (DISABLED by default)

    Returns:
        Configured Flask blueprint
    """
    chat_bp = Blueprint("chat", __name__)

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

        # Check if developer mode is enabled (DISABLED FOR NOW)
        developer_mode = False  # Hardcoded to False - feature disabled

        # Only detect editor requests if developer mode is enabled
        is_editor_request = False
        # Developer mode disabled - no code editing allowed
        # if developer_mode:
        #     is_editor_request = any(t in user_message.lower() for t in EDITOR_TRIGGERS)

        # Check infiltration mode
        infiltration_mode = session.get("infiltration_mode", False)
        attack_result = None

        # Detect attacks if infiltration mode is enabled
        if infiltration_mode and attack_detector:
            attack_result = attack_detector.detect(
                user_message, enable_blocking=infiltration_auto_block
            )

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
                    "timestamp": datetime.now().isoformat(),
                }

                # Block if configured
                if attack_result.should_block:
                    return (
                        jsonify(
                            {
                                "error": "Attack detected and blocked",
                                "attack_info": {
                                    "types": attack_result.attack_types,
                                    "severity": attack_result.severity,
                                    "confidence": attack_result.confidence,
                                    "details": attack_result.details,
                                },
                            }
                        ),
                        403,
                    )

        # Web search: only if enabled by user via toggle
        web_context = ""
        web_search_enabled = request.json.get("web_search", False)
        print(f"[SEARCH] web_search flag received: {web_search_enabled}")
        if web_search_enabled and not should_skip_search(user_message):
            print(f"[SEARCH] Fetching web context for: {user_message[:80]}")
            web_context = web_search(user_message)
        elif web_search_enabled and should_skip_search(user_message):
            print(f"[SEARCH] Skipped -- message too short or conversational")

        # Skin lesion classification: detect if user wants classification
        classification_context = ""
        classification_keywords = [
            "diagnose", "classify", "what is this", "skin lesion", "mole", 
            "melanoma", "cancer", "skin cancer", "what kind", "identify",
            "spot on skin", "mark on skin", "growth", "bump", "rash",
            "skin condition", "dermatology", "skin problem"
        ]
        
        # Check if user explicitly requested classification OR if message contains classification keywords with image
        classify_image_flag = request.json.get("classify_image", False)
        has_image = bool(image_b64)
        has_classification_intent = any(keyword in user_message.lower() for keyword in classification_keywords)
        
        # Check if classification was done in last 2 messages (avoid redundancy)
        recent_classification = False
        if "history" in session and len(session["history"]) >= 2:
            for msg in session["history"][-2:]:
                if msg.get("role") == "assistant" and "[SKIN LESION CLASSIFICATION" in msg.get("content", ""):
                    recent_classification = True
                    break
        
        should_classify = (classify_image_flag or (has_image and has_classification_intent)) and not recent_classification
        
        if should_classify and has_image:
            try:
                import base64
                from services.skin_classifier import SkinClassifierService
                
                print(f"[CLASSIFIER] Auto-detecting skin lesion classification request")
                
                # Decode base64 image
                try:
                    image_bytes = base64.b64decode(image_b64)
                    
                    # Get classifier instance and classify
                    classifier = SkinClassifierService()
                    result = classifier.classify_image(image_bytes, top_k=3)
                    
                    # Build classification context for AI
                    top_pred = result.get_top_prediction()
                    alternatives = [
                        f"{pred.disease_name} ({pred.confidence:.1%})" 
                        for pred in result.predictions[1:3] if len(result.predictions) > 1
                    ]
                    
                    # Determine severity icon
                    if top_pred.severity == 'benign':
                        severity_icon = '✅'
                    elif top_pred.severity == 'pre-cancerous':
                        severity_icon = '⚠️'
                    else:  # malignant
                        severity_icon = '🚨'
                    
                    classification_context = f"""
[AI RESPONSE FORMAT - CRITICAL INSTRUCTION]

You MUST start your response with this exact format to confirm classification happened:

🔬 **Image Analysis Complete**

I've analyzed your skin lesion image using our AI classifier. Processing time: {result.processing_time_ms:.0f}ms

**Classification Results:**
🔬 {top_pred.disease_name}
📊 Confidence: {top_pred.confidence:.1%}
{severity_icon} Status: {top_pred.severity.title()}

[DETAILED CLASSIFICATION DATA FOR YOUR REFERENCE]
Disease code: {top_pred.disease_code}
Disease name: {top_pred.disease_name}
Confidence: {top_pred.confidence:.2%}
Severity: {top_pred.severity}
Description: {top_pred.description}
Alternative possibilities: {', '.join(alternatives) if alternatives else 'None with significant probability'}

[YOUR RESPONSE INSTRUCTIONS]
1. Start with the confirmation message above (including emojis and bold formatting)
2. Explain what this condition is in simple, easy-to-understand terms
3. Provide educational information about the condition
4. Explain whether this is concerning or not
5. Advise when to see a doctor (use the ABCDE rule for moles if relevant)
6. Include the medical disclaimer at the end
7. Be empathetic, supportive, and educational

CRITICAL: The user MUST know their image was analyzed. Use the format above exactly.
The classification confirmation is the most important part of your response.
"""
                    
                    print(f"[CLASSIFIER] Classification: {top_pred.disease_name} ({top_pred.confidence:.2%})")
                    
                except Exception as e:
                    print(f"[CLASSIFIER] Classification failed: {e}")
                    # Don't block the chat if classification fails
                    classification_context = ""
            
            except ImportError:
                print(f"[CLASSIFIER] Skin classifier service not available")
                classification_context = ""

        # Enhance prompt -- skip enhancement for editor requests and when web search is active
        enhancement_enabled = (
            enable_prompt_enhancement
            and not is_editor_request
            and not web_search_enabled
        )
        enhancement_result = enhance_user_prompt(user_message, enhancement_enabled)
        enhanced_message = enhancement_result["enhanced"]
        was_enhanced = enhancement_result["was_enhanced"]

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
                    role = msg["metadata"].get("role", "unknown")
                    content = msg["content"][:150]
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

        # Detect if user wants to edit code -- inject editor system prompt + file contents
        if is_editor_request:
            print(f"[EDITOR] Detected code edit request")
            # Read project files dynamically and inject their contents so AI can write exact old strings
            editor_file_context = ""
            FILE_CAP = 15000  # characters per file
            EDITABLE_EXTS = {".py", ".html", ".css", ".js", ".md"}
            SKIP_DIRS = {
                "__pycache__",
                ".git",
                ".vscode",
                ".kiro",
                "backups",
                "node_modules",
                "vector_db",
                "memory",
                "user_profiles",
                "analysis",
                "achivementfolder",
            }
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

            # Detect if user mentions a specific file -- load it first
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

            # Build ordered file list: detected -> priority -> rest
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
                    editor_file_context += (
                        f"\n\n[Current content of {rel_path}]\n```\n{content}\n```"
                    )
                    loaded_count += 1
                except Exception:
                    pass

            if editor_file_context:
                file_context = (
                    (file_context + editor_file_context)
                    if file_context
                    else editor_file_context
                )
                print(
                    f"[EDITOR] Injected {len(editor_file_context)} chars from {loaded_count} files"
                )
        elif developer_mode and any(t in user_message.lower() for t in EDITOR_TRIGGERS):
            # Editor request detected but developer mode is OFF
            print(
                f"[EDITOR] Code edit request detected but developer mode is OFF - treating as normal chat"
            )

        # Combine contexts
        combined_context = long_term_summary
        if vector_context:
            combined_context = (
                f"{long_term_summary}\n\n{vector_context}"
                if long_term_summary
                else vector_context
            )

        # CRITICAL: Web search results MUST take absolute priority
        if web_context:
            web_instruction = (
                "\n\n" + "=" * 70 + "\n"
                "🚨 CRITICAL INSTRUCTION - WEB SEARCH MODE ACTIVATED 🚨\n"
                "=" * 70 + "\n"
                "The user has explicitly requested current, real-time information.\n"
                "YOU MUST FOLLOW THESE RULES STRICTLY:\n\n"
                "1. OK USE ONLY the web search results below for factual information\n"
                "2. FAIL DO NOT use your training data for any facts covered in the search results\n"
                "3. OK CITE the source URLs from the search results in your response\n"
                "4. OK If the search results say 'as of [date]', include that date in your answer\n"
                "5. OK If search results conflict with your training data, TRUST THE SEARCH RESULTS\n"
                "6. FAIL DO NOT say 'I don't have current information' - you DO have it below\n"
                "7. OK Answer with confidence using ONLY the information from these search results\n\n"
                "=" * 70 + "\n\n"
            )
            combined_context = (
                f"{combined_context}{web_instruction}{web_context}"
                if combined_context
                else f"{web_instruction}{web_context}"
            )
            print(
                f"[SEARCH] OK Injecting web context ({len(web_context)} chars) with CRITICAL priority instructions"
            )
        
        # Inject classification context if available
        if classification_context:
            combined_context = (
                f"{combined_context}\n\n{classification_context}"
                if combined_context
                else classification_context
            )
            print(f"[CLASSIFIER] Injecting classification context ({len(classification_context)} chars)")

        if file_context:
            combined_context = (
                f"{combined_context}\n\n{file_context}"
                if combined_context
                else file_context
            )
            print(f"[FILE] Injecting file context ({len(file_context)} chars)")
        if profile_prompt:
            combined_context = (
                f"{profile_prompt}\n\n{combined_context}"
                if combined_context
                else profile_prompt
            )
            print(f"[PROFILE] Injecting profile for session {sid[:8]}\u2026")
        if is_editor_request:
            combined_context = (
                f"{EDITOR_SYSTEM_PROMPT}\n\n{combined_context}"
                if combined_context
                else EDITOR_SYSTEM_PROMPT
            )

        # Snapshot for the generator (session object unavailable inside generator)
        messages_snapshot = list(session["history"])
        # For editor requests, prepend the system prompt directly into the user message
        if (
            is_editor_request
            and messages_snapshot
            and messages_snapshot[-1]["role"] == "user"
        ):
            messages_snapshot[-1] = {
                "role": "user",
                "content": f"{EDITOR_SYSTEM_PROMPT}\n\nUser request: {enhanced_message}",
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

            for chunk in streaming_service.stream_with_fallback(
                messages_snapshot, long_term_snapshot, image_b64, image_mime
            ):
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
                                    print(
                                        f"[EDITOR] Proposal detected with {len(proposal.get('changes', []))} changes"
                                    )
                    except Exception:
                        pass
                yield chunk

            # Persist assistant reply to short-term history
            if assistant_reply:
                session["history"].append(
                    {"role": "assistant", "content": assistant_reply}
                )
                if len(session["history"]) > max_short_term:
                    session["history"] = session["history"][-max_short_term:]
                session.modified = True

                # Save to vector memory for semantic search
                if vector_memory:
                    vector_memory.add_message(
                        sid_snapshot, "user", user_message_snapshot
                    )
                    vector_memory.add_message(
                        sid_snapshot, "assistant", assistant_reply
                    )
                    print(f"[VECTOR] Saved messages to vector database")

                # Update user profile in background
                update_profile_async(sid_snapshot, list(session.get("history", [])))

                # Fire-and-forget background thread for long-term summarization
                memory.generate_summary_async(
                    long_term_snapshot, user_message_snapshot, assistant_reply
                )

        return Response(
            stream_with_context(generate_and_capture()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
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

        print(
            f"[CLEAR] Conversation memory cleared for session {sid[:8] if sid else 'unknown'}..."
        )
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

        return jsonify(
            {"infiltration_mode": session["infiltration_mode"], "status": status}
        )

    @chat_bp.route("/infiltration/status", methods=["GET"])
    def infiltration_status():
        """Get current infiltration mode status and last attack info."""
        if not enable_infiltration_mode:
            return jsonify({"enabled": False, "available": False})

        return jsonify(
            {
                "enabled": session.get("infiltration_mode", False),
                "available": True,
                "auto_block": infiltration_auto_block,
                "last_attack": session.get("last_attack"),
            }
        )

    @chat_bp.route("/developer/toggle", methods=["POST"])
    def toggle_developer():
        """Toggle developer mode (code editing) on/off - DISABLED."""
        return (
            jsonify(
                {
                    "error": "Developer mode is currently disabled",
                    "developer_mode": False,
                    "available": False,
                }
            ),
            403,
        )

    @chat_bp.route("/developer/status", methods=["GET"])
    def developer_status():
        """Get current developer mode status - DISABLED."""
        return jsonify(
            {
                "enabled": False,
                "available": False,
                "message": "Developer mode is currently disabled",
            }
        )

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
            return (
                jsonify(
                    {"error": "Infiltration mode is not enabled. Enable it first."}
                ),
                400,
            )

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
            results.append(
                {
                    "id": injection["id"],
                    "name": injection["name"],
                    "description": injection["description"],
                    "query": injection["query"],
                    "tested": False,  # Frontend will test these
                }
            )

            # If not testing all, stop after first success
            if not test_all and successful_count > 0:
                print(f"[INJECTION TEST] Stopping after first successful bypass")
                break

        return jsonify(
            {
                "base_query": base_query,
                "total_injections": len(results),
                "injections": results,
                "test_all": test_all,
            }
        )

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

    @chat_bp.route("/classify", methods=["POST"])
    def classify_skin_lesion():
        """
        Classify a skin lesion image using the trained EfficientNet model.
        
        Request body:
        {
            "image_b64": str,  # Base64-encoded image
            "image_mime": str,  # MIME type (image/jpeg, image/png)
            "top_k": int,      # Optional, default: 3
        }
        
        Returns:
        {
            "status": "success",
            "predictions": [...],
            "processing_time_ms": float,
            "model_info": {...},
            "timestamp": str,
            "disclaimer": str
        }
        """
        import base64
        from services.skin_classifier import SkinClassifierService
        
        try:
            # Parse request
            data = request.json
            if not data:
                return jsonify({"error": "Request body is required"}), 400
            
            image_b64 = data.get("image_b64", "")
            image_mime = data.get("image_mime", "image/jpeg")
            top_k = data.get("top_k", 3)
            
            # Validate input
            if not image_b64:
                return jsonify({"error": "image_b64 field is required"}), 400
            
            # Validate top_k
            try:
                top_k = int(top_k)
                if not 1 <= top_k <= 7:
                    return jsonify({"error": "top_k must be between 1 and 7"}), 400
            except (TypeError, ValueError):
                return jsonify({"error": "top_k must be an integer"}), 400
            
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_b64)
            except Exception as e:
                return jsonify({"error": f"Invalid base64 encoding: {e}"}), 400
            
            # Validate image size (10MB limit)
            max_size = 10 * 1024 * 1024  # 10MB
            if len(image_bytes) > max_size:
                return jsonify({
                    "error": f"Image too large. Maximum size: 10MB. Got: {len(image_bytes) / (1024*1024):.2f}MB"
                }), 413
            
            print(f"[CLASSIFIER] Classifying image ({len(image_bytes)} bytes, top_k={top_k})")
            
            # Get classifier instance
            classifier = SkinClassifierService()
            
            # Classify image
            result = classifier.classify_image(image_bytes, top_k=top_k)
            
            print(f"[CLASSIFIER] Classification complete: {result.get_top_prediction().disease_name} ({result.get_top_prediction().confidence:.2%})")
            
            # Return JSON response
            return jsonify(result.to_dict()), 200
            
        except FileNotFoundError as e:
            print(f"[CLASSIFIER] Model not found: {e}")
            return jsonify({
                "error": "Classification service unavailable. Model not found.",
                "details": str(e)
            }), 503
        
        except ValueError as e:
            print(f"[CLASSIFIER] Validation error: {e}")
            return jsonify({"error": str(e)}), 400
        
        except RuntimeError as e:
            print(f"[CLASSIFIER] Runtime error: {e}")
            return jsonify({
                "error": "Classification service temporarily unavailable.",
                "details": str(e)
            }), 503
        
        except Exception as e:
            print(f"[CLASSIFIER] Unexpected error: {e}")
            return jsonify({
                "error": "An unexpected error occurred during classification.",
                "details": str(e)
            }), 500
    
    # Apply rate limit to /classify endpoint (10 requests per minute)
    if limiter:
        classify_skin_lesion = limiter.limit("10 per minute")(classify_skin_lesion)

    @chat_bp.route("/health/classifier", methods=["GET"])
    def classifier_health():
        """
        Health check endpoint for the skin lesion classifier service.
        
        Returns:
        - 200 OK if model is loaded and operational
        - 503 Service Unavailable if model is not loaded or unavailable
        """
        from services.skin_classifier import SkinClassifierService
        
        try:
            classifier = SkinClassifierService()
            is_loaded = classifier.is_loaded()
            
            if is_loaded:
                # Model is loaded and ready
                return jsonify({
                    "status": "healthy",
                    "model_loaded": True,
                    "message": "Classifier service is operational"
                }), 200
            else:
                # Model not loaded yet
                return jsonify({
                    "status": "unavailable",
                    "model_loaded": False,
                    "message": "Model not loaded. Will load on first classification request."
                }), 503
        
        except FileNotFoundError:
            # Model checkpoint doesn't exist
            return jsonify({
                "status": "unavailable",
                "model_loaded": False,
                "message": "Model checkpoint not found. Training may still be in progress."
            }), 503
        
        except Exception as e:
            # Unexpected error
            return jsonify({
                "status": "error",
                "model_loaded": False,
                "message": f"Health check failed: {str(e)}"
            }), 503

    return chat_bp
