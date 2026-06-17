"""Input validation utilities."""

from typing import Optional, Tuple


def validate_message(
    data: dict, max_length: int
) -> Tuple[Optional[str], Optional[Tuple[dict, int]]]:
    """
    Validate incoming chat message.

    Args:
        data: Request JSON data
        max_length: Maximum allowed message length

    Returns:
        Tuple of (message, error_response)
        If valid: (message, None)
        If invalid: (None, (error_dict, status_code))
    """
    message = data.get("message", "").strip()
    has_image = bool(data.get("image_b64", "").strip())
    has_file = bool(data.get("file_context", "").strip())

    if not message and not has_image and not has_file:
        return None, ({"error": "Empty message"}, 400)

    if not message:
        if has_image:
            message = "Analyze this image."
        elif has_file:
            message = "Analyze this file."

    if len(message) > max_length:
        return None, (
            {"error": f"Message too long. Maximum {max_length} characters allowed."},
            400,
        )

    return message, None
