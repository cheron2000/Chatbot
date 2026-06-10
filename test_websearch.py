"""Test script for web search functionality."""
import os
from dotenv import load_dotenv
from services.websearch import web_search

# Load environment variables
load_dotenv()

def test_api_key():
    """Check if API key is configured."""
    api_key = os.environ.get("SERPER_API_KEY", "")
    
    if not api_key:
        print("❌ SERPER_API_KEY not found in .env file")
        print("📝 Please add your API key to .env file:")
        print("   SERPER_API_KEY=your_api_key_here")
        return False
    
    if api_key == "your_serper_api_key_here":
        print("❌ SERPER_API_KEY is still set to default value")
        print("📝 Please replace with your actual API key from:")
        print("   https://serper.dev/dashboard")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    return True

def test_search():
    """Test a simple web search."""
    if not test_api_key():
        return
    
    print("\n🔍 Testing web search with query: 'Python 3.12 features'")
    print("─" * 60)
    
    results = web_search("Python 3.12 features", max_results=2)
    
    if results:
        print("✅ Search successful!\n")
        print(results)
        print("─" * 60)
        print("✅ Web search is working correctly!")
    else:
        print("❌ Search failed - check console logs above for details")
        print("📝 Common issues:")
        print("   1. Invalid API key - verify at https://serper.dev/dashboard")
        print("   2. Network connectivity issue")
        print("   3. API rate limit exceeded")

if __name__ == "__main__":
    print("=" * 60)
    print("Web Search Test Script")
    print("=" * 60)
    test_search()
