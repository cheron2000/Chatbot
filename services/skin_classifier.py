"""
Skin lesion classification service using EfficientNet.

This service provides a singleton interface for loading and using the trained
EfficientNet model for skin lesion classification.
"""

import json
import os
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import timm
from PIL import Image
from torchvision import transforms

from models.classification import (
    ClassificationResult,
    DiseaseInfo,
    ModelInfo,
    Prediction
)


# Medical disclaimer constant
MEDICAL_DISCLAIMER = """
⚠️ IMPORTANT MEDICAL DISCLAIMER ⚠️

This AI classification is for educational purposes only and should NOT be used as 
a substitute for professional medical advice, diagnosis, or treatment.

Always consult a qualified dermatologist or healthcare provider for any concerns 
about skin lesions. Early detection and professional evaluation are crucial for 
proper diagnosis and treatment.

This tool is not FDA-approved and should not be used to make medical decisions.
"""


class SkinClassifierService:
    """Singleton service for skin lesion classification using EfficientNet."""
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _device = None
    _label_map = None
    _index_to_label = None
    _disease_info_cache = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_path: str = "best_efficientnet_ham10000.pth", device: str = "auto"):
        """
        Initialize the classifier service.
        
        Args:
            model_path: Path to the trained model checkpoint (.pth file)
            device: Computing device ("cpu", "cuda", or "auto")
        """
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
        
        self.model_path = Path(model_path)
        self.device_str = device
        self._model_name = None
        self._num_classes = None
        self._initialized = True
    
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded in memory."""
        return self._model is not None
    
    def load_model(self) -> None:
        """
        Load the EfficientNet model and label map from checkpoint.
        Uses lazy loading - only loads when first needed.
        Thread-safe for concurrent requests.
        
        Raises:
            FileNotFoundError: If model checkpoint doesn't exist
            RuntimeError: If model loading fails
        """
        # Double-check locking pattern for thread safety
        if self._model is not None:
            return
        
        with self._lock:
            # Check again after acquiring lock
            if self._model is not None:
                return
            
            print(f"[CLASSIFIER] Loading model from {self.model_path}")
            
            # Validate checkpoint exists
            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Model checkpoint not found at {self.model_path}. "
                    f"Please ensure training has completed and the checkpoint exists."
                )
            
            # Determine device
            if self.device_str == "auto":
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            else:
                self._device = torch.device(self.device_str)
            
            print(f"[CLASSIFIER] Using device: {self._device}")
            
            # Load checkpoint
            try:
                checkpoint = torch.load(self.model_path, map_location=self._device)
            except Exception as e:
                raise RuntimeError(f"Failed to load checkpoint: {e}")
            
            # Validate checkpoint contents
            required_keys = ["model_state_dict", "label_map", "model_name"]
            for key in required_keys:
                if key not in checkpoint:
                    raise RuntimeError(f"Checkpoint missing required key: {key}")
            
            # Extract metadata
            self._label_map = checkpoint["label_map"]
            self._model_name = checkpoint["model_name"]
            self._num_classes = len(self._label_map)
            
            if self._num_classes != 7:
                raise RuntimeError(
                    f"Expected 7 disease classes, got {self._num_classes}"
                )
            
            print(f"[CLASSIFIER] Model: {self._model_name}, Classes: {self._num_classes}")
            
            # Create model architecture
            try:
                self._model = timm.create_model(
                    self._model_name,
                    pretrained=False,
                    num_classes=self._num_classes
                )
            except Exception as e:
                raise RuntimeError(f"Failed to create model architecture: {e}")
            
            # Load trained weights
            try:
                self._model.load_state_dict(checkpoint["model_state_dict"])
                self._model.to(self._device)
                self._model.eval()
            except Exception as e:
                raise RuntimeError(f"Failed to load model weights: {e}")
            
            # Create reverse mapping (index -> label)
            self._index_to_label = {idx: label for label, idx in self._label_map.items()}
            
            print(f"[CLASSIFIER] Model loaded successfully")
    
    def _preprocess_image(self, image_bytes: bytes) -> torch.Tensor:
        """
        Preprocess image bytes into a normalized tensor ready for model inference.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
        
        Returns:
            Preprocessed tensor with shape (1, 3, 224, 224)
        
        Raises:
            ValueError: If image is invalid or too small
        """
        try:
            # Step 1: Decode image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Step 2: Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Step 3: Validate image dimensions
            if image.width < 50 or image.height < 50:
                raise ValueError(
                    f"Image too small. Minimum dimensions: 50x50 pixels. "
                    f"Got: {image.width}x{image.height}"
                )
            
            # Step 4: Define preprocessing transforms
            # Using ImageNet normalization statistics
            preprocess = transforms.Compose([
                transforms.Resize((224, 224)),  # Resize to model input size
                transforms.ToTensor(),          # Convert to tensor [0, 1]
                transforms.Normalize(           # Normalize using ImageNet stats
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            # Step 5: Apply transforms
            tensor = preprocess(image)
            
            # Step 6: Add batch dimension (1, 3, 224, 224)
            tensor = tensor.unsqueeze(0)
            
            return tensor
            
        except IOError as e:
            raise ValueError(f"Invalid image format. Could not decode image: {e}")
        except Exception as e:
            raise ValueError(f"Error preprocessing image: {e}")
    
    def classify_image(
        self,
        image_bytes: bytes,
        top_k: int = 3
    ) -> ClassificationResult:
        """
        Classify a skin lesion image.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            top_k: Number of top predictions to return (default: 3)
        
        Returns:
            ClassificationResult with predictions and metadata
        
        Raises:
            ValueError: If image is invalid or cannot be processed
            RuntimeError: If model inference fails
        """
        # Validate top_k parameter
        if not 1 <= top_k <= 7:
            raise ValueError(f"top_k must be between 1 and 7, got {top_k}")
        
        # Ensure model is loaded
        if not self.is_loaded():
            self.load_model()
        
        # Record start time
        start_time = time.time()
        
        try:
            # Step 1: Preprocess image
            image_tensor = self._preprocess_image(image_bytes)
            image_tensor = image_tensor.to(self._device)
            
            # Step 2: Run inference
            with torch.no_grad():
                logits = self._model(image_tensor)
                probabilities = torch.softmax(logits, dim=1)
            
            # Step 3: Get top-K predictions
            top_probs, top_indices = torch.topk(probabilities, k=top_k, dim=1)
            
            # Step 4: Build predictions list
            predictions = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                prob_value = prob.item()
                idx_value = idx.item()
                
                # Map index to disease code
                disease_code = self._index_to_label[idx_value]
                
                # Get disease information
                disease_info = self.get_disease_info(disease_code)
                
                # Create prediction object
                prediction = Prediction(
                    disease_code=disease_code,
                    disease_name=disease_info.name,
                    confidence=prob_value,
                    description=disease_info.description,
                    severity=disease_info.severity,
                    prevalence=disease_info.prevalence
                )
                
                predictions.append(prediction)
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Step 5: Build result
            result = ClassificationResult(
                predictions=predictions,
                processing_time_ms=processing_time_ms,
                model_info=ModelInfo(
                    name=self._model_name,
                    input_size=224,
                    num_classes=self._num_classes,
                    framework="pytorch",
                    library="timm",
                    checkpoint_path=str(self.model_path)
                ),
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                disclaimer=MEDICAL_DISCLAIMER
            )
            
            return result
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            raise RuntimeError(f"Model inference failed: {e}")
    
    def get_disease_info(self, disease_code: str) -> DiseaseInfo:
        """
        Get detailed information about a disease class.
        
        Args:
            disease_code: Disease code (e.g., "mel", "bkl", "bcc")
        
        Returns:
            DiseaseInfo object with description and details
        
        Raises:
            ValueError: If disease code is invalid
        """
        # Load disease info from JSON file (cached)
        if self._disease_info_cache is None:
            disease_json_path = Path(__file__).parent.parent / "data" / "diseases.json"
            
            if not disease_json_path.exists():
                raise FileNotFoundError(
                    f"Disease information file not found at {disease_json_path}"
                )
            
            with open(disease_json_path, 'r', encoding='utf-8') as f:
                self._disease_info_cache = json.load(f)
        
        if disease_code not in self._disease_info_cache:
            raise ValueError(
                f"Invalid disease code: {disease_code}. "
                f"Valid codes: {list(self._disease_info_cache.keys())}"
            )
        
        data = self._disease_info_cache[disease_code]
        return DiseaseInfo(**data)
    
    def unload_model(self) -> None:
        """
        Unload the model from memory to free resources.
        Useful for memory management in resource-constrained environments.
        """
        with self._lock:
            if self._model is not None:
                print(f"[CLASSIFIER] Unloading model from memory")
                del self._model
                self._model = None
                
                # Clear CUDA cache if using GPU
                if self._device and self._device.type == "cuda":
                    torch.cuda.empty_cache()
