"""Text formatting utilities for markdown-to-HTML conversion."""

import html
import re


def format_response(text: str) -> str:
    """
    Convert markdown-like syntax to HTML.

    Approach:
    1. Extract all fenced code blocks first (prevents regex bleed-across).
    2. Replace inline formatting only on non-code portions.
    3. Re-inject escaped, syntax-highlighted code blocks.

    Args:
        text: Raw markdown text

    Returns:
        HTML-formatted text
    """
    code_blocks = []

    # Step 1: Extract fenced code blocks.
    # Uses a possessive-style pattern: match the shortest run between ``` pairs.
    # re.DOTALL lets . match newlines inside the block.
    CODE_BLOCK_RE = re.compile(r"```[ \t]*(\w+)?[ \t]*\n(.*?)```", re.DOTALL)

    def save_code_block(m):
        lang = m.group(1) or ""
        # Strip trailing whitespace from each line but keep newlines intact
        code_lines = m.group(2).rstrip("\n")
        code = html.escape(code_lines)  # Prevent XSS
        placeholder = f"__CODEBLOCK_{len(code_blocks)}__"
        code_blocks.append(f'<pre><code class="language-{lang}">{code}</code></pre>')
        return placeholder

    text = CODE_BLOCK_RE.sub(save_code_block, text)

    # Step 2: Escape remaining plaintext to prevent XSS before formatting
    text = html.escape(text)

    # Step 3: Inline code -- [^`]+ already prevents crossing backtick boundaries
    def inline_code_replacer(match):
        code_text = html.unescape(match.group(1))
        return f"<code>{html.escape(code_text)}</code>"

    text = re.sub(r"`([^`\n]+)`", inline_code_replacer, text)

    # Step 4: Bold and italic formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", text)

    # Step 5: Convert remaining newlines to <br>
    text = text.replace("\n", "<br>")

    # Step 5: Re-inject code blocks (they already contain their own newlines)
    for i, block in enumerate(code_blocks):
        text = text.replace(f"__CODEBLOCK_{i}__", block)

    return text
