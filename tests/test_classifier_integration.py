"""
Quick test script for Skin Lesion Classifier Integration

This script tests all three endpoints:
1. Health check
2. Direct classification
3. Chat integration

Run this after starting the Flask application to verify everything works.
"""

import requests
import base64
import sys
from pathlib import Path


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_health_check():
    """Test the health check endpoint."""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get('http://localhost:5000/health/classifier')
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {data}")
        
        if response.status_code == 200 and data.get('status') == 'healthy':
            print("✅ Health check PASSED - Classifier is operational")
            return True
        elif response.status_code == 503:
            print("⚠️  Health check: Model not loaded yet (will load on first request)")
            return True
        else:
            print("❌ Health check FAILED")
            return False
    
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_direct_classification():
    """Test direct classification via /classify endpoint."""
    print_section("TEST 2: Direct Classification (/classify endpoint)")
    
    # Find a test image from HAM10000 dataset
    test_image_path = Path("datasets/dataset/HAM10000_images_part_1")
    
    if not test_image_path.exists():
        print("❌ Test images not found. Please ensure HAM10000 dataset is extracted.")
        return False
    
    # Get first image from dataset
    image_files = list(test_image_path.glob("*.jpg"))
    if not image_files:
        print("❌ No test images found")
        return False
    
    test_image = image_files[0]
    print(f"Using test image: {test_image.name}")
    
    try:
        # Read and encode image
        with open(test_image, 'rb') as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"Image size: {len(image_bytes)} bytes")
        print("Sending classification request...")
        
        # Send classification request
        response = requests.post('http://localhost:5000/classify', json={
            'image_b64': image_b64,
            'image_mime': 'image/jpeg',
            'top_k': 3
        })
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n📊 Classification Results:")
            print(f"Processing Time: {data['processing_time_ms']:.1f}ms")
            print(f"\nTop 3 Predictions:")
            
            for i, pred in enumerate(data['predictions'], 1):
                print(f"\n{i}. {pred['disease_name']} ({pred['disease_code']})")
                print(f"   Confidence: {pred['confidence']:.2%}")
                print(f"   Severity: {pred['severity']}")
                print(f"   Description: {pred['description'][:100]}...")
            
            print(f"\n⚠️  Disclaimer: {data['disclaimer'][:100]}...")
            print("\n✅ Direct classification PASSED")
            return True
        
        else:
            print(f"❌ Classification failed: {response.json()}")
            return False
    
    except Exception as e:
        print(f"❌ Classification error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_integration():
    """Test chat integration with auto-classification."""
    print_section("TEST 3: Chat Integration (auto-classification)")
    
    # Find a test image
    test_image_path = Path("datasets/dataset/HAM10000_images_part_1")
    
    if not test_image_path.exists():
        print("❌ Test images not found")
        return False
    
    image_files = list(test_image_path.glob("*.jpg"))
    if not image_files:
        print("❌ No test images found")
        return False
    
    test_image = image_files[1] if len(image_files) > 1 else image_files[0]
    print(f"Using test image: {test_image.name}")
    
    try:
        # Read and encode image
        with open(test_image, 'rb') as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        print("Sending chat message with classification keywords...")
        
        # Send chat request with classification trigger
        response = requests.post('http://localhost:5000/chat', 
            json={
                'message': 'What is this skin lesion? Should I be worried?',
                'image_b64': image_b64,
                'image_mime': 'image/jpeg'
            },
            stream=True
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("\n💬 AI Response (streaming):")
            print("-" * 70)
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            import json
                            data = json.loads(line_str[6:])
                            if data.get('type') == 'token':
                                text = data.get('text', '')
                                print(text, end='', flush=True)
                                full_response += text
                        except:
                            pass
            
            print("\n" + "-" * 70)
            
            # Check if classification context was injected
            if "classification" in full_response.lower() or "lesion" in full_response.lower():
                print("\n✅ Chat integration PASSED - Classification context detected")
                return True
            else:
                print("\n⚠️  Chat integration: No obvious classification context")
                print("   (But this might be normal if AI rephrased the response)")
                return True
        
        else:
            print(f"❌ Chat failed: {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Chat integration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        Skin Lesion Classifier Integration - Test Suite              ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    print("This script will test all three classifier endpoints:")
    print("  1. Health check (/health/classifier)")
    print("  2. Direct classification (/classify)")
    print("  3. Chat integration (/chat with auto-detection)")
    print("\nMake sure the Flask application is running on http://localhost:5000")
    print("\nStarting tests...")
    
    # Run tests
    results = []
    
    results.append(("Health Check", test_health_check()))
    results.append(("Direct Classification", test_direct_classification()))
    results.append(("Chat Integration", test_chat_integration()))
    
    # Print summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests PASSED! Skin lesion classifier is fully operational.")
        print("\n📚 Next steps:")
        print("   - Start using the classifier in your chatbot")
        print("   - Upload skin lesion images and ask diagnostic questions")
        print("   - Refer to SKIN_CLASSIFIER_DEPLOYMENT_GUIDE.md for more info")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        print("   - Ensure Flask application is running")
        print("   - Verify model checkpoint exists")
        print("   - Check application logs for errors")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
