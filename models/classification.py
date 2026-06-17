"""
Data models for skin lesion classification.

This module defines the data structures used for classification results,
predictions, model information, and disease information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any


@dataclass
class Prediction:
    """Single disease prediction with confidence score."""
    
    disease_code: str       # Short code: "mel", "bkl", "bcc", etc.
    disease_name: str       # Full name: "Melanoma", "Benign Keratosis"
    confidence: float       # 0.0 to 1.0
    description: str        # Educational description of the condition
    severity: str           # "benign", "pre-cancerous", "malignant"
    prevalence: str         # "common", "uncommon", "rare"
    
    def __post_init__(self):
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "disease_code": self.disease_code,
            "disease_name": self.disease_name,
            "confidence": self.confidence,
            "description": self.description,
            "severity": self.severity,
            "prevalence": self.prevalence
        }


@dataclass
class ModelInfo:
    """Metadata about the classification model."""
    
    name: str               # "efficientnet_b0"
    input_size: int         # 224
    num_classes: int        # 7
    framework: str          # "pytorch"
    library: str            # "timm"
    checkpoint_path: str    # Path to .pth file
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "input_size": self.input_size,
            "num_classes": self.num_classes,
            "framework": self.framework,
            "library": self.library,
            "checkpoint_path": self.checkpoint_path
        }


@dataclass
class ClassificationResult:
    """Result of a skin lesion classification."""
    
    predictions: List[Prediction]  # Top K predictions, sorted by confidence
    processing_time_ms: float      # Inference time in milliseconds
    model_info: ModelInfo           # Model metadata
    timestamp: str                  # ISO 8601 timestamp
    disclaimer: str                 # Medical disclaimer text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "status": "success",
            "predictions": [pred.to_dict() for pred in self.predictions],
            "processing_time_ms": self.processing_time_ms,
            "model_info": self.model_info.to_dict(),
            "timestamp": self.timestamp,
            "disclaimer": self.disclaimer
        }
    
    def get_top_prediction(self) -> Prediction:
        """Get the highest confidence prediction."""
        if not self.predictions:
            raise ValueError("No predictions available")
        return self.predictions[0]


@dataclass
class DiseaseInfo:
    """Detailed information about a skin lesion disease class."""
    
    code: str               # "mel", "bkl", "bcc", "akiec", "df", "nv", "vasc"
    name: str               # Full disease name
    description: str        # Multi-paragraph educational description
    severity: str           # "benign", "pre-cancerous", "malignant"
    prevalence: str         # "common", "uncommon", "rare"
    risk_factors: List[str] = field(default_factory=list)  # List of known risk factors
    treatment: str = ""     # General treatment approach
    prognosis: str = ""     # Expected outcome
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "prevalence": self.prevalence,
            "risk_factors": self.risk_factors,
            "treatment": self.treatment,
            "prognosis": self.prognosis
        }
