"""Web search integration for fetching current information."""
import httpx
import os
import time
from typing import Optional


def web_search(query: str, max_results: int = 5, max_retries: int = 2) -> str:
    """
    Perform web search using Serper.dev API and return formatted results.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (increased to 5 for better coverage)
        max_retries: Maximum number of retry attempts
        
    Returns:
        Formatted string with search results, or empty string if search fails
    """
    # Get API key from environment
    api_key = os.environ.get("SERPER_API_KEY", "")
    
    if not api_key or api_key == "your_serper_api_key_here":
        print(f"[SEARCH] Error: SERPER_API_KEY not configured in .env file")
        print(f"[SEARCH] Get your API key from: https://serper.dev/dashboard")
        return ""
    
    # Retry loop
    for attempt in range(max_retries):
        try:
            # Using Serper.dev Google Search API
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": max_results,
                "gl": "us",  # Geographic location
                "hl": "en"   # Language
            }
            
            # Use longer timeout and enable keep-alive
            with httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0), http2=True) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code == 401:
                    print(f"[SEARCH] Error: Invalid SERPER_API_KEY")
                    print(f"[SEARCH] Check your API key at: https://serper.dev/dashboard")
                    return ""
                
                if response.status_code == 429:
                    print(f"[SEARCH] Rate limit exceeded. Waiting before retry...")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    return ""
                
                if response.status_code != 200:
                    print(f"[SEARCH] Failed with status {response.status_code}")
                    print(f"[SEARCH] Response: {response.text[:200]}")
                    if attempt < max_retries - 1:
                        print(f"[SEARCH] Retrying... (attempt {attempt + 2}/{max_retries})")
                        time.sleep(1)
                        continue
                    return ""
                
                # Parse JSON response
                data = response.json()
                
                # Extract organic results
                organic = data.get("organic", [])
                
                if not organic:
                    print(f"[SEARCH] No results found for: {query}")
                    return ""
                
                # Format results with enhanced structure
                formatted = "═══════════════════════════════════════════════════════\n"
                formatted += "🌐 LIVE WEB SEARCH RESULTS (CURRENT INFORMATION)\n"
                formatted += "═══════════════════════════════════════════════════════\n"
                formatted += f"Query: {query}\n"
                formatted += f"Results: {len(organic)} sources found\n"
                formatted += "═══════════════════════════════════════════════════════\n\n"
                
                for i, result in enumerate(organic[:max_results], 1):
                    title = result.get("title", "No title")
                    snippet = result.get("snippet", "No description")
                    link = result.get("link", "")
                    date = result.get("date", "")
                    
                    formatted += f"【Result #{i}】\n"
                    formatted += f"Title: {title}\n"
                    if date:
                        formatted += f"Published: {date}\n"
                    formatted += f"Content: {snippet}\n"
                    formatted += f"Source: {link}\n"
                    formatted += "─" * 50 + "\n\n"
                
                formatted += "═══════════════════════════════════════════════════════\n"
                formatted += "⚠️ IMPORTANT: Use ONLY the information above to answer.\n"
                formatted += "DO NOT use your training data for facts covered here.\n"
                formatted += "ALWAYS cite the source URLs in your response.\n"
                formatted += "═══════════════════════════════════════════════════════\n"
                
                print(f"[SEARCH] ✅ Found {len(organic)} results for: {query[:50]}...")
                return formatted
                
        except httpx.RemoteProtocolError as e:
            print(f"[SEARCH] Server disconnected: {e}")
            if attempt < max_retries - 1:
                print(f"[SEARCH] Retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(1)
                continue
            return ""
        except httpx.TimeoutException:
            print(f"[SEARCH] Timeout while searching for: {query}")
            if attempt < max_retries - 1:
                print(f"[SEARCH] Retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(1)
                continue
            return ""
        except Exception as e:
            print(f"[SEARCH] Error: {e}")
            if attempt < max_retries - 1:
                print(f"[SEARCH] Retrying... (attempt {attempt + 2}/{max_retries})")
                time.sleep(1)
                continue
            return ""
    
    # All retries exhausted
    print(f"[SEARCH] ❌ Failed after {max_retries} attempts")
    return ""


def search_with_fallback(query: str) -> str:
    """
    Try web search with fallback to empty string.
    
    This is a safe wrapper that never raises exceptions.
    """
    try:
        return web_search(query)
    except Exception as e:
        print(f"[SEARCH] Fallback triggered: {e}")
        return ""
