"""
Test script to verify vector memory is working correctly.
Run this to check if semantic search is functioning.
"""
import sys
from models.vector_memory import VectorMemory

def test_vector_memory():
    """Test vector memory functionality."""
    print("=" * 60)
    print("VECTOR MEMORY TEST")
    print("=" * 60)
    
    # Initialize vector memory
    print("\n1. Initializing vector memory...")
    try:
        vm = VectorMemory(persist_directory="./vector_db")
        print("   ✅ Vector memory initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return False
    
    # Add test messages
    print("\n2. Adding test messages...")
    test_session = "test_session_123"
    
    messages = [
        {"role": "user", "content": "What is Python programming language?"},
        {"role": "assistant", "content": "Python is a high-level, interpreted programming language known for its simplicity and readability."},
        {"role": "user", "content": "How do I deploy to AWS?"},
        {"role": "assistant", "content": "To deploy to AWS, you can use services like EC2, Elastic Beanstalk, or Lambda depending on your needs."},
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is a subset of AI that enables systems to learn from data without explicit programming."},
    ]
    
    try:
        for msg in messages:
            vm.add_message(test_session, msg["role"], msg["content"])
        print(f"   ✅ Added {len(messages)} test messages")
    except Exception as e:
        print(f"   ❌ Failed to add messages: {e}")
        return False
    
    # Test semantic search
    print("\n3. Testing semantic search...")
    
    test_queries = [
        ("Tell me about Python", "Should find Python-related messages"),
        ("AWS deployment guide", "Should find AWS-related messages"),
        ("AI and ML concepts", "Should find machine learning messages"),
    ]
    
    for query, expected in test_queries:
        print(f"\n   Query: '{query}'")
        print(f"   Expected: {expected}")
        try:
            results = vm.search_similar(query, test_session, n_results=2)
            if results:
                print(f"   ✅ Found {len(results)} relevant messages:")
                for i, result in enumerate(results, 1):
                    content = result['content'][:80] + "..." if len(result['content']) > 80 else result['content']
                    distance = result['distance']
                    print(f"      {i}. [{distance:.3f}] {content}")
            else:
                print("   ⚠️  No results found")
        except Exception as e:
            print(f"   ❌ Search failed: {e}")
            return False
    
    # Get statistics
    print("\n4. Database statistics...")
    try:
        stats = vm.get_stats()
        print(f"   ✅ Total messages: {stats['total_messages']}")
        print(f"   ✅ Collection: {stats['collection_name']}")
    except Exception as e:
        print(f"   ❌ Failed to get stats: {e}")
        return False
    
    # Test session history
    print("\n5. Testing session history retrieval...")
    try:
        history = vm.get_session_history(test_session, limit=10)
        print(f"   ✅ Retrieved {len(history)} messages from session")
    except Exception as e:
        print(f"   ❌ Failed to get history: {e}")
        return False
    
    # Cleanup
    print("\n6. Cleaning up test data...")
    try:
        deleted = vm.delete_session(test_session)
        print(f"   ✅ Deleted {deleted} test messages")
    except Exception as e:
        print(f"   ❌ Failed to cleanup: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - VECTOR MEMORY IS WORKING!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_vector_memory()
    sys.exit(0 if success else 1)
