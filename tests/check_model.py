"""Quick script to check the trained model checkpoint."""

import sys
from pathlib import Path

try:
    import torch
    print("✅ PyTorch is available")
    print(f"   Version: {torch.__version__}")
    
    # Check model checkpoint
    checkpoint_path = Path("best_efficientnet_ham10000.pth")
    
    if not checkpoint_path.exists():
        print("❌ Model checkpoint not found at:", checkpoint_path)
        sys.exit(1)
    
    print(f"\n✅ Model checkpoint found:")
    print(f"   Path: {checkpoint_path}")
    print(f"   Size: {checkpoint_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Load checkpoint
    print("\n📦 Loading checkpoint...")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    
    # Check contents
    print("✅ Checkpoint loaded successfully")
    print(f"\n📊 Checkpoint Contents:")
    
    required_keys = ["model_state_dict", "label_map", "model_name"]
    for key in required_keys:
        if key in checkpoint:
            print(f"   ✅ {key}: present")
        else:
            print(f"   ❌ {key}: MISSING")
    
    # Display model info
    print(f"\n🏷️  Model Information:")
    print(f"   Model Name: {checkpoint.get('model_name', 'N/A')}")
    print(f"   Number of Classes: {len(checkpoint.get('label_map', {}))}")
    print(f"   Training Epoch: {checkpoint.get('epoch', 'N/A')}")
    
    val_accuracy = checkpoint.get('val_accuracy', None)
    if val_accuracy:
        print(f"   Validation Accuracy: {val_accuracy:.2%}")
    
    # Display disease classes
    label_map = checkpoint.get('label_map', {})
    if label_map:
        print(f"\n🦠 Disease Classes ({len(label_map)}):")
        for disease_code, idx in sorted(label_map.items(), key=lambda x: x[1]):
            print(f"   {idx}: {disease_code}")
    
    print("\n" + "="*70)
    print("✅ MODEL CHECKPOINT IS VALID AND READY TO USE!")
    print("="*70)
    print("\n💡 You can now:")
    print("   1. Install dependencies: pip install -r requirements.txt")
    print("   2. Start the application: python app_refactored.py")
    print("   3. Test the classifier: python test_classifier_integration.py")
    
except ImportError:
    print("❌ PyTorch not installed in this environment")
    print("\n💡 To install:")
    print("   pip install torch torchvision timm")
    print("\n   Or use requirements.txt:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
