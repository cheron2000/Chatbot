from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import boto3
from botocore.config import Config
import json
import re
import html
import os
import uuid
import threading
from datetime import datetime, timezone

app = Flask(__name__)

# ── Session config (server-side filesystem sessions) ──────────────────────────
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), ".flask_sessions")
app.config["SESSION_PERMANENT"] = False
Session(app)

# ── Rate limiter (in-memory, per IP) ────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    on_breach=lambda limit: (jsonify({"error": "Rate limit exceeded. Please slow down."}), 429)
)

# ── Memory constants ──────────────────────────────────────────────────────────
# Short-term: last N messages kept verbatim in flask-session (fast, recent context)
MAX_SHORT_TERM = 10

# Long-term: one JSON file per session on disk, holds a rolling AI-written summary
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
os.makedirs(MEMORY_DIR, exist_ok=True)

MAX_TOKENS = 4096          # Max output tokens per response
MAX_MESSAGE_LENGTH = 4000  # Max characters per user input

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    config=Config(
        connect_timeout=5,   # seconds to establish TCP connection
        read_timeout=60,     # seconds to wait for first byte from Bedrock
        retries={"max_attempts": 0}  # no retries — fallback handles it
    )
)

# Model priority list — first one is tried first, falls back to next
MODELS = [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "nvidia.nemotron-nano-12b-v2",
]


# ── Format helpers ────────────────────────────────────────────────────────────

def format_response(text):
    """Convert markdown-like syntax to HTML.

    Approach:
    1. Extract all fenced code blocks first (prevents regex bleed-across).
    2. Replace inline formatting only on non-code portions.
    3. Re-inject escaped, syntax-highlighted code blocks.
    """
    code_blocks = []

    # Step 1: Extract fenced code blocks.
    # Uses a possessive-style pattern: match the shortest run between ``` pairs.
    # re.DOTALL lets . match newlines inside the block.
    CODE_BLOCK_RE = re.compile(r'```[ \t]*(\w+)?[ \t]*\n(.*?)```', re.DOTALL)

    def save_code_block(m):
        lang = m.group(1) or ""
        # Strip trailing whitespace from each line but keep newlines intact
        code_lines = m.group(2).rstrip("\n")
        code = html.escape(code_lines)  # Prevent XSS
        placeholder = f"__CODEBLOCK_{len(code_blocks)}__"
        code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
        return placeholder

    text = CODE_BLOCK_RE.sub(save_code_block, text)

    # Step 2: Inline code — [^`]+ already prevents crossing backtick boundaries
    text = re.sub(r'`([^`\n]+)`', lambda m: f'<code>{html.escape(m.group(1))}</code>', text)

    # Step 3: Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Step 4: Convert remaining newlines to <br>
    text = text.replace('\n', '<br>')

    # Step 5: Re-inject code blocks (they already contain their own newlines)
    for i, block in enumerate(code_blocks):
        text = text.replace(f'__CODEBLOCK_{i}__', block)

    return text


# ── Long-term memory helpers ──────────────────────────────────────────────────

def get_longterm_path(session_id: str) -> str:
    """Return the filesystem path for a session's long-term memory file."""
    return os.path.join(MEMORY_DIR, f"{session_id}_longterm.json")


def load_longterm(session_id: str) -> str:
    """Load the long-term summary string for a session. Returns '' if none exists."""
    path = get_longterm_path(session_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("summary", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


def save_longterm(session_id: str, summary: str) -> None:
    """Persist an updated long-term summary to disk."""
    path = get_longterm_path(session_id)
    payload = {
        "summary": summary,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def generate_summary(session_id: str, previous_summary: str,
                     user_message: str, assistant_reply: str) -> None:
    """Call the model (non-streaming) to produce an updated conversation summary
    and write it to disk. Runs in a background thread — never blocks the response.

    The summary is intentionally concise (≤ 150 tokens) so it doesn't consume
    excessive context space when prepended to future prompts.
    """
    prompt = (
        "You are a memory manager for a chatbot. "
        "Your only job is to maintain a short, factual summary of the conversation.\n\n"
        f"Previous summary:\n{previous_summary or 'None yet.'}\n\n"
        f"New exchange:\n"
        f"User: {user_message}\n"
        f"Assistant: {assistant_reply[:1000]}\n\n"  # cap to avoid huge prompts
        "Write an updated summary (2–4 sentences, max 150 words) that captures "
        "all key topics, facts, preferences, and context from the full conversation. "
        "Be specific. Do NOT include greetings or filler. Output ONLY the summary text."
    )
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(body)
        )
        result = json.loads(response["body"].read())
        new_summary = result["content"][0]["text"].strip()
        save_longterm(session_id, new_summary)
        print(f"[MEMORY] Summary updated for session {session_id[:8]}…")
    except Exception as e:
        print(f"[WARN] Summary generation failed: {e}")
        # On failure, keep the old summary — don't erase it
        if previous_summary:
            save_longterm(session_id, previous_summary)


# ── Streaming route ───────────────────────────────────────────────────────────

def stream_anthropic(messages, long_term_summary: str = ""):
    """Stream tokens from Anthropic Claude via Bedrock SSE.

    long_term_summary is injected as a system prompt so Claude has persistent
    context from previous sessions without blowing up the messages array.
    """
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": messages
    }
    if long_term_summary:
        body["system"] = (
            "The following is a summary of the conversation history so far "
            "(may span previous sessions). Use it as background context:\n\n"
            + long_term_summary
        )
    response = client.invoke_model_with_response_stream(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps(body)
    )

    input_tokens = 0
    output_tokens = 0
    full_text = ""

    for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        chunk_type = chunk.get("type", "")

        if chunk_type == "content_block_delta":
            token = chunk["delta"].get("text", "")
            full_text += token
            # Send raw token to frontend
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

        elif chunk_type == "message_delta":
            output_tokens = chunk.get("usage", {}).get("output_tokens", 0)

        elif chunk_type == "message_start":
            input_tokens = chunk.get("message", {}).get("usage", {}).get("input_tokens", 0)

    # After streaming ends, send the fully formatted HTML + token counts
    formatted = format_response(full_text)
    yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"


def stream_nvidia(messages, long_term_summary: str = ""):
    """Stream tokens from NVIDIA Nemotron via Bedrock SSE.

    NVIDIA uses the OpenAI chat format, so long_term_summary is prepended
    as a system message at position 0 in the messages list.
    """
    # Prepend system context if we have long-term memory
    messages_with_ctx = messages
    if long_term_summary:
        system_msg = {
            "role": "system",
            "content": (
                "The following is a summary of the conversation history so far "
                "(may span previous sessions). Use it as background context:\n\n"
                + long_term_summary
            )
        }
        messages_with_ctx = [system_msg] + messages

    body = {
        "messages": messages_with_ctx,
        "max_tokens": MAX_TOKENS,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": True
    }
    response = client.invoke_model_with_response_stream(
        modelId="nvidia.nemotron-nano-12b-v2",
        body=json.dumps(body)
    )

    full_text = ""
    input_tokens = 0
    output_tokens = 0

    for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])

        # OpenAI-compatible streaming format
        for choice in chunk.get("choices", []):
            token = choice.get("delta", {}).get("content", "")
            if token:
                full_text += token
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

        # Usage comes in the last chunk
        if "usage" in chunk:
            input_tokens  = chunk["usage"].get("prompt_tokens", 0)
            output_tokens = chunk["usage"].get("completion_tokens", 0)

    formatted = format_response(full_text)
    yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': input_tokens, 'output_tokens': output_tokens})}\n\n"


