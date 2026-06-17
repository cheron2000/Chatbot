"""File processor -- extracts text content from uploaded files."""

import base64
import io

# Supported file types
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

TEXT_EXTENSIONS = {
    # Code
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".cs",
    ".go",
    ".rb",
    ".rs",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".html",
    ".css",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".env",
    ".md",
    ".txt",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_CHARS = 12000  # max chars sent to AI


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {i+1}]\n{text.strip()}")
        return "\n\n".join(pages)[:MAX_TEXT_CHARS]
    except ImportError:
        return "[PDF parsing requires pypdf. Run: py -3.10 -m pip install pypdf]"
    except Exception as e:
        return f"[PDF parsing failed: {e}]"


def process_file(filename: str, mime_type: str, file_bytes: bytes) -> dict:
    """
    Process an uploaded file and return a dict with:
    - type: "image" | "text"
    - content: extracted text OR base64 for images
    - mime: mime type
    - filename: original filename
    - summary: short description for the UI
    """
    if len(file_bytes) > MAX_FILE_SIZE:
        return {"type": "error", "content": "File too large. Max 10MB allowed."}

    # -- Images -> pass as base64 to vision model --
    if mime_type in IMAGE_TYPES:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        return {
            "type": "image",
            "content": b64,
            "mime": mime_type,
            "filename": filename,
            "summary": f"Image: {filename}",
        }

    # -- PDF --
    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
        return {
            "type": "text",
            "content": f"[File: {filename}]\n\n{text}",
            "filename": filename,
            "summary": f"PDF: {filename}",
        }

    # -- Code / text files --
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in TEXT_EXTENSIONS or mime_type.startswith("text/"):
        try:
            text = file_bytes.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
            return {
                "type": "text",
                "content": f"[File: {filename}]\n```{ext.lstrip('.')}\n{text}\n```",
                "filename": filename,
                "summary": f"File: {filename}",
            }
        except Exception as e:
            return {"type": "error", "content": f"Could not read file: {e}"}

    return {"type": "error", "content": f"Unsupported file type: {mime_type}"}
