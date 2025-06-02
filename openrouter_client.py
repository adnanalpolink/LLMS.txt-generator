"""OpenRouter API client for LLM integration."""

import httpx
import json
import logging
from typing import Optional, Dict, Any
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for interacting with OpenRouter API."""
    
    def __init__(self, api_key: str = None):
        """Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If not provided, uses config default.
        """
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = OPENROUTER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo/llms-txt-generator",
            "X-Title": "LLMS.txt Generator"
        }
    
    async def generate_description(
        self, 
        content: str, 
        title: str = "", 
        url: str = "",
        model: str = DEFAULT_MODEL,
        max_tokens: int = 200
    ) -> Optional[str]:
        """Generate a description for web page content using LLM.
        
        Args:
            content: The main content of the web page
            title: The page title (optional)
            url: The page URL (optional)
            model: The LLM model to use
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated description or None if failed
        """
        if not self.api_key:
            logger.warning("No OpenRouter API key provided")
            return None
            
        if not content.strip():
            logger.warning("Empty content provided for description generation")
            return None
        
        # Create the prompt
        prompt = self._create_description_prompt(content, title, url)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        description = result["choices"][0]["message"]["content"].strip()
                        return description
                    else:
                        logger.error(f"Unexpected response format: {result}")
                        return None
                else:
                    logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            return None
    
    def _create_description_prompt(self, content: str, title: str = "", url: str = "") -> str:
        """Create a prompt for generating page descriptions.
        
        Args:
            content: The main content of the web page
            title: The page title (optional)
            url: The page URL (optional)
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            "Please analyze the following web page content and generate a concise, informative description (1-2 sentences) that summarizes what this page is about.",
            "Focus on the main topic, purpose, and key information covered.",
            "Make the description useful for someone deciding whether to visit this page."
        ]
        
        if title:
            prompt_parts.append(f"\nPage Title: {title}")
        
        if url:
            prompt_parts.append(f"Page URL: {url}")
        
        prompt_parts.extend([
            f"\nPage Content:\n{content[:6000]}",  # Limit content to avoid token limits
            "\nGenerate a description:"
        ])
        
        return "\n".join(prompt_parts)
    
    def is_configured(self) -> bool:
        """Check if the client is properly configured with an API key.
        
        Returns:
            True if API key is available, False otherwise
        """
        return bool(self.api_key and self.api_key.strip())


# Synchronous wrapper for easier integration
def generate_description_sync(
    content: str, 
    title: str = "", 
    url: str = "",
    model: str = DEFAULT_MODEL,
    api_key: str = None
) -> Optional[str]:
    """Synchronous wrapper for generating descriptions.
    
    Args:
        content: The main content of the web page
        title: The page title (optional)
        url: The page URL (optional)
        model: The LLM model to use
        api_key: OpenRouter API key (optional)
        
    Returns:
        Generated description or None if failed
    """
    import asyncio
    
    client = OpenRouterClient(api_key)
    
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            client.generate_description(content, title, url, model)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in synchronous description generation: {str(e)}")
        return None