def stream_with_fallback(messages, long_term_summary: str = ""):
    """Try models in order. If one fails, fall back to the next.

    Passes long_term_summary into each model function so they can inject
    it as system-level context. If a model fails AFTER already yielding
    tokens (mid-stream), emits an error event to the frontend.
    """
    for model_id in MODELS:
        tokens_yielded = False
        try:
            print(f"[INFO] Streaming from: {model_id}")
            if "anthropic" in model_id:
                gen = stream_anthropic(messages, long_term_summary)
            elif "nvidia" in model_id:
                gen = stream_nvidia(messages, long_term_summary)
            else:
                continue

            for chunk in gen:
                if '"type": "token"' in chunk:
                    tokens_yielded = True
                yield chunk

            return  # success — stop trying

        except Exception as e:
            print(f"[WARN] {model_id} failed: {e}")
            if tokens_yielded:
                # Mid-stream failure — notify the frontend immediately
                err_html = format_response(f"⚠ Connection lost mid-response ({model_id}). Please try again.")
                yield f"data: {json.dumps({'type': 'error', 'html': err_html})}\n\n"
                return  # can't retry after partial output
            continue  # pre-stream failure — try next model

    # All models failed before yielding any tokens
    error_msg = "⚠ All models failed. Please try again."
    formatted  = format_response(error_msg)
    yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': 0, 'output_tokens': 0})}\n\n"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
@limiter.limit("20 per minute")
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    if len(user_message) > MAX_MESSAGE_LENGTH:
        return jsonify({"error": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters allowed."}), 400

    # ── Assign a stable session ID (persists in the flask-session cookie) ──
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    sid = session["session_id"]

    # ── Load long-term memory from disk ──
    long_term_summary = load_longterm(sid)

    # ── Short-term memory: last MAX_SHORT_TERM messages in session ──
    if "history" not in session:
        session["history"] = []

    session["history"].append({"role": "user", "content": user_message})

    # Trim short-term history BEFORE snapshotting
    if len(session["history"]) > MAX_SHORT_TERM:
        session["history"] = session["history"][-MAX_SHORT_TERM:]
    session.modified = True

    # Snapshot for the generator (session object unavailable inside generator)
    messages_snapshot       = list(session["history"])
    long_term_snapshot      = long_term_summary
    user_message_snapshot   = user_message
    sid_snapshot            = sid

    def generate_and_capture():
        """Stream response to browser, capture full reply, trigger background summary."""
        assistant_reply = ""

        for chunk in stream_with_fallback(messages_snapshot, long_term_snapshot):
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
            if len(session["history"]) > MAX_SHORT_TERM:
                session["history"] = session["history"][-MAX_SHORT_TERM:]
            session.modified = True

            # ── Fire-and-forget background thread for long-term summarization ──
            # The user sees the response immediately; summary updates silently.
            t = threading.Thread(
                target=generate_summary,
                args=(sid_snapshot, long_term_snapshot,
                      user_message_snapshot, assistant_reply),
                daemon=True
            )
            t.start()

    return Response(
        stream_with_context(generate_and_capture()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/clear", methods=["POST"])
def clear_history():
    """Reset short-term AND long-term memory for the current session."""
    session.pop("history", None)
    sid = session.get("session_id")
    if sid:
        mem_path = get_longterm_path(sid)
        if os.path.exists(mem_path):
            os.remove(mem_path)
            print(f"[MEMORY] Deleted long-term memory for session {sid[:8]}…")
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    # Threaded=True is important for SSE to work correctly
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)