"""
HAM10000 Model Accuracy Test

This script randomly selects 20-30 images from HAM10000 Part 1 dataset,
compares the model's predictions with ground truth labels from the metadata,
and calculates accuracy metrics.
"""

import random
import pandas as pd
import torch
import timm
from pathlib import Path
from PIL import Image
from torchvision import transforms
from collections import Counter
import time


# Disease name mapping for display
DISEASE_NAMES = {
    'akiec': 'Actinic Keratoses',
    'bcc': 'Basal Cell Carcinoma',
    'bkl': 'Benign Keratosis',
    'df': 'Dermatofibroma',
    'mel': 'Melanoma',
    'nv': 'Melanocytic Nevi',
    'vasc': 'Vascular Lesions'
}


def load_metadata():
    """Load the HAM10000 metadata file."""
    print("📂 Loading metadata...")
    metadata_path = Path("datasets/dataset/HAM10000_metadata.tab")
    
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
    
    # Load tab-separated file
    df = pd.read_csv(metadata_path, sep='\t')
    print(f"✅ Loaded {len(df)} metadata entries")
    return df


def get_available_images():
    """Get list of available images from Part 1."""
    print("\n📁 Scanning for images in Part 1...")
    image_dir = Path("datasets/dataset/HAM10000_images_part_1")
    
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")
    
    images = list(image_dir.glob("*.jpg"))
    print(f"✅ Found {len(images)} images in Part 1")
    return images


