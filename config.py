"""Application configuration management."""
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class BedrockConfig:
    """AWS Bedrock service configuration."""
    region: str = "us-east-1"
    connect_timeout: int = 5
    read_timeout: int = 60
    max_retries: int = 0
    models: List[str] = field(default_factory=lambda: [
        "anthropic.claude-3-haiku-20240307-v1:0",
        "nvidia.nemotron-nano-12b-v2",
    ])


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    max_short_term: int = 10
    max_summary_tokens: int = 200
    summary_model: str = "anthropic.claude-3-haiku-20240307-v1:0"
    memory_dir: str = "memory"
    vector_db_dir: str = "vector_db"
    enable_vector_memory: bool = True
    vector_search_results: int = 3


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    default_limit: str = "200 per day"
    chat_limit: str = "20 per minute"


@dataclass
class AppConfig:
    """Main application configuration."""
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", "dev-secret-change-in-prod"))
    session_type: str = "filesystem"
    session_file_dir: str = ".flask_sessions"
    session_permanent: bool = False
    max_message_length: int = 4000
    max_tokens: int = 4096
    enable_prompt_enhancement: bool = True  # Enable automatic prompt improvement
    
    # Infiltration Mode Settings
    enable_infiltration_mode: bool = True  # Allow users to enable infiltration mode
    infiltration_auto_block: bool = False  # Auto-block detected attacks (False = log only)
    infiltration_log_file: str = "infiltration_log.json"  # Log file for detected attacks
    
    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)


# Global config instance
config = AppConfig()
