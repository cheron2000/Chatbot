"""Memory management for conversation history."""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional
import boto3


class MemoryManager:
    """Manages short-term and long-term conversation memory."""
    
    def __init__(self, session_id: str, memory_dir: str, bedrock_client,
                 summary_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        """
        Initialize memory manager.

        Args:
            session_id: Unique session identifier
            memory_dir: Directory for long-term memory files
            bedrock_client: Boto3 Bedrock client for summary generation
            summary_model_id: Bedrock model ID used for summary generation
        """
        self.session_id = session_id
        self.memory_dir = memory_dir
        self.bedrock_client = bedrock_client
        self.summary_model_id = summary_model_id
        os.makedirs(memory_dir, exist_ok=True)
    
    def get_longterm_path(self) -> str:
        """Return the filesystem path for this session's long-term memory file."""
        return os.path.join(self.memory_dir, f"{self.session_id}_longterm.json")
    
    def load_longterm(self) -> str:
        """
        Load the long-term summary string for this session.
        
        Returns:
            Summary string, or empty string if none exists
        """
        path = self.get_longterm_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f).get("summary", "")
        except (FileNotFoundError, json.JSONDecodeError):
            return ""
    
    def save_longterm(self, summary: str) -> None:
        """
        Persist an updated long-term summary to disk.
        
        Args:
            summary: Updated conversation summary
        """
        path = self.get_longterm_path()
        payload = {
            "summary": summary,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    
    def generate_summary_async(self, previous_summary: str, 
                               user_message: str, assistant_reply: str) -> None:
        """
        Call the model (non-streaming) to produce an updated conversation summary
        and write it to disk. Runs in a background thread — never blocks the response.

        The summary is intentionally concise (≤ 150 tokens) so it doesn't consume
        excessive context space when prepended to future prompts.
        
        Args:
            previous_summary: Existing summary from previous interactions
            user_message: Latest user message
            assistant_reply: Latest assistant response
        """
        def _generate():
            prompt = (
                "You are a memory manager for a chatbot. "
                "Your only job is to maintain a short, factual summary of the conversation.\n\n"
                f"Previous summary:\n{previous_summary or 'None yet.'}\n\n"
                f"New exchange:\n"
                f"User: {user_message}\n"
                f"Assistant: {assistant_reply[:1000]}\n\n"  # cap to avoid huge prompts
                "Write an updated summary (2–4 sentences, max 150 words) that captures "
                "all key topics, facts, preferences, and context from the full conversation. "
                "Be specific. Do NOT include greetings or filler. Output ONLY the summary text."
            )
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}]
            }
            try:
                response = self.bedrock_client.invoke_model(
                    modelId=self.summary_model_id,
                    body=json.dumps(body)
                )
                result = json.loads(response["body"].read())
                new_summary = result["content"][0]["text"].strip()
                self.save_longterm(new_summary)
                print(f"[MEMORY] Summary updated for session {self.session_id[:8]}…")
            except Exception as e:
                print(f"[WARN] Summary generation failed: {e}")
                # On failure, keep the old summary — don't erase it
                if previous_summary:
                    self.save_longterm(previous_summary)
        
        # Fire and forget
        t = threading.Thread(target=_generate, daemon=True)
        t.start()
    
    def delete_longterm(self) -> None:
        """Delete the long-term memory file for this session."""
        path = self.get_longterm_path()
        if os.path.exists(path):
            os.remove(path)
            print(f"[MEMORY] Deleted long-term memory for session {self.session_id[:8]}…")