def load_model():
    """Load the trained EfficientNet model."""
    print("\n🔧 Loading trained model...")
    checkpoint_path = Path("best_efficientnet_ham10000.pth")
    
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_path}")
    
    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    
    model_name = checkpoint["model_name"]
    label_map = checkpoint["label_map"]
    num_classes = len(label_map)
    
    # Create model
    model = timm.create_model(model_name, pretrained=False, num_classes=num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    
    # Create reverse label map (index -> disease code)
    index_to_label = {idx: label for label, idx in label_map.items()}
    
    print(f"✅ Model loaded: {model_name}")
    print(f"   Classes: {num_classes}")
    print(f"   Device: CPU")
    
    return model, index_to_label


def preprocess_image(image_path):
    """Preprocess image for model inference."""
    # Load image
    image = Image.open(image_path).convert("RGB")
    
    # Define preprocessing
    preprocess = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    # Apply transforms
    tensor = preprocess(image).unsqueeze(0)  # Add batch dimension
    return tensor


def predict_image(model, image_path, index_to_label):
    """Run model prediction on an image."""
    # Preprocess
    image_tensor = preprocess_image(image_path)
    
    # Predict
    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        
        # Get top prediction
        confidence, predicted_idx = torch.max(probabilities, 1)
        predicted_class = index_to_label[predicted_idx.item()]
        confidence_value = confidence.item()
    
    return predicted_class, confidence_value


def run_accuracy_test(num_samples=30):
    """Run the accuracy test on random samples."""
    print("=" * 80)
    print("HAM10000 MODEL ACCURACY TEST")
    print("=" * 80)
    
    # Load metadata and images
    metadata = load_metadata()
    available_images = get_available_images()
    
    # Load model
    model, index_to_label = load_model()
    
    # Randomly select images
    print(f"\n🎲 Randomly selecting {num_samples} images...")
    random.seed(42)  # For reproducibility
    selected_images = random.sample(available_images, min(num_samples, len(available_images)))
    print(f"✅ Selected {len(selected_images)} images")
    
    # Prepare results
    results = []
    correct_predictions = 0
    total_predictions = 0
    inference_times = []
    
    print("\n" + "=" * 80)
    print("RUNNING PREDICTIONS")
    print("=" * 80)
    
    # Process each image
    for idx, image_path in enumerate(selected_images, 1):
        # Get image ID from filename (e.g., ISIC_0024306.jpg -> ISIC_0024306)
        image_id = image_path.stem
        
        # Find ground truth from metadata
        image_metadata = metadata[metadata['image_id'] == image_id]
        
        if image_metadata.empty:
            print(f"\n⚠️  {idx}. {image_id}: No metadata found, skipping...")
            continue
        
        ground_truth = image_metadata.iloc[0]['dx']
        
        # Run prediction
        start_time = time.time()
        predicted_class, confidence = predict_image(model, image_path, index_to_label)
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        inference_times.append(inference_time)
        
        # Check if correct
        is_correct = predicted_class == ground_truth
        if is_correct:
            correct_predictions += 1
        total_predictions += 1
        
        # Store result
        results.append({
            'image_id': image_id,
            'ground_truth': ground_truth,
            'predicted': predicted_class,
            'confidence': confidence,
            'correct': is_correct,
            'inference_time_ms': inference_time
        })
        
        # Print result
        status = "✅ CORRECT" if is_correct else "❌ WRONG"
        print(f"\n{idx}. {image_id}")
        print(f"   Ground Truth:  {ground_truth:6s} ({DISEASE_NAMES[ground_truth]})")
        print(f"   Predicted:     {predicted_class:6s} ({DISEASE_NAMES[predicted_class]})")
        print(f"   Confidence:    {confidence:.2%}")
        print(f"   Inference:     {inference_time:.1f}ms")
        print(f"   Status:        {status}")
    
    # Calculate overall accuracy
    accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
    avg_inference_time = sum(inference_times) / len(inference_times) if inference_times else 0
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 Overall Accuracy: {correct_predictions}/{total_predictions} = {accuracy:.2f}%")
    print(f"⏱️  Average Inference Time: {avg_inference_time:.1f}ms")
    print(f"⏱️  Total Test Time: {sum(inference_times)/1000:.2f}s")
    
    # Show per-class breakdown
    print("\n" + "=" * 80)
    print("PER-CLASS PERFORMANCE")
    print("=" * 80)
    
    # Group results by ground truth class
    class_results = {}
    for result in results:
        gt_class = result['ground_truth']
        if gt_class not in class_results:
            class_results[gt_class] = {'correct': 0, 'total': 0, 'confidences': []}
        
        class_results[gt_class]['total'] += 1
        if result['correct']:
            class_results[gt_class]['correct'] += 1
        class_results[gt_class]['confidences'].append(result['confidence'])
    
    # Print per-class statistics
    print(f"\n{'Class':<10} {'Name':<30} {'Correct':<10} {'Total':<8} {'Accuracy':<12} {'Avg Conf'}")
    print("-" * 80)
    
    for disease_code in sorted(class_results.keys()):
        stats = class_results[disease_code]
        class_accuracy = (stats['correct'] / stats['total'] * 100)
        avg_confidence = sum(stats['confidences']) / len(stats['confidences'])
        
        print(f"{disease_code:<10} {DISEASE_NAMES[disease_code]:<30} "
              f"{stats['correct']:<10} {stats['total']:<8} "
              f"{class_accuracy:>6.2f}%      {avg_confidence:.2%}")
    
    # Show confusion patterns
    print("\n" + "=" * 80)
    print("COMMON MISTAKES")
    print("=" * 80)
    
    mistakes = [r for r in results if not r['correct']]
    if mistakes:
        mistake_patterns = Counter([(r['ground_truth'], r['predicted']) for r in mistakes])
        
        print(f"\nFound {len(mistakes)} incorrect predictions:")
        for (gt, pred), count in mistake_patterns.most_common(5):
            print(f"  • {DISEASE_NAMES[gt]} → {DISEASE_NAMES[pred]}: {count} times")
    else:
        print("\n🎉 No mistakes! Perfect accuracy!")
    
    # Show confidence distribution
    print("\n" + "=" * 80)
    print("CONFIDENCE DISTRIBUTION")
    print("=" * 80)
    
    correct_confidences = [r['confidence'] for r in results if r['correct']]
    incorrect_confidences = [r['confidence'] for r in results if not r['correct']]
    
    if correct_confidences:
        print(f"\n✅ Correct Predictions:")
        print(f"   Average Confidence: {sum(correct_confidences)/len(correct_confidences):.2%}")
        print(f"   Min Confidence: {min(correct_confidences):.2%}")
        print(f"   Max Confidence: {max(correct_confidences):.2%}")
    
    if incorrect_confidences:
        print(f"\n❌ Incorrect Predictions:")
        print(f"   Average Confidence: {sum(incorrect_confidences)/len(incorrect_confidences):.2%}")
        print(f"   Min Confidence: {min(incorrect_confidences):.2%}")
        print(f"   Max Confidence: {max(incorrect_confidences):.2%}")
    
    # Performance rating
    print("\n" + "=" * 80)
    print("PERFORMANCE RATING")
    print("=" * 80)
    
    if accuracy >= 90:
        rating = "🌟 EXCELLENT"
        comment = "Outstanding performance! The model is highly accurate."
    elif accuracy >= 80:
        rating = "✅ VERY GOOD"
        comment = "Great performance! The model is reliable for educational purposes."
    elif accuracy >= 70:
        rating = "👍 GOOD"
        comment = "Good performance. Suitable for preliminary assessments."
    elif accuracy >= 60:
        rating = "⚠️  FAIR"
        comment = "Moderate performance. Use with caution and verify results."
    else:
        rating = "❌ NEEDS IMPROVEMENT"
        comment = "Performance below expectations. Consider retraining."
    
    print(f"\nRating: {rating}")
    print(f"Comment: {comment}")
    
    # Save detailed results
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    # Save to CSV
    results_df = pd.DataFrame(results)
    output_path = "model_accuracy_test_results.csv"
    results_df.to_csv(output_path, index=False)
    print(f"\n✅ Detailed results saved to: {output_path}")
    
    # Create summary report
    summary_path = "model_accuracy_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("HAM10000 MODEL ACCURACY TEST SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Samples: {total_predictions}\n")
        f.write(f"Correct Predictions: {correct_predictions}\n")
        f.write(f"Overall Accuracy: {accuracy:.2f}%\n")
        f.write(f"Average Inference Time: {avg_inference_time:.1f}ms\n\n")
        
        f.write("Per-Class Performance:\n")
        f.write("-" * 80 + "\n")
        for disease_code in sorted(class_results.keys()):
            stats = class_results[disease_code]
            class_accuracy = (stats['correct'] / stats['total'] * 100)
            f.write(f"{DISEASE_NAMES[disease_code]}: {class_accuracy:.2f}% "
                   f"({stats['correct']}/{stats['total']})\n")
        
        f.write(f"\nRating: {rating}\n")
        f.write(f"Comment: {comment}\n")
    
    print(f"✅ Summary report saved to: {summary_path}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE!")
    print("=" * 80)
    
    return accuracy, results


if __name__ == "__main__":
    import sys
    
    # Get number of samples from command line or use default
    num_samples = 2000
    if len(sys.argv) > 1:
        try:
            num_samples = int(sys.argv[1])
            if num_samples < 1:
                print("Error: Number of samples must be at least 1")
                sys.exit(1)
        except ValueError:
            print(f"Error: Invalid number: {sys.argv[1]}")
            sys.exit(1)
    
    try:
        accuracy, results = run_accuracy_test(num_samples)
        
        print(f"\n🎯 Final Accuracy: {accuracy:.2f}%")
        print("\nThank you for testing! 🎉")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure:")
        print("  1. Model checkpoint exists at: best_efficientnet_ham10000.pth")
        print("  2. Metadata file exists at: datasets/dataset/HAM10000_metadata.tab")
        print("  3. Images exist in: datasets/dataset/HAM10000_images_part_1/")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
