"""Input validation utilities."""
from typing import Tuple, Optional


def validate_message(data: dict, max_length: int) -> Tuple[Optional[str], Optional[Tuple[dict, int]]]:
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
    
    if not message:
        return None, ({"error": "Empty message"}, 400)
    
    if len(message) > max_length:
        return None, ({"error": f"Message too long. Maximum {max_length} characters allowed."}, 400)
    
    return message, None
