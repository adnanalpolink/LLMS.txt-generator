import unittest
from unittest.mock import patch, MagicMock
import sys
import requests # <--- Added this import
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import categorize_urls, find_md_link, generate_llms_txt, clean_description

# DEFAULT_CATEGORY_KEYWORDS from app.py, copied here for test independence
DEFAULT_CATEGORY_KEYWORDS = {
    "Introduction": ["introduction", "intro", "overview", "about"],
    "Get started": ["get-started", "getting-started", "quickstart", "setup", "installation"],
    "Dashboard": ["dashboard", "admin", "console"],
    "API Reference": ["api", "reference", "sdk", "endpoints", "graphql", "swagger", "rest"],
    "Guides": [ # Further refined list
            "guide", "tutorial", "how-to", "howto", "walkthrough",
            "-example", "example-", "_example", "example_", # Removed /example and example/
            "-examples", "examples-", "_examples", "examples_", # Removed /examples and examples/
            "use-case", "getting-started/examples" # More specific example paths
    ],
    "Other": []
}

class TestAppLogic(unittest.TestCase):

    def test_categorize_urls(self):
        urls = [
            "http://example.com/intro-to-service",
            "http://example.com/docs/api-reference",
            "http://example.com/guides/how-to-use-feature-x",
            "http://example.com/blog/random-post",
            "http://example.com/getting-started-guide",
            "http://example.com/api/v2/endpoints"
        ]
        categorized = categorize_urls(urls, DEFAULT_CATEGORY_KEYWORDS)

        self.assertIn("http://example.com/intro-to-service", categorized["Introduction"])
        self.assertIn("http://example.com/docs/api-reference", categorized["API Reference"])
        self.assertIn("http://example.com/api/v2/endpoints", categorized["API Reference"])
        self.assertIn("http://example.com/guides/how-to-use-feature-x", categorized["Guides"])
        self.assertIn("http://example.com/getting-started-guide", categorized["Get started"])
        self.assertIn("http://example.com/blog/random-post", categorized["Other"])
        self.assertEqual(len(categorized["Dashboard"]), 0)

    @patch('requests.head')
    def test_find_md_link(self, mock_head):
        # Test case 1: .md file exists (e.g., page.html -> page.md)
        # Default mock response for cases where we expect a 404 or don't care about specific URL
        mock_response_not_found = MagicMock()
        mock_response_not_found.status_code = 404

        def side_effect_logic(url_to_check, **kwargs):
            # Case 1: page.html -> page.md
            if url_to_check == "http://example.com/docs/feature.md":
                resp = MagicMock()
                resp.status_code = 200
                resp.url = "http://example.com/docs/feature.md"
                return resp
            # Case 2: /docs/main -> /docs/main.md
            elif url_to_check == "http://example.com/docs/main.md":
                resp = MagicMock()
                resp.status_code = 200
                resp.url = "http://example.com/docs/main.md"
                return resp
            # Case 3: /docs/dir/ -> /docs/dir.md (assuming /docs/dir/dir.md 404s)
            elif url_to_check == "http://example.com/docs/dir/dir.md": # First attempt by find_md_link for trailing slash
                return mock_response_not_found
            elif url_to_check == "http://example.com/docs/dir.md": # Second attempt
                resp = MagicMock()
                resp.status_code = 200
                resp.url = "http://example.com/docs/dir.md"
                return resp
            # Case 5: Timeout
            elif url_to_check == "http://example.com/docs/timeout.md":
                raise requests.exceptions.Timeout
            # Case 6: Redirect to non-md
            elif url_to_check == "http://example.com/docs/redirect-test.md":
                resp = MagicMock()
                resp.status_code = 200
                resp.url = "http://example.com/docs/redirect-test.html" # Redirected to non-.md
                return resp
            # Default for others (like no-such-file.md)
            return mock_response_not_found

        mock_head.side_effect = side_effect_logic

        # Test case 1: .md file exists (e.g., page.html -> page.md)
        self.assertEqual(find_md_link("http://example.com/docs/feature.html"), "http://example.com/docs/feature.md")

        # Test case 2: path like /docs/main -> /docs/main.md
        self.assertEqual(find_md_link("http://example.com/docs/main"), "http://example.com/docs/main.md")

        # Test case 3: path like /docs/dir/ -> /docs/dir.md
        self.assertEqual(find_md_link("http://example.com/docs/dir/"), "http://example.com/docs/dir.md")

        # Test case 4: .md file does not exist (404)
        self.assertIsNone(find_md_link("http://example.com/docs/no-such-file.html")) # will try no-such-file.md

        # Test case 5: requests.head times out
        self.assertIsNone(find_md_link("http://example.com/docs/timeout.html")) # will try timeout.md

        # Test case 6: URL path doesn't end with .md after redirect
        self.assertIsNone(find_md_link("http://example.com/docs/redirect-test.html")) # will try redirect-test.md

        # Test case 7: Non-http URL
        mock_head.side_effect = None # Disable side_effect for this simple case not involving requests
        self.assertIsNone(find_md_link("ftp://example.com/docs/feature.html"))

    @patch('app.batch_process_urls') # Patching where it's used
    def test_generate_llms_txt_structure_and_format(self, mock_batch_process_urls):
        # Mock the return value of batch_process_urls
        # Each category will call batch_process_urls once.
        # Let's simulate two categories: Introduction and API Reference
        def mock_batch_side_effect(*args, **kwargs):
            urls_being_processed = args[0] # The list of URLs for the category
            if "http://example.com/intro" in urls_being_processed[0]:
                return [
                    ("Intro Page 1", "Description for intro 1.", "http://example.com/intro1", None),
                    ("Intro Page 2", "Description for intro 2.", "http://example.com/intro2", "http://example.com/intro2.md"),
                ]
            elif "http://example.com/api/ref1" in urls_being_processed[0]:
                return [
                    ("API Ref 1", "Description for API ref 1.", "http://example.com/api/ref1", "http://example.com/api/ref1.md"),
                ]
            return []

        mock_batch_process_urls.side_effect = mock_batch_side_effect

        urls_for_llms_txt = [
            "http://example.com/intro1", # Introduction
            "http://example.com/intro2", # Introduction
            "http://example.com/api/ref1", # API Reference
            "http://example.com/otherpage" # Other
        ]

        # For 'Other', let batch_process_urls return an empty list to test no header for empty actuals
        # Or let it return one item to test the 'Other' category.
        # Let's refine side_effect for the "Other" category specifically.

        def mock_batch_side_effect_detailed(*args, **kwargs):
            urls_being_processed = args[0]
            if not urls_being_processed: return [] # Should not happen if category_urls is not empty

            if "intro" in urls_being_processed[0]:
                 return [
                    ("Intro Page 1", "Description for intro 1.", "http://example.com/intro1", None),
                    ("Intro Page 2", "Description for intro 2.", "http://example.com/intro2", "http://example.com/intro2.md"),
                ]
            elif "api/ref1" in urls_being_processed[0]:
                 return [
                    ("API Ref 1", "Description for API ref 1.", "http://example.com/api/ref1", "http://example.com/api/ref1.md"),
                ]
            elif "otherpage" in urls_being_processed[0]:
                return [
                    ("Other Page", "Description for other.", "http://example.com/otherpage", None)
                ]
            return []
        mock_batch_process_urls.side_effect = mock_batch_side_effect_detailed


        llms_txt_content = generate_llms_txt(
            urls_for_llms_txt, "Test Site", "Test site description."
        )

        expected_parts = [
            "# Test Site",
            "> Test site description.",
            "## Introduction",
            "- [Intro Page 1](http://example.com/intro1): Description for intro 1.",
            "- [Intro Page 2](http://example.com/intro2): Description for intro 2. ([intro2.md](http://example.com/intro2.md))",
            "## API Reference",
            "- [API Ref 1](http://example.com/api/ref1): Description for API ref 1. ([ref1.md](http://example.com/api/ref1.md))",
            "## Other", # Assuming 'Other' category has items from the mock
            "- [Other Page](http://example.com/otherpage): Description for other.",
            "<!-- Generated by LLMS.txt Generator on " # Check for generation info start
        ]

        for part in expected_parts:
            self.assertIn(part, llms_txt_content)

        self.assertNotIn("## Dashboard", llms_txt_content) # Example of an empty category
        self.assertNotIn("## Get started", llms_txt_content)
        self.assertNotIn("## Guides", llms_txt_content)

        # Test that there's a blank line after a section's URLs
        self.assertIn("intro2.md](http://example.com/intro2.md))\n\n## API Reference", llms_txt_content)


    @patch('app.batch_process_urls')
    def test_generate_llms_txt_empty_sections_not_printed(self, mock_batch_process_urls):
        # Simulate that batch_process_urls returns empty lists for all categories except "Other"
        # and "Other" itself is empty.
        mock_batch_process_urls.return_value = []

        urls_for_llms_txt = [
            "http://example.com/some/other/url" # This URL will go to "Other"
        ]

        # If batch_process_urls returns [] for the "Other" category's URLs,
        # then no section should be printed.
        llms_txt_content = generate_llms_txt(
            urls_for_llms_txt, "Empty Site", "Site with no processable content."
        )

        self.assertNotIn("## Introduction", llms_txt_content)
        self.assertNotIn("## API Reference", llms_txt_content)
        self.assertNotIn("## Other", llms_txt_content)
        # Check that header and description are still there
        self.assertIn("# Empty Site", llms_txt_content)
        self.assertIn("> Site with no processable content.", llms_txt_content)
        self.assertIn("<!-- Generated by LLMS.txt Generator on ", llms_txt_content)


    def test_clean_description(self):
        self.assertEqual(clean_description("  Test   description  "), "Test description")
        self.assertEqual(clean_description("Test\n\ndescription\twith  spaces."), "Test description with spaces.")
        long_desc = "This is a very long description that definitely exceeds the one hundred and fifty character limit by a fair margin, so it should be truncated appropriately at the end."
        expected_trunc = long_desc[:147] + "..."
        self.assertEqual(clean_description(long_desc), expected_trunc)
        self.assertEqual(clean_description(None), "Resource information")
        self.assertEqual(clean_description(""), "Resource information")


if __name__ == '__main__':
    unittest.main()
