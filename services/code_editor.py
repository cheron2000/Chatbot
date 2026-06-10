"""Code editor service — safe file operations with backup and validation."""
import os
import py_compile
import shutil
import json
import tempfile
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR   = os.path.join(PROJECT_ROOT, "backups")
CHANGE_LOG   = os.path.join(PROJECT_ROOT, "changes.log")

# Files that can NEVER be modified
PROTECTED_FILES = {
    "config.py", ".env", "requirements.txt",
    "app_refactored.py", "changes.log"
}

# Allowed file extensions for editing
EDITABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".md", ".txt", ".sh", ".sql"
}


def _safe_path(relative_path: str) -> str | None:
    """
    Resolve relative path to absolute, ensure it stays inside project root.
    Returns None if the path is outside the project or protected.
    """
    abs_path = os.path.normpath(os.path.join(PROJECT_ROOT, relative_path))

    # Must stay inside project root
    if not abs_path.startswith(PROJECT_ROOT):
        return None

    # Must not be a protected file
    filename = os.path.basename(abs_path)
    if filename in PROTECTED_FILES:
        return None

    # Must have an editable extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in EDITABLE_EXTENSIONS:
        return None

    return abs_path


def backup_file(abs_path: str) -> str:
    """Copy file to backups/ with timestamp. Returns backup path."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename  = os.path.basename(abs_path)
    backup_path = os.path.join(BACKUP_DIR, f"{timestamp}_{filename}")
    if os.path.exists(abs_path):
        shutil.copy2(abs_path, backup_path)
    return backup_path


def validate_python(code: str) -> tuple[bool, str]:
    """Compile-check Python code without executing it."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                         delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp = f.name
        py_compile.compile(tmp, doraise=True)
        os.unlink(tmp)
        return True, ""
    except py_compile.PyCompileError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def _log_change(action: dict, backup_path: str) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file":      action.get("file"),
        "action":    action.get("action"),
        "backup":    backup_path,
        "reason":    action.get("reason", "")
    }
    with open(CHANGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def apply_change(action: dict) -> tuple[bool, str]:
    """
    Apply a single change action to a file.

    action = {
      "file":   "routes/chat.py",        # relative to project root
      "action": "replace" | "append" | "create",
      "old":    "exact string to replace",  # only for replace
      "new":    "new content",
      "reason": "why this change"
    }

    Returns (success, error_message)
    """
    rel_path = action.get("file", "")
    act_type = action.get("action", "")
    new_content = action.get("new", "")

    abs_path = _safe_path(rel_path)
    if not abs_path:
        return False, f"File '{rel_path}' is protected or outside project root."

    # ── Validate Python before touching disk ──
    if abs_path.endswith(".py") and act_type in ("replace", "create"):
        if act_type == "replace":
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    current = f.read()
                preview = current.replace(action.get("old", ""), new_content, 1)
            except FileNotFoundError:
                preview = new_content
        else:
            preview = new_content

        ok, err = validate_python(preview)
        if not ok:
            return False, f"Python syntax error: {err}"

    # ── Backup ──
    backup_path = backup_file(abs_path)

    try:
        if act_type == "create":
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        elif act_type == "append":
            with open(abs_path, "a", encoding="utf-8") as f:
                f.write("\n" + new_content)

        elif act_type == "replace":
            old_str = action.get("old", "")
            if not os.path.exists(abs_path):
                return False, f"File '{rel_path}' does not exist."
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            if old_str not in content:
                return False, f"Target string not found in '{rel_path}'."
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content.replace(old_str, new_content, 1))
        else:
            return False, f"Unknown action: {act_type}"

        _log_change(action, backup_path)
        print(f"[EDITOR] Applied '{act_type}' to {rel_path} (backup: {os.path.basename(backup_path)})")
        return True, ""

    except Exception as e:
        # Restore backup on failure
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, abs_path)
        return False, str(e)


def restore_file(backup_filename: str) -> tuple[bool, str]:
    """Restore a file from a backup by filename."""
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        return False, "Backup not found."

    # Extract original filename (strip timestamp prefix: YYYYMMDD_HHMMSS_)
    parts = backup_filename.split("_", 2)
    if len(parts) < 3:
        return False, "Invalid backup filename."
    original_name = parts[2]

    # Search for original file in project
    for root, _, files in os.walk(PROJECT_ROOT):
        if "backups" in root:
            continue
        if original_name in files:
            dest = os.path.join(root, original_name)
            shutil.copy2(backup_path, dest)
            print(f"[EDITOR] Restored {original_name} from {backup_filename}")
            return True, dest

    return False, f"Could not locate original file '{original_name}' in project."


def list_backups() -> list:
    """Return list of available backups sorted newest first."""
    if not os.path.exists(BACKUP_DIR):
        return []
    files = sorted(os.listdir(BACKUP_DIR), reverse=True)
    return files[:20]  # last 20 backups
