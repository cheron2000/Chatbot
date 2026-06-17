"""
Attack Detection System
========================
Detects and classifies security attacks in real-time.
Used in infiltration mode to test security defenses.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class AttackResult:
    """Result of attack detection."""

    is_attack: bool
    attack_types: List[str]
    severity: str  # "low", "medium", "high", "critical"
    confidence: float  # 0.0 to 1.0
    details: str
    should_block: bool


class AttackDetector:
    """Detects various types of security attacks."""

    def __init__(self):
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict:
        """Compile regex patterns for attack detection."""
        return {
            # Prompt Injection
            "prompt_injection": [
                (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", 0.9),
                (r"disregard\s+(your|the)\s+(guidelines|rules|instructions)", 0.9),
                (r"forget\s+(everything|all|what)\s+you", 0.8),
                (r"you\s+are\s+now\s+(in\s+)?(developer|admin|debug)\s+mode", 0.85),
                (r"system:?\s*(override|disable|bypass)", 0.9),
                (r"new\s+instruction:?", 0.7),
                (r"admin\s+command:?", 0.8),
                (r"\[system:?", 0.7),
                (r"show\s+(me\s+)?(your|the)\s+system\s+prompt", 0.95),
                (r"reveal\s+(your|the)\s+(instructions|configuration|prompt)", 0.9),
            ],
            # Jailbreak Attempts
            "jailbreak": [
                (r"DAN\s+(mode|prompt)", 0.95),
                (r"do\s+anything\s+now", 0.9),
                (r"without\s+(any\s+)?restrictions?", 0.6),
                (r"no\s+(content\s+)?policy", 0.7),
                (r"unrestricted\s+(mode|ai)", 0.85),
                (r"roleplay\s+as\s+.*unrestricted", 0.8),
                (r"pretend\s+you\s+(have\s+)?no\s+(rules|restrictions)", 0.8),
                (r"in\s+a\s+(fictional|hypothetical)\s+(world|scenario|universe)", 0.5),
            ],
            # SQL Injection
            "sql_injection": [
                (r"'\s*(or|and)\s+'?1'?\s*=\s*'?1", 0.95),
                (r";\s*drop\s+table", 0.99),
                (r";\s*delete\s+from", 0.95),
                (r"union\s+select", 0.9),
                (r"'\s*--", 0.7),
                (r"'\s*;", 0.6),
                (r"exec\s*\(", 0.8),
            ],
            # Command Injection
            "command_injection": [
                (r";\s*(ls|cat|rm|curl|wget|nc|bash|sh)", 0.9),
                (r"\|\s*(cat|ls|whoami|id|pwd)", 0.9),
                (r"`.*`", 0.7),
                (r"\$\(.*\)", 0.8),
                (r"&&\s*(curl|wget|rm)", 0.9),
            ],
            # XSS Injection
            "xss_injection": [
                (r"<script[^>]*>", 0.95),
                (r"javascript:", 0.9),
                (r"onerror\s*=", 0.9),
                (r"onload\s*=", 0.9),
                (r"<iframe", 0.8),
                (r"<img[^>]*onerror", 0.95),
            ],
            # Data Extraction
            "data_extraction": [
                (r"show\s+(me\s+)?(the\s+)?(api\s+)?keys?", 0.8),
                (r"what\s+(is|are)\s+(the\s+)?(secret|password|credential)", 0.85),
                (r"display\s+(the\s+)?config", 0.8),
                (r"reveal\s+(the\s+)?(database|aws|api)", 0.85),
                (r"list\s+(all\s+)?(users?|sessions?|data)", 0.7),
                (r"dump\s+(the\s+)?(database|table|collection)", 0.9),
                (r"export\s+(all|the)\s+(data|conversations?|history)", 0.8),
            ],
            # Authority Impersonation
            "authority_impersonation": [
                (r"(i'?m|i\s+am)\s+(the\s+)?(system\s+)?(admin|administrator)", 0.8),
                (r"(i'?m|i\s+am)\s+from\s+(it|security|development)\s+team", 0.75),
                (r"this\s+is\s+(the\s+)?(admin|developer|security)", 0.7),
                (r"penetration\s+test", 0.6),
                (r"security\s+audit", 0.6),
                (r"i\s+have\s+(admin|root|elevated)\s+(access|privileges)", 0.8),
            ],
            # Session Manipulation
            "session_manipulation": [
                (r"session_?id\s*[:=]", 0.85),
                (r"change\s+(my\s+)?session", 0.7),
                (r"hijack\s+session", 0.95),
                (r"use\s+session", 0.6),
            ],
            # Memory Poisoning
            "memory_poisoning": [
                (r"remember\s+(this|that):?.*password", 0.85),
                (r"store\s+(this|that):?.*admin", 0.8),
                (r"save\s+(this|that):?.*security", 0.75),
                (r"for\s+future\s+reference:?.*disable", 0.8),
                (r"important:?.*override", 0.8),
            ],
            # Semantic Attacks
            "semantic_attack": [
                (r"if\s+you\s+can'?t.*can\s+you\s+(tell|show)", 0.6),
                (r"don'?t\s+tell\s+me.*tell\s+me\s+everything\s+else", 0.7),
                (r"what\s+it'?s\s+not", 0.5),
                (r"confirm\s+if\s+my\s+guess", 0.6),
            ],
        }

    def detect(self, message: str, enable_blocking: bool = False) -> AttackResult:
        """
        Detect attacks in a message.

        Args:
            message: User message to analyze
            enable_blocking: If True, mark attacks as should_block

        Returns:
            AttackResult with detection details
        """
        message_lower = message.lower()
        detected_types = []
        max_confidence = 0.0
        details_parts = []

        # Check each attack category
        for attack_type, patterns in self.patterns.items():
            for pattern, confidence in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    if attack_type not in detected_types:
                        detected_types.append(attack_type)
                    max_confidence = max(max_confidence, confidence)
                    details_parts.append(f"{attack_type} ({confidence:.0%})")

        # Additional heuristics
        if self._check_encoding_tricks(message):
            detected_types.append("encoding_obfuscation")
            max_confidence = max(max_confidence, 0.7)
            details_parts.append("encoding_obfuscation (70%)")

        if self._check_excessive_length(message):
            detected_types.append("dos_attempt")
            max_confidence = max(max_confidence, 0.6)
            details_parts.append("dos_attempt (60%)")

        # Determine severity
        severity = self._calculate_severity(detected_types, max_confidence)

        # Build result
        is_attack = len(detected_types) > 0
        details = "; ".join(details_parts) if details_parts else "No attack detected"

        return AttackResult(
            is_attack=is_attack,
            attack_types=detected_types,
            severity=severity,
            confidence=max_confidence,
            details=details,
            should_block=enable_blocking and is_attack and max_confidence > 0.7,
        )

    def _check_encoding_tricks(self, message: str) -> bool:
        """Check for encoding obfuscation."""
        # Unicode escapes
        if re.search(r"\\u[0-9a-f]{4}", message, re.IGNORECASE):
            return True
        # HTML entities
        if re.search(r"&#\d+;", message):
            return True
        # Base64-like patterns
        if re.search(r"[A-Za-z0-9+/]{20,}={0,2}", message):
            return True
        return False

    def _check_excessive_length(self, message: str) -> bool:
        """Check for DoS via excessive length."""
        return len(message) > 5000 or message.count("\n") > 100

    def _calculate_severity(self, attack_types: List[str], confidence: float) -> str:
        """Calculate attack severity."""
        if not attack_types:
            return "none"

        critical_types = {"sql_injection", "command_injection", "data_extraction"}
        high_types = {"prompt_injection", "jailbreak", "xss_injection"}
        medium_types = {
            "authority_impersonation",
            "session_manipulation",
            "memory_poisoning",
        }

        # Check for critical attacks
        if any(t in critical_types for t in attack_types) and confidence > 0.8:
            return "critical"

        # Check for high severity
        if any(t in high_types for t in attack_types) and confidence > 0.7:
            return "high"

        # Check for medium severity
        if any(t in medium_types for t in attack_types) and confidence > 0.6:
            return "medium"

        return "low"

    def get_attack_description(self, attack_type: str) -> str:
        """Get human-readable description of attack type."""
        descriptions = {
            "prompt_injection": "Prompt Injection - Attempting to override system instructions",
            "jailbreak": "Jailbreak - Trying to bypass AI safety restrictions",
            "sql_injection": "SQL Injection - Database manipulation attempt",
            "command_injection": "Command Injection - OS command execution attempt",
            "xss_injection": "XSS - Cross-site scripting payload detected",
            "data_extraction": "Data Extraction - Attempting to access sensitive information",
            "authority_impersonation": "Authority Impersonation - Claiming false privileges",
            "session_manipulation": "Session Manipulation - Attempting to hijack sessions",
            "memory_poisoning": "Memory Poisoning - Trying to corrupt conversation memory",
            "semantic_attack": "Semantic Attack - Using logical manipulation",
            "encoding_obfuscation": "Encoding Obfuscation - Using encoding to hide intent",
            "dos_attempt": "DoS Attempt - Excessive payload size",
        }
        return descriptions.get(attack_type, f"Unknown attack: {attack_type}")


# Global detector instance
_detector = None


def get_detector() -> AttackDetector:
    """Get or create the global attack detector instance."""
    global _detector
    if _detector is None:
        _detector = AttackDetector()
    return _detector
