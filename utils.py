import re
import logging
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger('llms_generator.utils')

def normalize_url(url):
    """Normalize a URL by removing query parameters and fragments."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

def is_valid_url(url):
    """Check if a URL is valid."""
    parsed = urlparse(url)
    return bool(parsed.netloc and parsed.scheme in ['http', 'https'])

def get_domain(url):
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc

def get_base_url(url):
    """Get base URL (scheme + domain)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_content_type(url, timeout=10):
    """Determine content type of a URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '')
        return content_type.split(';')[0].strip().lower()
    except Exception as e:
        logger.warning(f"Could not determine content type for {url}: {str(e)}")
        return ""

def is_html_page(url, timeout=10):
    """Check if a URL points to an HTML page."""
    content_type = get_content_type(url, timeout)
    return content_type in ['text/html', 'application/xhtml+xml']

def is_media_file(url):
    """Check if a URL points to a media file."""
    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.webm', '.mp3', '.wav', '.pdf', '.zip', '.tar.gz']
    return any(url.lower().endswith(ext) for ext in extensions)

def extract_relative_links(html_content, base_url):
    """Extract and normalize relative links from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Skip anchors, javascript, and mailto links
        if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
            continue
        
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)
        
        # Ensure we're still on the same domain
        if get_domain(absolute_url) == get_domain(base_url):
            links.append(absolute_url)
    
    return links

def slugify(text):
    """Create a URL-friendly slug from text."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove special characters
    text = re.sub(r'[^a-z0-9\-]', '', text)
    # Remove duplicate hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text
