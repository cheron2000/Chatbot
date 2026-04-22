from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import boto3
import json
import re

app = Flask(__name__)

client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Model priority list — first one is tried first, falls back to next
MODELS = [
    "anthropic.claude-3-haiku-20240307-v1:0",
    "nvidia.nemotron-nano-12b-v2",
]

MAX_TOKENS = 4096  # Raised from 500 — no more cut-off responses


# ── Format helpers ────────────────────────────────────────────────────────────

def format_response(text):
    """Convert markdown-like syntax to HTML, preserving code block newlines."""
    code_blocks = []

    def save_code_block(m):
        lang = m.group(1) or ""
        code = m.group(2)
        placeholder = f"__CODEBLOCK_{len(code_blocks)}__"
        code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
        return placeholder

    text = re.sub(r'```(\w+)?\n?(.*?)```', save_code_block, text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = text.replace('\n', '<br>')

    for i, block in enumerate(code_blocks):
        text = text.replace(f'__CODEBLOCK_{i}__', block)

    return text


# ── Streaming route ───────────────────────────────────────────────────────────

def stream_anthropic(prompt):
    """Stream tokens from Anthropic Claude via Bedrock SSE."""
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}]
    }
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


def stream_nvidia(prompt):
    """Stream tokens from NVIDIA Nemotron via Bedrock SSE."""
    body = {
        "messages": [{"role": "user", "content": prompt}],
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


def stream_with_fallback(prompt):
    """Try models in order. If one fails, fall back to the next."""
    errors = []

    for model_id in MODELS:
        try:
            print(f"[INFO] Streaming from: {model_id}")
            if "anthropic" in model_id:
                yield from stream_anthropic(prompt)
            elif "nvidia" in model_id:
                yield from stream_nvidia(prompt)
            return  # success — stop trying

        except Exception as e:
            print(f"[WARN] {model_id} failed: {e}")
            errors.append(str(e))
            continue

    # All models failed
    error_msg = "⚠ All models failed. Please try again."
    formatted  = format_response(error_msg)
    yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': 0, 'output_tokens': 0})}\n\n"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    return Response(
        stream_with_context(stream_with_fallback(user_message)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",   # disables Nginx buffering if behind a proxy
        }
    )


if __name__ == "__main__":
    # Threaded=True is important for SSE to work correctly
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)