"""Editor routes — propose, apply, and restore code changes."""
import json
import os
from flask import Blueprint, request, jsonify, session
from services.code_editor import apply_change, restore_file, list_backups, PROJECT_ROOT

editor_bp = Blueprint("editor", __name__)

# System prompt injected when AI is asked to propose code changes
EDITOR_SYSTEM_PROMPT = """⚠️ CRITICAL: CODE EDITOR MODE ACTIVATED ⚠️

You MUST respond with EXACTLY this JSON structure. ANY deviation will cause system failure.

DO NOT use: CODE_EDITOR_MODE, ACTION, DETAILS, REMOVED, ADDED, TYPE, SELECTOR, PROPERTY, VALUE
DO NOT invent new JSON formats
DO NOT add extra nesting
DO NOT add any text outside the JSON block

REQUIRED FORMAT (copy this structure exactly):
```json
{
  "summary": "one line description of the change",
  "changes": [
    {
      "file": "templates/index.html",
      "action": "replace",
      "old": "EXACT string copied from file - must match character for character including spaces and newlines",
      "new": "replacement string",
      "reason": "brief explanation"
    }
  ]
}
```

MANDATORY RULES:
1. Output ONLY the JSON block above — nothing before, nothing after
2. "old" MUST be copied character-for-character from the [Current content of ...] blocks provided
3. "action" MUST be one of: "replace", "append", or "create"
4. For CSS/theme changes: the CSS lives inside a <style> tag in templates/index.html — search for it there
5. Copy the ENTIRE CSS rule (selector + opening brace + properties + closing brace) as "old"
6. If you cannot find the EXACT text to replace, use "append" to add new CSS after the </style> tag
7. NEVER modify: config.py, .env, requirements.txt, app_refactored.py
8. Always check [Current content of templates/index.html] carefully for the real CSS before writing "old"

EXAMPLE 1 — Changing background color (CSS inside index.html):
```json
{
  "summary": "Change background to white",
  "changes": [
    {
      "file": "templates/index.html",
      "action": "replace",
      "old": "        body {\n            font-family: 'Segoe UI', sans-serif;\n            background: #0d0d0d;",
      "new": "        body {\n            font-family: 'Segoe UI', sans-serif;\n            background: #FFFFFF;",
      "reason": "User requested white background"
    }
  ]
}
```

EXAMPLE 2 — Adding a new CSS rule (when you can't find existing rule to replace):
```json
{
  "summary": "Override chat bubble color to blue",
  "changes": [
    {
      "file": "templates/index.html",
      "action": "append",
      "old": "",
      "new": "\n<style>\n.user-bubble { background: #1a73e8 !important; color: #fff !important; }\n</style>",
      "reason": "Appending override CSS because original rule uses a complex selector"
    }
  ]
}
```

EXAMPLE 3 — Changing Python code:
```json
{
  "summary": "Increase max message length",
  "changes": [
    {
      "file": "config.py",
      "action": "replace",
      "old": "MAX_MESSAGE_LENGTH = 2000",
      "new": "MAX_MESSAGE_LENGTH = 5000",
      "reason": "User requested longer message limit"
    }
  ]
}
```

⚠️ REMEMBER: Read the provided file contents carefully. Copy "old" EXACTLY as-is."""


def extract_json_proposal(text: str) -> dict | None:
    """Extract JSON proposal from AI response text."""
    # Method 1: Extract from ```json code block
    try:
        start = text.find("```json")
        end   = text.find("```", start + 6)
        if start != -1 and end != -1:
            json_str = text[start + 7:end].strip()
            proposal = json.loads(json_str)
            # Validate structure
            if "changes" in proposal and isinstance(proposal["changes"], list):
                return proposal
            else:
                print(f"[EDITOR] JSON parsed but missing 'changes' array. Keys found: {list(proposal.keys())}")
    except Exception as e:
        print(f"[EDITOR] Failed to parse JSON code block: {e}")

    # Method 2: Try raw JSON fallback
    try:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            proposal = json.loads(text[start:end])
            # Validate structure
            if "changes" in proposal and isinstance(proposal["changes"], list):
                return proposal
            else:
                print(f"[EDITOR] Raw JSON parsed but missing 'changes' array. Keys: {list(proposal.keys())}")
    except Exception as e:
        print(f"[EDITOR] Failed to parse raw JSON: {e}")

    # Method 3: Detect common wrong formats and log them clearly
    if "CODE_EDITOR_MODE" in text:
        print(f"[EDITOR] ERROR: AI used wrong format — CODE_EDITOR_MODE detected")
    elif "\"action\"" in text and "\"changes\"" not in text:
        print(f"[EDITOR] ERROR: AI used wrong format — 'action' key without 'changes' array")
    elif "{" not in text:
        print(f"[EDITOR] ERROR: AI response contains no JSON at all")
    else:
        print(f"[EDITOR] ERROR: Could not extract valid proposal from response")

    print(f"[EDITOR] AI response preview (first 400 chars): {text[:400]}")
    return None


