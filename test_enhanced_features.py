"""Test script for enhanced features."""

import asyncio
import logging
from content_extractor import ContentExtractor, extract_content_sync
from openrouter_client import OpenRouterClient, generate_description_sync
from config import DEFAULT_MODEL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_content_extraction():
    """Test content extraction without Puppeteer."""
    print("Testing content extraction...")
    
    test_url = "https://example.com"
    
    try:
        title, meta_desc, main_content = extract_content_sync(test_url, use_puppeteer=False)
        
        print(f"URL: {test_url}")
        print(f"Title: {title}")
        print(f"Meta Description: {meta_desc}")
        print(f"Main Content Length: {len(main_content)} characters")
        print(f"Main Content Preview: {main_content[:200]}...")
        print("✅ Content extraction test passed!")
        
    except Exception as e:
        print(f"❌ Content extraction test failed: {str(e)}")

def test_openrouter_client():
    """Test OpenRouter client (without actual API call)."""
    print("\nTesting OpenRouter client...")
    
    try:
        client = OpenRouterClient()
        
        # Test configuration check
        is_configured = client.is_configured()
        print(f"Client configured: {is_configured}")
        
        # Test prompt creation
        test_content = "This is a test page about Python programming."
        test_title = "Python Programming Guide"
        test_url = "https://example.com/python-guide"
        
        prompt = client._create_description_prompt(test_content, test_title, test_url)
        print(f"Generated prompt length: {len(prompt)} characters")
        print("✅ OpenRouter client test passed!")
        
    except Exception as e:
        print(f"❌ OpenRouter client test failed: {str(e)}")

def test_enhanced_workflow():
    """Test the complete enhanced workflow."""
    print("\nTesting enhanced workflow...")
    
    test_url = "https://httpbin.org/html"  # Simple HTML test page
    
    try:
        # Test without LLM
        title1, desc1, content1 = extract_content_sync(test_url, use_puppeteer=False)
        print(f"Without LLM - Title: {title1}")
        print(f"Without LLM - Description: {desc1}")
        
        # Test with mock LLM (no API key)
        mock_description = generate_description_sync(
            content=content1,
            title=title1,
            url=test_url,
            model=DEFAULT_MODEL,
            api_key=None  # No API key for testing
        )
        
        if mock_description is None:
            print("✅ LLM integration correctly handles missing API key")
        else:
            print(f"LLM Description: {mock_description}")
        
        print("✅ Enhanced workflow test passed!")
        
    except Exception as e:
        print(f"❌ Enhanced workflow test failed: {str(e)}")

def main():
    """Run all tests."""
    print("🧪 Testing Enhanced LLMS.txt Generator Features")
    print("=" * 50)
    
    test_content_extraction()
    test_openrouter_client()
    test_enhanced_workflow()
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")
    print("\nTo test with real API:")
    print("1. Get an OpenRouter API key from https://openrouter.ai/keys")
    print("2. Set OPENROUTER_API_KEY environment variable")
    print("3. Run the Streamlit app: streamlit run app.py")

if __name__ == "__main__":
    main()
