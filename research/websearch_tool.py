"""
Integration test for web_search_tool with real Brave API
Run this only if you have a valid BRAVE_API_KEY in your .env file
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Import your actual function (adjust the import path as needed)
# from your_module.search import web_search_tool

# For this test, we'll redefine it
from html.parser import HTMLParser
import requests
from typing import List, Dict

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_html(html: str) -> str:
    s = HTMLStripper()
    s.feed(html)
    return s.get_data()


BRAVE_API_KEY="BSAxM8-IgA7TtoIKZ0QQLJ-lHzAqTX1"

def web_search_tool(tags: str) -> List[Dict]:
    
    if not BRAVE_API_KEY:
        return [{"error": "Brave API key not provided"}]

    tag_list = [tag.strip() for tag in tags.split(",")]
    query = " OR ".join(tag_list[:3])

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "x-subscription-token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": 5,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])
    except requests.exceptions.RequestException as e:
        return [{"error": f"HTTP Request failed: {str(e)}"}]

    formatted_results = []
    for item in results:
        content = item.get("description", "")
        clean_content = strip_html(content)
        formatted_results.append({
            "title": item.get("title", ""),
            "date": item.get("published", ""),
            "tags": tags,
            "content": clean_content,
            "website": item.get("url", "")
        })

    return formatted_results


def test_real_api():
    """Test with real Brave API"""
    print("Testing with real Brave API...")
    print("=" * 60)
    
    # Check if API key exists
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        print("⚠ BRAVE_API_KEY not found in environment")
        print("Please set it in your .env file to run this test")
        return
    
    # Test 1: Single tag search
    print("\n[Test 1] Searching for: 'python'")
    results = web_search_tool("python")
    
    if results and "error" in results[0]:
        print(f"✗ Error: {results[0]['error']}")
        return
    
    print(f"✓ Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Title: {result['title'][:80]}...")
        print(f"    Date: {result['date']}")
        print(f"    Content: {result['content'][:100]}...")
        print(f"    URL: {result['website'][:60]}...")
    
    # Test 2: Multiple tags
    print("\n" + "=" * 60)
    print("[Test 2] Searching for: 'artificial intelligence, machine learning'")
    results = web_search_tool("artificial intelligence, machine learning")
    
    if results and "error" in results[0]:
        print(f"✗ Error: {results[0]['error']}")
        return
    
    print(f"✓ Found {len(results)} results")
    for i, result in enumerate(results[:2], 1):  # Show only first 2
        print(f"\n  Result {i}:")
        print(f"    Title: {result['title'][:80]}")
        print(f"    Tags: {result['tags']}")
        print(f"    Content length: {len(result['content'])} chars")
    
    # Test 3: Check content quality (should have at least some content)
    print("\n" + "=" * 60)
    print("[Test 3] Validating content quality...")
    
    has_content = sum(1 for r in results if len(r.get('content', '')) > 50)
    print(f"✓ {has_content}/{len(results)} results have substantial content (>50 chars)")
    
    has_dates = sum(1 for r in results if r.get('date'))
    print(f"✓ {has_dates}/{len(results)} results have publication dates")
    
    has_urls = sum(1 for r in results if r.get('website'))
    print(f"✓ {has_urls}/{len(results)} results have URLs")
    
    print("\n" + "=" * 60)
    print("✓ Integration test completed!")


if __name__ == "__main__":
    test_real_api()