def get_file_preview(rel_path: str, old_str: str, new_str: str) -> dict:
    """Generate before/after preview for a change."""
    abs_path = os.path.join(PROJECT_ROOT, rel_path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Find context around the change (3 lines before/after)
        lines = content.split("\n")
        old_lines = old_str.split("\n")
        for i, line in enumerate(lines):
            if old_str.split("\n")[0] in line:
                start = max(0, i - 2)
                end   = min(len(lines), i + len(old_lines) + 2)
                before_ctx = "\n".join(lines[start:end])
                after_content = content.replace(old_str, new_str, 1)
                after_lines = after_content.split("\n")
                after_ctx = "\n".join(after_lines[start:end + (len(new_str.split("\n")) - len(old_lines))])
                return {"before": before_ctx, "after": after_ctx, "found": True}
        return {"before": old_str, "after": new_str, "found": False}
    except FileNotFoundError:
        return {"before": "(new file)", "after": new_str, "found": True}
    except Exception as e:
        return {"before": str(e), "after": new_str, "found": False}


@editor_bp.route("/editor/propose", methods=["POST"])
def propose():
    """
    Receive AI-generated proposal JSON and return enriched preview data.
    Frontend sends the raw AI response text, we extract and validate the proposal.
    """
    data = request.json or {}
    ai_response = data.get("ai_response", "")

    proposal = extract_json_proposal(ai_response)
    if not proposal:
        # Categorize the failure reason for a helpful error message
        snippet = ai_response[:300].strip() if ai_response else "(empty response)"

        if not ai_response:
            reason = "The AI returned an empty response. Please try again."
        elif "CODE_EDITOR_MODE" in ai_response:
            reason = ("The AI used an incorrect JSON format (CODE_EDITOR_MODE). "
                      "Please try again with a more specific request.")
        elif "{" not in ai_response:
            reason = ("The AI responded with plain text instead of JSON. "
                      "Try saying: 'Edit the code to change X to Y'.")
        elif "\"action\"" in ai_response and "\"changes\"" not in ai_response:
            reason = ("The AI produced a JSON object but used the wrong keys. "
                      "Expected a 'changes' array. Please retry.")
        else:
            reason = "No valid JSON proposal was found in the AI response. Please retry with a clearer request."

        print(f"[EDITOR] Proposal extraction failed. Reason: {reason}")
        print(f"[EDITOR] Response snippet: {snippet}")
        return jsonify({
            "error": reason,
            "ai_response_snippet": snippet
        }), 400

    changes = proposal.get("changes", [])
    if not changes:
        return jsonify({"error": "No changes in proposal. Please provide specific editing instructions."}), 400

    # Enrich each change with before/after preview
    enriched = []
    for change in changes:
        preview = {}
        if change.get("action") in ("replace", "append"):
            preview = get_file_preview(
                change.get("file", ""),
                change.get("old", ""),
                change.get("new", "")
            )
        enriched.append({**change, "preview": preview})

    return jsonify({
        "summary":  proposal.get("summary", ""),
        "changes":  enriched,
        "total":    len(enriched)
    })


@editor_bp.route("/editor/apply", methods=["POST"])
def apply():
    """Apply a list of approved changes to the codebase."""
    data    = request.json or {}
    changes = data.get("changes", [])

    if not changes:
        return jsonify({"error": "No changes provided."}), 400

    results = []
    for change in changes:
        success, error = apply_change(change)
        results.append({
            "file":    change.get("file"),
            "action":  change.get("action"),
            "success": success,
            "error":   error
        })

    applied = sum(1 for r in results if r["success"])
    failed  = len(results) - applied

    for r in results:
        if not r["success"]:
            print(f"[EDITOR] FAILED {r['file']}: {r['error']}")

    print(f"[EDITOR] Applied {applied}/{len(results)} changes")
    return jsonify({"results": results, "applied": applied, "failed": failed})


@editor_bp.route("/editor/restore", methods=["POST"])
def restore():
    """Restore a file from a backup."""
    backup_filename = request.json.get("backup", "")
    if not backup_filename:
        return jsonify({"error": "No backup filename provided."}), 400

    success, msg = restore_file(backup_filename)
    if success:
        return jsonify({"status": "restored", "file": msg})
    return jsonify({"error": msg}), 400


@editor_bp.route("/editor/backups", methods=["GET"])
def backups():
    """List available backups."""
    return jsonify({"backups": list_backups()})
