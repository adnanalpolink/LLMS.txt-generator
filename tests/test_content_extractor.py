import unittest
import sys
import os

# Add parent directory to path to import content_extractor
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from content_extractor import ContentExtractor

class TestContentExtractor(unittest.TestCase):

    def setUp(self):
        # Initialize ContentExtractor without Puppeteer for these tests
        # as we are providing HTML directly.
        self.extractor = ContentExtractor(use_puppeteer=False)

    def test_extract_main_content_simple(self):
        html_content = """
        <html><head><title>Test Page</title></head>
        <body>
            <header>Site Header</header>
            <nav>Navigation Menu</nav>
            <main>
                <h1>Main Title</h1>
                <p>This is the main article content.</p>
                <p>Another paragraph of the main content.</p>
            </main>
            <footer>Site Footer</footer>
        </body></html>
        """
        expected_text = "Main Title This is the main article content. Another paragraph of the main content."
        extracted_text = self.extractor.extract_main_content(html_content)
        self.assertEqual(extracted_text, expected_text)

    def test_extract_main_content_with_noise(self):
        html_content = """
        <html><head><title>Test Page</title></head>
        <body>
            <div id="cookie-banner">This is a cookie banner.</div>
            <header>Site Header</header>
            <nav role="navigation">Navigation Menu</nav>
            <aside class="sidebar">Sidebar content</aside>
            <article>
                <h2>Article Heading</h2>
                <p>First paragraph of the article.</p>
                <script>console.log("test");</script>
                <p>Second paragraph with a <a href="#">link</a>.</p>
                <div style="display:none;">This is hidden content.</div>
                <div class="advertisement">Ad content here</div>
            </article>
            <div class="modal" aria-modal="true">A pop-up modal.</div>
            <footer><p>Copyright 2024</p></footer>
        </body></html>
        """
        # Readability might pick "Article Heading" as title, so text starts from there.
        # The exact output of readability + further cleaning can be a bit sensitive.
        # The goal is to get the core text.
        # Adjusted for potential extra space before period due to .get_text() behavior
        expected_text = "Article Heading First paragraph of the article. Second paragraph with a link ."
        extracted_text = self.extractor.extract_main_content(html_content)
        self.assertEqual(extracted_text.strip(), expected_text.strip()) # Use strip for comparison robustness

    def test_extract_main_content_visually_hidden(self):
        html_content = """
        <html><body>
            <p>Visible text.</p>
            <p style="display: none;">Hidden text by display none.</p>
            <p style="visibility: hidden;">Hidden text by visibility hidden.</p>
            <p>More visible text.</p>
        </body></html>
        """
        expected_text = "Visible text. More visible text."
        extracted_text = self.extractor.extract_main_content(html_content)
        # Readability might also try to be smart. We test that our explicit removal works.
        # The key is that "Hidden text..." should not be there.
        self.assertNotIn("Hidden text by display none", extracted_text)
        self.assertNotIn("Hidden text by visibility hidden", extracted_text)
        self.assertTrue("Visible text." in extracted_text and "More visible text." in extracted_text)


    def test_extract_main_content_empty_input(self):
        html_content = ""
        expected_text = ""
        extracted_text = self.extractor.extract_main_content(html_content)
        self.assertEqual(extracted_text, expected_text)

    def test_extract_main_content_only_noise(self):
        html_content = """
        <html><head><title>Noise Page</title></head>
        <body>
            <header>Site Header</header>
            <nav>Navigation Menu</nav>
            <div id="cookie-banner">Cookie info</div>
            <style>.foo {}</style>
            <script>var x=1;</script>
            <footer>Site Footer</footer>
        </body></html>
        """
        # Readability might return the title "Noise Page" or an empty string.
        # Our cleaning should ensure nothing from the body remains.
        # If readability returns title, it will be "Noise Page". If not, empty.
        # The function also has fallbacks that might try to get *something*.
        # Let's assert that the known noise elements are not present.
        extracted_text = self.extractor.extract_main_content(html_content)
        self.assertNotIn("Site Header", extracted_text)
        self.assertNotIn("Navigation Menu", extracted_text)
        self.assertNotIn("Cookie info", extracted_text)
        self.assertNotIn("Site Footer", extracted_text)
        # If readability cannot find any content, it might return title.
        # If title is also not there, it might be empty.
        # This test is more about ensuring aggressive removal of non-content elements.
        # The current fallback logic in extract_main_content might get "Noise Page"
        # or if the body is empty, it might try body.get_text() which could be just whitespace.
        # A more robust check is that the cleaned content is very short if not empty.
        self.assertTrue(len(extracted_text) < 50)


    def test_extract_main_content_fallback_if_readability_empty(self):
        # This HTML might be entirely stripped by readability initially.
        # Example: A page that's just a collection of divs that readability doesn't see as an article
        html_content = """
        <html><head><title>Fallback Test</title></head><body>
            <div>This is some text in a div.</div>
            <div>Another bit of text.</div>
            <script>var x=1;</script>
            <footer>Footer for fallback test</footer>
        </body></html>
        """
        # The fallback logic in `extract_main_content` should trigger if `doc.summary()` is empty
        # and then try a more basic cleaning.
        # Expected: "Fallback Test This is some text in a div. Another bit of text." (title + body text minus script/footer)
        # Actual output depends heavily on readability's doc.summary() for this specific input.
        # If readability's summary is empty, the fallback is `soup_orig.get_text()`.
        # `extract_main_content` has a fallback:
        # if not initial_text_content and html_content:
        #    soup_orig = BeautifulSoup(html_content, 'html.parser')
        #    for tag_name in ['script', 'style', 'nav', 'header', 'footer', 'aside']: ...decompose...
        #    text_content = soup_orig.get_text()
        extracted_text = self.extractor.extract_main_content(html_content)
        self.assertIn("This is some text in a div.", extracted_text)
        self.assertIn("Another bit of text.", extracted_text)
        self.assertNotIn("Footer for fallback test", extracted_text) # Due to the fallback's own cleaning
        # Title might or might not be included by readability in this scenario.
        # If readability's summary is empty, our code doesn't explicitly add the title before basic cleaning.

    def test_extract_title_and_meta(self):
        html_content = """
        <html><head><title> My Page Title </title>
        <meta name="description" content=" This is the meta description.  ">
        </head><body></body></html>
        """
        title, desc = self.extractor.extract_title_and_meta(html_content, "http://example.com/test")
        self.assertEqual(title, "My Page Title")
        self.assertEqual(desc, "This is the meta description.")

    def test_extract_title_and_meta_og(self):
        html_content = """
        <html><head><title> OG Title </title>
        <meta property="og:description" content=" This is the OG description.  ">
        </head><body></body></html>
        """
        title, desc = self.extractor.extract_title_and_meta(html_content, "http://example.com/ogtest")
        self.assertEqual(title, "OG Title")
        self.assertEqual(desc, "This is the OG description.")

    def test_extract_title_and_meta_fallback(self):
        html_content = "<html><head></head><body></body></html>"
        title, desc = self.extractor.extract_title_and_meta(html_content, "http://example.com/fallback/page_name")
        self.assertEqual(title, "Page Name") # Fallback from URL path
        self.assertEqual(desc, "")

        title, desc = self.extractor.extract_title_and_meta(html_content, "http://example.com/")
        self.assertEqual(title, "example.com") # Fallback from domain
        self.assertEqual(desc, "")


if __name__ == '__main__':
    unittest.main()
