import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import normalize_url, is_valid_url, get_domain, get_base_url, slugify

class TestUtils(unittest.TestCase):
    def test_normalize_url(self):
        # Test with query parameters
        self.assertEqual(
            normalize_url("https://example.com/page?param=value"),
            "https://example.com/page"
        )
        
        # Test with fragments
        self.assertEqual(
            normalize_url("https://example.com/page#section"),
            "https://example.com/page"
        )
        
        # Test with both query parameters and fragments
        self.assertEqual(
            normalize_url("https://example.com/page?param=value#section"),
            "https://example.com/page"
        )
        
        # Test with trailing slash
        self.assertEqual(
            normalize_url("https://example.com/page/"),
            "https://example.com/page/"
        )
    
    def test_is_valid_url(self):
        # Valid URLs
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/page"))
        
        # Invalid URLs
        self.assertFalse(is_valid_url("example.com"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url(""))
    
    def test_get_domain(self):
        self.assertEqual(get_domain("https://example.com/path"), "example.com")
        self.assertEqual(get_domain("http://sub.example.com/path?query=value"), "sub.example.com")
    
    def test_get_base_url(self):
        self.assertEqual(get_base_url("https://example.com/path"), "https://example.com")
        self.assertEqual(get_base_url("http://sub.example.com/path?query=value"), "http://sub.example.com")
    
    def test_slugify(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
        self.assertEqual(slugify("  Spaces  at  edges  "), "spaces-at-edges")
        self.assertEqual(slugify("Special Ch@r$!"), "special-chr")
        self.assertEqual(slugify("Multiple---Hyphens"), "multiple-hyphens")

if __name__ == '__main__':
    unittest.main()
