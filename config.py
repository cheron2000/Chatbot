"""Application configuration management."""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class BedrockConfig:
    """AWS Bedrock service configuration."""

    region: str = "us-east-1"
    connect_timeout: int = 5
    read_timeout: int = 60
    max_retries: int = 0
    models: List[str] = field(
        default_factory=lambda: [
            "nvidia.nemotron-nano-12b-v2",
        ]
    )


@dataclass
class MemoryConfig:
    """Memory management configuration."""

    max_short_term: int = 10
    max_summary_tokens: int = 200
    summary_model: str = "nvidia.nemotron-nano-12b-v2"
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
class ClassifierConfig:
    """Skin lesion classifier configuration."""
    
    model_path: str = "best_efficientnet_ham10000.pth"
    device: str = "auto"  # "cpu", "cuda", or "auto"
    enable_caching: bool = True
    cache_size: int = 100
    auto_unload_minutes: int = 30
    max_image_size_mb: int = 10
    rate_limit: str = "10 per minute"


@dataclass
class AppConfig:
    """Main application configuration."""

    secret_key: str = field(
        default_factory=lambda: os.environ.get(
            "SECRET_KEY", "dev-secret-change-in-prod"
        )
    )
    session_type: str = "filesystem"
    session_file_dir: str = ".flask_sessions"
    session_permanent: bool = False
    max_message_length: int = 4000
    max_tokens: int = 4096
    enable_prompt_enhancement: bool = True  # Enable automatic prompt improvement

    # Infiltration Mode Settings
    enable_infiltration_mode: bool = False  # Disable by default for security
    infiltration_auto_block: bool = True  # Auto-block detected attacks by default
    infiltration_log_file: str = (
        "infiltration_log.json"  # Log file for detected attacks
    )

    bedrock: BedrockConfig = field(default_factory=BedrockConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    classifier: ClassifierConfig = field(default_factory=ClassifierConfig)


# Global config instance
config = AppConfig()
