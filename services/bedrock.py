"""AWS Bedrock client and streaming services."""
import json
import boto3
from botocore.config import Config
from typing import Generator, Tuple, Dict, Any, List
from config import BedrockConfig


class BedrockService:
    """Manages AWS Bedrock client and model interactions."""
    
    def __init__(self, config: BedrockConfig):
        """
        Initialize Bedrock service.
        
        Args:
            config: Bedrock configuration
        """
        self.config = config
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=config.region,
            config=Config(
                connect_timeout=config.connect_timeout,
                read_timeout=config.read_timeout,
                retries={"max_attempts": config.max_retries}
            )
        )
    
    def stream_anthropic(self, messages: List[Dict[str, str]], long_term_summary: str = "", 
                        max_tokens: int = 4096,
                        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0") -> Generator[Dict[str, Any], None, None]:
        """
        Stream tokens from an Anthropic model via Bedrock SSE.

        long_term_summary is injected as a system prompt so the model has persistent
        context from previous sessions without blowing up the messages array.
        
        Args:
            messages: Conversation history
            long_term_summary: Persistent context summary
            max_tokens: Maximum tokens to generate
            model_id: Bedrock model ID to invoke
            
        Yields:
            Dictionaries with token data or completion info
        """
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }
        if long_term_summary:
            body["system"] = (
                "The following is a summary of the conversation history so far "
                "(may span previous sessions). Use it as background context:\n\n"
                + long_term_summary
            )
        
        response = self.client.invoke_model_with_response_stream(
            modelId=model_id,
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
                yield {"type": "token", "text": token}

            elif chunk_type == "message_delta":
                output_tokens = chunk.get("usage", {}).get("output_tokens", 0)

            elif chunk_type == "message_start":
                input_tokens = chunk.get("message", {}).get("usage", {}).get("input_tokens", 0)

        # Final event with formatted HTML and token counts
        yield {
            "type": "done",
            "full_text": full_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    
    def stream_nvidia(self, messages: List[Dict[str, str]], long_term_summary: str = "",
                     max_tokens: int = 4096,
                     model_id: str = "nvidia.nemotron-nano-12b-v2",
                     image_b64: str = "", image_mime: str = "image/jpeg") -> Generator[Dict[str, Any], None, None]:
        """
        Stream tokens from an NVIDIA model via Bedrock SSE.
        Supports optional image input for vision analysis.
        """
        # If image provided, inject it into the last user message as a content list
        messages_with_ctx = list(messages)
        if image_b64 and messages_with_ctx and messages_with_ctx[-1]["role"] == "user":
            last = messages_with_ctx[-1]
            messages_with_ctx[-1] = {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{image_mime};base64,{image_b64}"}},
                    {"type": "text", "text": last["content"]}
                ]
            }

        # Prepend system context if we have long-term memory
        if long_term_summary:
            system_msg = {
                "role": "system",
                "content": (
                    "The following is a summary of the conversation history so far "
                    "(may span previous sessions). Use it as background context:\n\n"
                    + long_term_summary
                )
            }
            messages_with_ctx = [system_msg] + messages_with_ctx

        body = {
            "messages": messages_with_ctx,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": True
        }
        
        response = self.client.invoke_model_with_response_stream(
            modelId=model_id,
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
                    yield {"type": "token", "text": token}

            # Usage comes in the last chunk
            if "usage" in chunk:
                input_tokens = chunk["usage"].get("prompt_tokens", 0)
                output_tokens = chunk["usage"].get("completion_tokens", 0)

        yield {
            "type": "done",
            "full_text": full_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
