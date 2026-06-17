"""Prompt enhancement utilities to improve AI response quality."""

from typing import Dict, List


class PromptEnhancer:
    """Enhances user prompts for better AI responses."""

    # Patterns that indicate specific types of requests
    PATTERNS = {
        "code": [
            "code",
            "function",
            "script",
            "program",
            "implement",
            "write a",
            "create a",
        ],
        "explanation": ["explain", "what is", "how does", "why", "tell me about"],
        "debug": ["error", "bug", "not working", "fix", "issue", "problem"],
        "comparison": ["difference", "compare", "vs", "versus", "better"],
        "list": ["list", "examples", "types of", "kinds of"],
    }

    # Enhancement templates for different request types
    ENHANCEMENTS = {
        "code": (
            "Please provide a code solution with the following:\n"
            "1. Clear, well-commented code\n"
            "2. Explanation of how it works\n"
            "3. Example usage if applicable\n\n"
            "Request: {prompt}"
        ),
        "explanation": (
            "Please provide a clear explanation that includes:\n"
            "1. Simple definition\n"
            "2. Key concepts\n"
            "3. Practical examples\n\n"
            "Question: {prompt}"
        ),
        "debug": (
            "Please help debug this issue by:\n"
            "1. Identifying the likely cause\n"
            "2. Providing a solution\n"
            "3. Explaining how to prevent it\n\n"
            "Problem: {prompt}"
        ),
        "comparison": (
            "Please compare these items by:\n"
            "1. Key differences\n"
            "2. Pros and cons of each\n"
            "3. Use case recommendations\n\n"
            "Comparison request: {prompt}"
        ),
        "list": (
            "Please provide a comprehensive list with:\n"
            "1. Brief description for each item\n"
            "2. Organized by category if applicable\n"
            "3. Most important/common items first\n\n"
            "List request: {prompt}"
        ),
    }

    # Quality improvement rules
    QUALITY_RULES = [
        {
            "name": "Add context for vague questions",
            "triggers": ["it", "this", "that", "they"],
            "enhancement": "\n\nNote: Please provide specific details about what you're referring to for a more accurate response.",
        },
        {
            "name": "Request examples for abstract concepts",
            "triggers": ["concept", "theory", "principle", "idea"],
            "enhancement": "\n\nPlease include concrete examples to illustrate the concept.",
        },
        {
            "name": "Add accuracy requirement for facts",
            "triggers": ["when", "who", "where", "date", "year"],
            "enhancement": "\n\nPlease provide accurate, verifiable information with sources if possible.",
        },
    ]

    @staticmethod
    def detect_request_type(prompt: str) -> str:
        """
        Detect the type of request based on keywords.

        Args:
            prompt: User's original prompt

        Returns:
            Request type ('code', 'explanation', etc.) or 'general'
        """
        prompt_lower = prompt.lower()

        for request_type, keywords in PromptEnhancer.PATTERNS.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return request_type

        return "general"

    @staticmethod
    def apply_quality_rules(prompt: str) -> str:
        """
        Apply quality improvement rules to the prompt.

        Args:
            prompt: User's prompt

        Returns:
            Enhanced prompt with quality improvements
        """
        enhanced = prompt
        prompt_lower = prompt.lower()

        for rule in PromptEnhancer.QUALITY_RULES:
            if any(trigger in prompt_lower for trigger in rule["triggers"]):
                enhanced += rule["enhancement"]

        return enhanced

    @staticmethod
    def enhance_prompt(prompt: str, enable_enhancement: bool = True) -> Dict[str, str]:
        """
        Enhance user prompt for better AI responses.

        Args:
            prompt: Original user prompt
            enable_enhancement: Whether to apply enhancements

        Returns:
            Dictionary with 'original', 'enhanced', and 'type' keys
        """
        if not enable_enhancement or len(prompt) > 500:
            # Don't enhance very long prompts (user likely knows what they want)
            return {
                "original": prompt,
                "enhanced": prompt,
                "type": "general",
                "was_enhanced": False,
            }

        # Detect request type
        request_type = PromptEnhancer.detect_request_type(prompt)

        # Apply type-specific enhancement
        if request_type != "general" and request_type in PromptEnhancer.ENHANCEMENTS:
            enhanced = PromptEnhancer.ENHANCEMENTS[request_type].format(prompt=prompt)
        else:
            enhanced = prompt

        # Apply quality rules
        enhanced = PromptEnhancer.apply_quality_rules(enhanced)

        return {
            "original": prompt,
            "enhanced": enhanced,
            "type": request_type,
            "was_enhanced": enhanced != prompt,
        }

    @staticmethod
    def add_system_instructions(request_type: str) -> str:
        """
        Get system-level instructions based on request type.

        Args:
            request_type: Type of request detected

        Returns:
            System instructions to prepend to conversation
        """
        instructions = {
            "code": (
                "You are a helpful coding assistant. Provide clean, well-commented code "
                "with explanations. Always include error handling and follow best practices."
            ),
            "explanation": (
                "You are a clear and patient teacher. Break down complex topics into "
                "simple terms. Use analogies and examples to aid understanding."
            ),
            "debug": (
                "You are an expert debugger. Analyze problems systematically, identify "
                "root causes, and provide clear solutions with explanations."
            ),
            "comparison": (
                "You are an objective analyst. Provide balanced comparisons with clear "
                "pros and cons. Consider different use cases and contexts."
            ),
            "list": (
                "You are a knowledgeable organizer. Provide comprehensive, well-structured "
                "lists with brief descriptions. Prioritize by importance or relevance."
            ),
            "general": (
                "You are a helpful, accurate, and friendly assistant. Provide clear, "
                "concise responses. Ask for clarification if the request is ambiguous."
            ),
        }

        return instructions.get(request_type, instructions["general"])


def enhance_user_prompt(prompt: str, enable: bool = True) -> Dict[str, str]:
    """
    Convenience function to enhance a user prompt.

    Args:
        prompt: User's original prompt
        enable: Whether enhancement is enabled

    Returns:
        Dictionary with enhancement details
    """
    return PromptEnhancer.enhance_prompt(prompt, enable)
