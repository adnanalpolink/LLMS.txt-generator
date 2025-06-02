"""Enhanced content extraction with Puppeteer and main content filtering."""

import asyncio
import logging
import re
from typing import Optional, Tuple, Dict
from bs4 import BeautifulSoup
from readability import Document
import requests
from pyppeteer import launch
from config import (
    PUPPETEER_TIMEOUT, 
    PUPPETEER_WAIT_UNTIL, 
    USER_AGENT, 
    REQUEST_TIMEOUT,
    MAX_CONTENT_LENGTH,
    MIN_CONTENT_LENGTH
)

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Enhanced content extractor with Puppeteer support and main content filtering."""
    
    def __init__(self, use_puppeteer: bool = False):
        """Initialize the content extractor.
        
        Args:
            use_puppeteer: Whether to use Puppeteer for JavaScript rendering
        """
        self.use_puppeteer = use_puppeteer
        self.browser = None
    
    async def get_page_content_puppeteer(self, url: str) -> str:
        """Fetch page content using Puppeteer for JavaScript rendering.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string
        """
        try:
            if not self.browser:
                self.browser = await launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
            
            page = await self.browser.newPage()
            await page.setUserAgent(USER_AGENT)
            
            # Set viewport
            await page.setViewport({'width': 1920, 'height': 1080})
            
            # Navigate to page and wait for content
            await page.goto(url, {
                'waitUntil': PUPPETEER_WAIT_UNTIL,
                'timeout': PUPPETEER_TIMEOUT
            })
            
            # Get the HTML content
            content = await page.content()
            await page.close()
            
            return content
            
        except Exception as e:
            logger.error(f"Error fetching content with Puppeteer for {url}: {str(e)}")
            return ""
    
    def get_page_content_requests(self, url: str) -> str:
        """Fetch page content using requests (traditional method).
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string
        """
        try:
            headers = {"User-Agent": USER_AGENT}
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching content with requests for {url}: {str(e)}")
            return ""
    
    async def get_page_content(self, url: str) -> str:
        """Get page content using the configured method.
        
        Args:
            url: The URL to fetch
            
        Returns:
            HTML content as string
        """
        if self.use_puppeteer:
            return await self.get_page_content_puppeteer(url)
        else:
            return self.get_page_content_requests(url)
    
    def extract_main_content(self, html_content: str) -> str:
        """Extract main content from HTML, excluding headers, footers, and navigation.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            Cleaned main content as text
        """
        if not html_content:
            return ""
        
        try:
            # Use readability to extract main content
            doc = Document(html_content)
            main_content_html = doc.summary()
            
            # Parse with BeautifulSoup for further cleaning
            soup = BeautifulSoup(main_content_html, 'html.parser')
            
            # Remove unwanted elements
            unwanted_tags = [
                'script', 'style', 'nav', 'header', 'footer', 
                'aside', 'advertisement', 'ads', 'sidebar',
                'menu', 'breadcrumb', 'social', 'share'
            ]
            
            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove elements with unwanted classes/ids
            unwanted_patterns = [
                'nav', 'header', 'footer', 'sidebar', 'menu',
                'advertisement', 'ads', 'social', 'share',
                'breadcrumb', 'pagination', 'related', 'comment'
            ]
            
            for pattern in unwanted_patterns:
                # Remove by class
                for element in soup.find_all(class_=re.compile(pattern, re.I)):
                    element.decompose()
                # Remove by id
                for element in soup.find_all(id=re.compile(pattern, re.I)):
                    element.decompose()
            
            # Extract text content
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Limit content length
            if len(text_content) > MAX_CONTENT_LENGTH:
                text_content = text_content[:MAX_CONTENT_LENGTH] + "..."
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting main content: {str(e)}")
            # Fallback to basic text extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)[:MAX_CONTENT_LENGTH]
    
    def extract_title_and_meta(self, html_content: str, url: str = "") -> Tuple[str, str]:
        """Extract title and meta description from HTML.
        
        Args:
            html_content: Raw HTML content
            url: The page URL (for fallback title)
            
        Returns:
            Tuple of (title, meta_description)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get title
            title = ""
            if soup.title:
                title = soup.title.string.strip() if soup.title.string else ""
            
            # Fallback title from URL
            if not title and url:
                from urllib.parse import urlparse
                path = urlparse(url).path
                title = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
                if not title:
                    title = urlparse(url).netloc
            
            # Get meta description
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc.get("content").strip()
            
            # Fallback to Open Graph description
            if not description:
                og_desc = soup.find("meta", attrs={"property": "og:description"})
                if og_desc and og_desc.get("content"):
                    description = og_desc.get("content").strip()
            
            return title, description
            
        except Exception as e:
            logger.error(f"Error extracting title and meta: {str(e)}")
            return f"Page at {url.split('/')[-1]}" if url else "Unknown Page", ""
    
    async def close(self):
        """Close the Puppeteer browser if it's open."""
        if self.browser:
            await self.browser.close()
            self.browser = None


# Synchronous wrapper functions for easier integration
def extract_content_sync(url: str, use_puppeteer: bool = False) -> Tuple[str, str, str]:
    """Synchronous wrapper for content extraction.
    
    Args:
        url: The URL to process
        use_puppeteer: Whether to use Puppeteer for rendering
        
    Returns:
        Tuple of (title, meta_description, main_content)
    """
    extractor = ContentExtractor(use_puppeteer)
    
    try:
        # Run async extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        html_content = loop.run_until_complete(extractor.get_page_content(url))
        
        if html_content:
            title, meta_desc = extractor.extract_title_and_meta(html_content, url)
            main_content = extractor.extract_main_content(html_content)
            
            # Close browser if used
            loop.run_until_complete(extractor.close())
            loop.close()
            
            return title, meta_desc, main_content
        else:
            loop.run_until_complete(extractor.close())
            loop.close()
            return f"Page at {url.split('/')[-1]}", "Resource information", ""
            
    except Exception as e:
        logger.error(f"Error in synchronous content extraction for {url}: {str(e)}")
        return f"Page at {url.split('/')[-1]}", "Resource information", ""
