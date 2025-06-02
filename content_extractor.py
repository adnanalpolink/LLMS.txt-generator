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
            # Initial parse for pre-cleaning
            pre_soup = BeautifulSoup(html_content, 'html.parser')

            # Perform aggressive cleaning *before* readability
            # All cleaning operations below use 'pre_soup'

            unwanted_tag_names = [
                'script', 'style', 'nav', 'header', 'footer', 
                'aside', 'advertisement', 'ads', 'sidebar',
                'menu', 'breadcrumb', 'social', 'share', 'dialog',
                'form', 'input', 'textarea', 'button', 'select', 'option',
                'iframe', 'canvas', 'map', 'object', 'embed'
            ]
            for tag_name_iter in unwanted_tag_names:
                for element in pre_soup.find_all(tag_name_iter):
                    element.decompose()

            specific_selectors = [
                '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                '[aria-modal="true"]', '[role="dialog"]', '[role="alert"]',
                # 'header', 'footer', 'nav', 'aside', # Covered by unwanted_tag_names
                '.cookie', '#cookie', '.banner', '#banner', '.popup', '#popup',
                '.modal', '#modal', '.dialog', '#dialog', '.gdpr', '.cc-banner',
                '[class*="cookie"]', '[id*="cookie"]',
                '[class*="banner"]', '[id*="banner"]',
                '[class*="popup"]', '[id*="popup"]',
                '[class*="modal"]', '[id*="modal"]',
                '[class*="dialog"]', '[id*="dialog"]',
                '[class*="consent"]', '[id*="consent"]',
                '[class*="gdpr"]', '[id*="gdpr"]'
            ]
            for selector in specific_selectors:
                try:
                    for element in pre_soup.select(selector):
                        element.decompose()
                except Exception as e_select:
                    logger.warning(f"CSS selector error during pre-cleaning: {selector} - {str(e_select)}")

            unwanted_patterns = [
                'nav', 'header', 'footer', 'sidebar', 'menu', 'masthead', 'bottom',
                'advertisement', 'ads', 'social', 'share', 'rating', 'metadata',
                'breadcrumb', 'pagination', 'related', 'comment', 'testimonial', 'author-bio',
                'cookie', 'banner', 'popup', 'modal', 'dialog', 'consent', 'gdpr',
                'widget', 'toolbar', 'utility-bar', 'skip-link', 'visually-hidden', 'sr-only',
                'cookie-consent', 'privacy-popup' # Added from original list that was missed
            ]
            for pattern in unwanted_patterns:
                for element in pre_soup.find_all(class_=re.compile(r'\b' + pattern + r'\b', re.I)):
                    element.decompose()
                for element in pre_soup.find_all(id=re.compile(r'\b' + pattern + r'\b', re.I)):
                    element.decompose()

            elements_to_remove_hidden = []
            for element in pre_soup.find_all(True):
                style = element.get('style', '').replace(' ', '').lower()
                if 'display:none' in style or 'visibility:hidden' in style:
                    elements_to_remove_hidden.append(element)
            for element in elements_to_remove_hidden:
                element.decompose()

            cleaned_html_for_readability = pre_soup.prettify()
            doc = Document(cleaned_html_for_readability)
            main_content_html_from_readability = doc.summary()

            final_soup = BeautifulSoup(main_content_html_from_readability, 'html.parser')
            text_content = final_soup.get_text(separator=' ', strip=True)
            
            if not text_content and html_content:
                logger.warning("Readability produced empty content from pre-cleaned HTML. Using text from pre-cleaned HTML itself.")
                text_content = pre_soup.get_text(separator=' ', strip=True)
            
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            if not text_content and html_content:
                 logger.warning("All extraction methods resulted in empty. Basic pass on original HTML.")
                 soup_basic_pass = BeautifulSoup(html_content, 'html.parser')
                 basic_unwanted_tags = ['script', 'style', 'nav', 'header', 'footer', 'aside']
                 for tag_name_iter_basic in basic_unwanted_tags: # Renamed var
                     for tag_element_basic in soup_basic_pass.find_all(tag_name_iter_basic):
                         tag_element_basic.decompose()
                 text_content = soup_basic_pass.get_text(separator=' ', strip=True)
                 text_content = re.sub(r'\s+', ' ', text_content).strip()

            text_content = re.sub(r'\s+', ' ', text_content).strip()

            if 0 < len(text_content) < MIN_CONTENT_LENGTH and html_content:
                pass

            if len(text_content) > MAX_CONTENT_LENGTH:
                text_content = text_content[:MAX_CONTENT_LENGTH] + "..."
            
            if not text_content and html_content:
                soup_fallback_body = BeautifulSoup(html_content, 'html.parser') # Renamed var
                if soup_fallback_body.body:
                    text_content = soup_fallback_body.body.get_text(separator=' ', strip=True)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                    if len(text_content) > MAX_CONTENT_LENGTH:
                        text_content = text_content[:MAX_CONTENT_LENGTH] + "..."
                if not text_content:
                    logger.warning("Main content extraction resulted in empty string despite initial HTML content.")

            return text_content
            
        except Exception as e:
            logger.error(f"Error extracting main content: {str(e)}")
            soup_fallback_exception = BeautifulSoup(html_content, 'html.parser')
            basic_unwanted_tags_exception = ['script', 'style', 'nav', 'header', 'footer', 'aside'] # Renamed var
            for tag_name_iter_exception in basic_unwanted_tags_exception: # Renamed var
                for tag_element in soup_fallback_exception.find_all(tag_name_iter_exception):
                    tag_element.decompose()
            fallback_text = soup_fallback_exception.get_text(separator=' ', strip=True)
            fallback_text = re.sub(r'\s+', ' ', fallback_text).strip()
            if len(fallback_text) > MAX_CONTENT_LENGTH:
                fallback_text = fallback_text[:MAX_CONTENT_LENGTH] + "..."
            return fallback_text
    
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
