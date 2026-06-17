"""
Test script for the trained EfficientNet model.
Run this after training completes to verify the model works correctly.
"""

import torch
import timm
from pathlib import Path
from PIL import Image
from torchvision import transforms


def test_model_checkpoint():
    """Test that the model checkpoint exists and can be loaded."""
    print("=" * 70)
    print("EFFICIENTNET MODEL TEST")
    print("=" * 70)
    
    # Check if checkpoint exists
    checkpoint_path = Path("best_efficientnet_ham10000.pth")
    if not checkpoint_path.exists():
        print("❌ FAILED: Model checkpoint not found at", checkpoint_path)
        print("   Training may still be in progress or hasn't started yet.")
        return False
    
    print("✅ Checkpoint file found:", checkpoint_path)
    print(f"   Size: {checkpoint_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Load checkpoint
    try:
        print("\n📦 Loading checkpoint...")
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        print("✅ Checkpoint loaded successfully")
    except Exception as e:
        print(f"❌ FAILED: Could not load checkpoint: {e}")
        return False
    
    # Verify checkpoint contents
    required_keys = ["model_state_dict", "label_map", "model_name"]
    print("\n🔍 Verifying checkpoint contents...")
    for key in required_keys:
        if key in checkpoint:
            print(f"✅ {key}: present")
        else:
            print(f"❌ {key}: MISSING")
            return False
    
    # Display model info
    model_name = checkpoint["model_name"]
    label_map = checkpoint["label_map"]
    num_classes = len(label_map)
    val_accuracy = checkpoint.get("val_accuracy", "N/A")
    epoch = checkpoint.get("epoch", "N/A")
    
    print(f"\n📊 Model Information:")
    print(f"   Model Name: {model_name}")
    print(f"   Number of Classes: {num_classes}")
    print(f"   Training Epoch: {epoch}")
    print(f"   Validation Accuracy: {val_accuracy:.2%}" if isinstance(val_accuracy, float) else f"   Validation Accuracy: {val_accuracy}")
    
    print(f"\n🏷️  Disease Classes ({num_classes}):")
    for disease_code, idx in sorted(label_map.items(), key=lambda x: x[1]):
        print(f"   {idx}: {disease_code}")
    
    # Create model architecture
    print(f"\n🏗️  Creating model architecture...")
    try:
        model = timm.create_model(model_name, pretrained=False, num_classes=num_classes)
        print("✅ Model architecture created")
    except Exception as e:
        print(f"❌ FAILED: Could not create model: {e}")
        return False
    
    # Load weights
    print("\n⚖️  Loading trained weights...")
    try:
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        print("✅ Weights loaded successfully")
    except Exception as e:
        print(f"❌ FAILED: Could not load weights: {e}")
        return False
    
    # Test inference with dummy data
    print("\n🧪 Testing inference with dummy image...")
    try:
        # Create dummy 224x224 RGB image
        dummy_input = torch.randn(1, 3, 224, 224)
        
        with torch.no_grad():
            output = model(dummy_input)
        
        print(f"✅ Inference successful")
        print(f"   Output shape: {output.shape}")
        print(f"   Expected shape: (1, {num_classes})")
        
        if output.shape != (1, num_classes):
            print(f"❌ WARNING: Output shape mismatch!")
            return False
        
        # Test softmax
        probs = torch.softmax(output, dim=1)
        print(f"\n📈 Probability Distribution:")
        print(f"   Min: {probs.min().item():.4f}")
        print(f"   Max: {probs.max().item():.4f}")
        print(f"   Sum: {probs.sum().item():.4f} (should be ~1.0)")
        
        # Get top prediction
        top_prob, top_idx = torch.max(probs, dim=1)
        reverse_label_map = {v: k for k, v in label_map.items()}
        top_disease = reverse_label_map[top_idx.item()]
        
        print(f"\n🎯 Top Prediction (dummy data):")
        print(f"   Disease: {top_disease}")
        print(f"   Confidence: {top_prob.item():.2%}")
        
    except Exception as e:
        print(f"❌ FAILED: Inference error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\n💡 The model is ready for integration with the chatbot.")
    print("   You can now proceed with implementing the SkinClassifierService.")
    
    return True


def test_with_real_image(image_path: str):
    """Test model with a real image."""
    print("\n" + "=" * 70)
    print("TESTING WITH REAL IMAGE")
    print("=" * 70)
    
    # Load checkpoint
    checkpoint_path = Path("best_efficientnet_ham10000.pth")
    if not checkpoint_path.exists():
        print("❌ Model checkpoint not found")
        return
    
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    model_name = checkpoint["model_name"]
    label_map = checkpoint["label_map"]
    num_classes = len(label_map)
    
    # Create and load model
    model = timm.create_model(model_name, pretrained=False, num_classes=num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    
    # Load and preprocess image
    print(f"\n📷 Loading image: {image_path}")
    try:
        image = Image.open(image_path).convert("RGB")
        print(f"   Original size: {image.size}")
    except Exception as e:
        print(f"❌ Could not load image: {e}")
        return
    
    # Preprocessing
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    image_tensor = transform(image).unsqueeze(0)
    print(f"   Preprocessed shape: {image_tensor.shape}")
    
    # Run inference
    print(f"\n🔮 Running inference...")
    with torch.no_grad():
        output = model(image_tensor)
        probs = torch.softmax(output, dim=1)
    
    # Get top 3 predictions
    top_probs, top_indices = torch.topk(probs, k=min(3, num_classes), dim=1)
    reverse_label_map = {v: k for k, v in label_map.items()}
    
    print(f"\n🎯 Top 3 Predictions:")
    for i, (prob, idx) in enumerate(zip(top_probs[0], top_indices[0]), 1):
        disease_code = reverse_label_map[idx.item()]
        print(f"   {i}. {disease_code}: {prob.item():.2%}")
    
    print("\n✅ Real image test completed!")


if __name__ == "__main__":
    import sys
    
    # Test checkpoint and model loading
    success = test_model_checkpoint()
    
    # If a test image path is provided, test with real image
    if len(sys.argv) > 1 and success:
        test_with_real_image(sys.argv[1])
    elif success:
        print("\n💡 To test with a real image, run:")
        print(f"   python {sys.argv[0]} <path_to_image.jpg>")
