"""Simple test to debug web search issues."""
from dotenv import load_dotenv
load_dotenv()

import os
print(f"API Key loaded: {os.getenv('SERPER_API_KEY', 'NOT FOUND')[:15]}...")

from services.websearch import web_search

print("\nTesting web search...")
try:
    result = web_search("latest silver price India", max_results=2)
    if result:
        print("\n✅ SUCCESS!")
        print(result)
    else:
        print("\n❌ FAILED - Empty result returned")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
