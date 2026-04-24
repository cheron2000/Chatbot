"""Streaming service with model fallback logic."""
import json
from typing import Generator, List
from services.bedrock import BedrockService
from utils.formatting import format_response


class StreamingService:
    """Handles streaming responses with automatic model fallback."""
    
    def __init__(self, bedrock_service: BedrockService, models: List[str], max_tokens: int):
        """
        Initialize streaming service.
        
        Args:
            bedrock_service: Bedrock service instance
            models: List of model IDs to try in order
            max_tokens: Maximum tokens per response
        """
        self.bedrock_service = bedrock_service
        self.models = models
        self.max_tokens = max_tokens
    
    def stream_with_fallback(self, messages: List[dict], long_term_summary: str = "") -> Generator[str, None, None]:
        """
        Try models in order. If one fails, fall back to the next.

        Passes long_term_summary into each model function so they can inject
        it as system-level context. If a model fails AFTER already yielding
        tokens (mid-stream), emits an error event to the frontend.
        
        Args:
            messages: Conversation history
            long_term_summary: Persistent context summary
            
        Yields:
            SSE-formatted event strings
        """
        for model_id in self.models:
            tokens_yielded = False
            try:
                print(f"[INFO] Streaming from: {model_id}")
                
                # Choose the appropriate streaming method
                if "anthropic" in model_id:
                    gen = self.bedrock_service.stream_anthropic(
                        messages, long_term_summary, self.max_tokens, model_id
                    )
                elif "nvidia" in model_id:
                    gen = self.bedrock_service.stream_nvidia(
                        messages, long_term_summary, self.max_tokens, model_id
                    )
                else:
                    continue

                # Stream events
                for event in gen:
                    if event["type"] == "token":
                        tokens_yielded = True
                        yield f"data: {json.dumps({'type': 'token', 'text': event['text']})}\n\n"
                    
                    elif event["type"] == "done":
                        # Format the full text as HTML
                        formatted = format_response(event["full_text"])
                        yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': event['input_tokens'], 'output_tokens': event['output_tokens']})}\n\n"

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
        formatted = format_response(error_msg)
        yield f"data: {json.dumps({'type': 'done', 'html': formatted, 'input_tokens': 0, 'output_tokens': 0})}\n\n"
