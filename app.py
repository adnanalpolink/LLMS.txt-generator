import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import base64
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import concurrent.futures
import time
from datetime import datetime
import re
import logging
import asyncio
from typing import Optional, Tuple

# Import our new modules
from content_extractor import ContentExtractor, extract_content_sync
from openrouter_client import OpenRouterClient, generate_description_sync
from config import (
    DEFAULT_LLM_MODELS,
    DEFAULT_MODEL,
    MIN_CONTENT_LENGTH,
    CATEGORIZED_LLM_MODELS,
    validate_custom_model,
    get_model_display_name
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set page configuration
st.set_page_config(
    page_title="LLMS.txt Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .stProgress > div > div > div {background-color: #1565C0;}
    .download-btn {
        background-color: #1565C0;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.3rem;
        text-decoration: none;
        font-weight: bold;
        display: inline-block;
        margin-top: 1rem;
    }
    .download-btn:hover {background-color: #0D47A1;}
    .download-btn {color: white !important;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def extract_urls_from_sitemap(sitemap_url, processed_sitemaps=None):
    """Extract URLs from an XML sitemap, including sitemap indexes."""
    if processed_sitemaps is None:
        processed_sitemaps = set()
    
    if sitemap_url in processed_sitemaps:
        return []
    
    processed_sitemaps.add(sitemap_url)
    
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        # Check if it's a sitemap index
        root = ET.fromstring(response.content)
        
        # Define namespace map
        ns_map = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9"
        }
        
        urls = []
        
        # Check if this is a sitemap index
        if root.tag.endswith('sitemapindex'):
            st.info(f"Processing sitemap index: {sitemap_url}")
            for sitemap in root.findall('.//sm:sitemap', ns_map):
                loc = sitemap.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    # Recursively process each sitemap
                    child_urls = extract_urls_from_sitemap(loc.text, processed_sitemaps)
                    urls.extend(child_urls)
        else:
            # Regular sitemap
            for url in root.findall('.//sm:url', ns_map):
                loc = url.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    urls.append(loc.text)
        
        return urls
    except Exception as e:
        st.error(f"Error processing sitemap {sitemap_url}: {str(e)}")
        return []

def extract_urls_from_csv(csv_file):
    """Extract URLs from a CSV file."""
    try:
        df = pd.read_csv(csv_file)
        
        # Try to find URL columns
        possible_url_columns = [col for col in df.columns if any(url_key in col.lower() for url_key in ['url', 'link', 'href', 'path'])]
        
        if possible_url_columns:
            # Use the first URL-like column
            url_column = possible_url_columns[0]
            urls = df[url_column].tolist()
            # Filter out non-URLs and NaN values
            urls = [url for url in urls if isinstance(url, str) and url.strip().startswith(('http://', 'https://'))]
            return urls
        else:
            # Try first column as fallback
            first_col = df.iloc[:, 0]
            urls = first_col.tolist()
            # Filter out non-URLs and NaN values
            urls = [url for url in urls if isinstance(url, str) and url.strip().startswith(('http://', 'https://'))]
            if urls:
                return urls
            else:
                st.warning("No URL column identified in the CSV file.")
                return []
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        return []

def get_page_content_enhanced(url, use_puppeteer=False, use_llm=False, llm_model=DEFAULT_MODEL, api_key=None):
    """Enhanced content extraction with Puppeteer and LLM integration.

    Args:
        url: The URL to fetch
        use_puppeteer: Whether to use Puppeteer for JavaScript rendering
        use_llm: Whether to use LLM for description generation
        llm_model: The LLM model to use
        api_key: OpenRouter API key

    Returns:
        Tuple of (title, description, main_content)
    """
    try:
        # Extract content using the enhanced extractor
        title, meta_desc, main_content = extract_content_sync(url, use_puppeteer)

        # Use LLM to generate description if enabled and content is sufficient
        if use_llm and api_key and len(main_content) >= MIN_CONTENT_LENGTH:
            llm_description = generate_description_sync(
                content=main_content,
                title=title,
                url=url,
                model=llm_model,
                api_key=api_key
            )

            # Use LLM description if available, otherwise fall back to meta description
            description = llm_description if llm_description else meta_desc
        else:
            description = meta_desc

        # Fallback to first paragraph if no description
        if not description and main_content:
            # Extract first meaningful sentence from main content
            sentences = main_content.split('. ')
            if sentences:
                description = sentences[0]
                if len(description) > 150:
                    description = description[:147] + "..."

        # Final fallback
        if not description:
            description = "Resource information"

        return title, description, main_content

    except Exception as e:
        logging.error(f"Error in enhanced content extraction for {url}: {str(e)}")
        return f"Page at {url.split('/')[-1]}", "Resource information", ""

def get_page_content(url):
    """Legacy function for backward compatibility."""
    title, _, _ = get_page_content_enhanced(url, use_puppeteer=False, use_llm=False)
    return ""  # Return empty string to maintain compatibility

def extract_title_and_description(html_content, url=""):
    """Legacy function for backward compatibility."""
    if not html_content:
        # Use enhanced extraction as fallback
        title, description, _ = get_page_content_enhanced(url, use_puppeteer=False, use_llm=False)
        return title, description

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Get title
        title = soup.title.string if soup.title else ""
        title = title.strip() if title else ""

        # If no title found, use the last part of the URL
        if not title and url:
            path = urlparse(url).path
            title = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            # If still empty, use domain name
            if not title:
                title = urlparse(url).netloc

        # Get meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc.get("content").strip()

        # If no description, try to get the first paragraph
        if not description:
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text().strip()
                # Truncate if too long
                if len(description) > 150:
                    description = description[:147] + "..."

        return title, description
    except Exception:
        return f"Page at {url.split('/')[-1]}", "Resource information"

def categorize_urls(urls, category_keywords):
    """Categorize URLs into sections based on keywords in their path or full URL.

    Args:
        urls: A list of URLs to categorize.
        category_keywords: A dictionary where keys are category names (section titles)
                           and values are lists of keywords.
                           Example: {"Introduction": ["intro", "start"], "API": ["api", "reference"]}

    Returns:
        A dictionary where keys are category names and values are lists of URLs
        belonging to that category. Includes a fallback "Other" category.
    """
    categorized = {category: [] for category in category_keywords}
    # Ensure "Other" category exists if not defined by user, though it's good practice to include it.
    if "Other" not in categorized:
        categorized["Other"] = []

    url_lower_map = {url: url.lower() for url in urls} # Pre-lower case for efficiency

    for url in urls:
        matched = False
        url_low = url_lower_map[url]
        path_low = urlparse(url).path.lower()
        
        for category, keywords in category_keywords.items():
            if category == "Other": # Skip "Other" during keyword matching pass
                continue

            # Keywords in category_keywords are assumed to be lowercase already
            if any(kw in url_low for kw in keywords) or \
               any(kw in path_low for kw in keywords):
                categorized[category].append(url)
                matched = True
                break  # First match wins

        if not matched:
            categorized["Other"].append(url)

    # Remove empty categories from the final output, except "Other" if it's also empty.
    # Or, keep all defined categories even if empty, for consistency in llms.txt structure.
    # For now, let's keep all defined categories. If "Other" is empty and was predefined, it's kept.
    return {k: v for k, v in categorized.items() if v or k in category_keywords}


def find_md_link(url: str) -> Optional[str]:
    """
    Checks for a corresponding .md file for a given URL by trying common patterns.
    Example: https://example.com/docs/feature -> https://example.com/docs/feature.md
             https://example.com/docs/feature.html -> https://example.com/docs/feature.md
             https://example.com/docs/feature/ -> https://example.com/docs/feature.md (or feature/feature.md)
    Makes an HTTP HEAD request to verify existence.
    """
    if not url.startswith(('http://', 'https://')):
        return None

    parsed_url = urlparse(url)
    path = parsed_url.path
    base_url_for_md = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    potential_md_paths = set()

    # Common web extensions to replace
    extensions_to_replace = ['.html', '.htm', '.php', '.aspx', '.asp']

    current_path_segment = path

    # Case 1: URL ends with a common web extension
    for ext in extensions_to_replace:
        if current_path_segment.endswith(ext):
            potential_md_paths.add(current_path_segment[:-len(ext)] + ".md")
            break
    else: # No common extension found, or after stripping extension
        # Case 2: URL ends with a slash (directory-like)
        if current_path_segment.endswith('/'):
            # e.g., /docs/feature/ -> /docs/feature.md
            potential_md_paths.add(current_path_segment[:-1] + ".md")
            # e.g., /docs/feature/ -> /docs/feature/feature.md (less common for .md but possible)
            # Only add if path has at least one segment before trailing slash
            parent_dir_name = current_path_segment.strip('/').split('/')[-1]
            if parent_dir_name:
                 potential_md_paths.add(current_path_segment + parent_dir_name + ".md")
        # Case 3: URL does not end with slash and no common extension (e.g. /docs/feature)
        else:
            potential_md_paths.add(current_path_segment + ".md")

    # Construct full URLs and test them
    for md_path in potential_md_paths:
        if not md_path: continue
        # Ensure path starts with a slash
        md_url_to_check = base_url_for_md + (md_path if md_path.startswith('/') else '/' + md_path)
        try:
            head_response = requests.head(md_url_to_check, timeout=2.5, allow_redirects=True) # Short timeout
            # Allow redirects because site might redirect /feature to /feature.md or vice-versa
            if head_response.status_code == 200:
                # Check if the final URL after redirects actually ends with .md
                if urlparse(head_response.url).path.endswith(".md"):
                    return head_response.url # Return the potentially redirected URL if it's the .md one
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout checking for .md link: {md_url_to_check}")
        except requests.exceptions.RequestException:
            pass # Silently ignore other errors (connection, too many redirects, etc.)

    return None


def process_url(url, default_desc="Resource", use_puppeteer=False, use_llm=False, llm_model=DEFAULT_MODEL, api_key=None, check_for_md=False):
    """Process a single URL to get title, description, and optionally an .md link.

    Args:
        url: The URL to process
        default_desc: Default description if none found
        use_puppeteer: Whether to use Puppeteer for JavaScript rendering
        use_llm: Whether to use LLM for description generation
        llm_model: The LLM model to use
        api_key: OpenRouter API key
        check_for_md: Boolean flag to attempt .md link discovery

    Returns:
        Tuple of (title, description, url, md_link)
    """
    md_link = None
    try:
        title, desc, main_content = get_page_content_enhanced(
            url, use_puppeteer, use_llm, llm_model, api_key
        )

        title = title if title else url.split('/')[-1]
        desc = desc if desc else default_desc

        if check_for_md:
            md_link = find_md_link(url)

        return title, desc, url, md_link

    except Exception as e:
        logging.error(f"Error processing URL {url}: {str(e)}")
        return url.split('/')[-1], default_desc, url, None

def batch_process_urls(urls, category_desc="Resource", max_workers=5, use_puppeteer=False, use_llm=False, llm_model=DEFAULT_MODEL, api_key=None, check_for_md_for_category=False):
    """Process multiple URLs in parallel with enhanced features.

    Args:
        urls: List of URLs to process
        category_desc: Default description for the category
        max_workers: Maximum number of concurrent workers
        use_puppeteer: Whether to use Puppeteer for JavaScript rendering
        use_llm: Whether to use LLM for description generation
        llm_model: The LLM model to use
        api_key: OpenRouter API key
        check_for_md_for_category: Boolean flag to attempt .md link discovery for this batch

    Returns:
        List of tuples (title, description, url, md_link)
    """
    results = []

    actual_max_workers = max_workers
    # Reduce workers if using Puppeteer to avoid resource issues
    if use_puppeteer:
        actual_max_workers = min(actual_max_workers, 2) # Puppeteer is resource-intensive
    # Reduce workers further if also checking for .md links to avoid too many outbound requests quickly
    if check_for_md_for_category:
        actual_max_workers = min(actual_max_workers, 3) # Max 3 workers if checking .md links

    # Ensure at least 1 worker
    actual_max_workers = max(1, actual_max_workers)


    with concurrent.futures.ThreadPoolExecutor(max_workers=actual_max_workers) as executor:
        future_to_url_map = {}
        for u in urls: # Changed variable name to avoid conflict
            future = executor.submit(
                process_url,
                u, # Current URL being processed
                category_desc,
                use_puppeteer,
                use_llm,
                llm_model,
                api_key,
                check_for_md_for_category # Pass the flag here
            )
            future_to_url_map[future] = u


        for future in concurrent.futures.as_completed(future_to_url_map):
            url_processed_item = future_to_url_map[future]
            try:
                result_tuple = future.result() # This will be (title, desc, original_url, md_link)
                results.append(result_tuple)
            except Exception as e:
                logging.error(f"Error processing URL {url_processed_item} in batch future: {str(e)}")
                path = urlparse(url_processed_item).path
                filename = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
                title = filename if filename else url_processed_item.split('/')[-1]
                results.append((title, category_desc, url_processed_item, None)) # Add None for md_link in error case

    return results

def clean_description(desc):
    """Clean and format description text."""
    if not desc:
        return "Resource information"
    
    # Remove newlines and excessive spaces
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    # Truncate if too long
    if len(desc) > 150:
        return desc[:147] + "..."
    
    return desc

def generate_llms_txt(urls, site_name, site_description, status_placeholder=None, use_puppeteer=False, use_llm=False, llm_model=DEFAULT_MODEL, api_key=None):
    """Generate the llms.txt content from a list of URLs with enhanced features.

    Args:
        urls: List of URLs to process
        site_name: Name of the website
        site_description: Description of the website
        status_placeholder: Streamlit placeholder for status updates
        use_puppeteer: Whether to use Puppeteer for JavaScript rendering
        use_llm: Whether to use LLM for description generation
        llm_model: The LLM model to use
        api_key: OpenRouter API key

    Returns:
        Generated llms.txt content as string
    """
    if not urls:
        return "No valid URLs provided."

    # Generate status updates
    if status_placeholder:
        status_text = "Processing URLs"
        if use_puppeteer:
            status_text += " with JavaScript rendering"
        if use_llm:
            status_text += " and AI descriptions"
        status_text += "..."
        status_placeholder.write(status_text)

    # Get the base URL from the first URL
    base_url = urlparse(urls[0]).netloc

    # Add protocol if missing in site name
    if not site_name:
        site_name = base_url.split('.')[-2].capitalize() if len(base_url.split('.')) > 1 else base_url

    if not site_description:
        site_description = f"Information about {site_name}"

    # Start building the llms.txt content
    content = []

    # Add header
    content.append(f"# {site_name}")
    content.append(f"> {site_description}")
    content.append("")

    # Define default categories and keywords
    DEFAULT_CATEGORY_KEYWORDS = {
        "Introduction": ["introduction", "intro", "overview", "about"],
        "Get started": ["get-started", "getting-started", "quickstart", "setup", "installation"],
        "Dashboard": ["dashboard", "admin", "console"],
        "API Reference": ["api", "reference", "sdk", "endpoints", "graphql", "swagger", "rest"],
        "Guides": [ # Restored to refined list
            "guide", "tutorial", "how-to", "howto", "walkthrough",
            "-example", "example-", "_example", "example_",
            "-examples", "examples-", "_examples", "examples_",
            "use-case", "getting-started/examples"
        ],
        "Other": []  # Fallback category, will catch URLs not matched by others
    }
    # Categories eligible for .md link checking
    MD_CHECK_CATEGORIES = {"API Reference", "Guides", "Docs", "Introduction", "Get started"}


    # Categorize URLs
    categorized_urls_map = categorize_urls(urls, DEFAULT_CATEGORY_KEYWORDS)

    # Process URLs and build content section by section
    total_processed_count = 0
    any_category_had_content = False

    for category_title, category_urls in categorized_urls_map.items():
        if not category_urls:
            # Special handling for "Other": only skip if it's empty AND other categories have/had content or will have content.
            # If "Other" is the only category with items, it should be processed.
            # If all categories are empty, nothing gets processed, which is fine.
            if category_title == "Other":
                is_other_empty = True
                other_cats_have_content = False
                for c_title, c_urls in categorized_urls_map.items():
                    if c_title != "Other" and c_urls:
                        other_cats_have_content = True
                        break
                if is_other_empty and other_cats_have_content:
                    continue # Skip empty "Other" if other categories have content
                elif is_other_empty and not other_cats_have_content and any_category_had_content: # Other is empty, no other cats have content now, but some previous cat had content
                    continue

            else: # For non-"Other" categories, if it's empty, just skip.
                continue

        current_category_has_entries = False
        temp_category_content = [] # Store entries for current category temporarily

        temp_category_content.append(f"## {category_title}")
        temp_category_content.append("")

        if status_placeholder:
            status_placeholder.write(f"Processing {len(category_urls)} URLs for {category_title}...")

        should_check_md_for_this_category = category_title in MD_CHECK_CATEGORIES

        processed_category_items = batch_process_urls(
            category_urls,
            f"{category_title} resource",
            max_workers=5,
            use_puppeteer=use_puppeteer,
            use_llm=use_llm,
            llm_model=llm_model,
            api_key=api_key,
            check_for_md_for_category=should_check_md_for_this_category
        )

        for title, desc, url_processed, md_link in processed_category_items:
            entry = f"- [{title}]({url_processed}): {clean_description(desc)}"
            if md_link:
                md_filename = md_link.split('/')[-1]
                entry += f" ([{md_filename}]({md_link}))"
            temp_category_content.append(entry)
            total_processed_count += 1
            current_category_has_entries = True

        if current_category_has_entries:
            temp_category_content.append("") # Add a blank line after section's URLs
            content.extend(temp_category_content)
            any_category_had_content = True
        # If no entries for this category, temp_category_content (header and blank line) is discarded.


    if total_processed_count == 0 and urls:
        # Fallback: if no URLs were processed at all despite having initial URLs (e.g. all categories empty, errors)
        # This should be rare due to the "Other" category logic.
        if status_placeholder:
            status_placeholder.write("Processing all URLs under General Information as fallback...")

        content.append("## General Information")
        content.append("")

        processed_remaining_urls = batch_process_urls(
            urls,
            "Resource information",
            max_workers=5,
            use_puppeteer=use_puppeteer,
            use_llm=use_llm,
            llm_model=llm_model,
            api_key=api_key,
            check_for_md_for_category=False # No .md check for this broad fallback
        )
        fallback_entries_added = False
        for title, desc, url_processed, md_link in processed_remaining_urls:
            content.append(f"- [{title}]({url_processed}): {clean_description(desc)}")
            fallback_entries_added = True

        if fallback_entries_added:
            content.append("")
        else: # No entries for General Information either, remove its header
            if content and content[-1] == "": content.pop()
            if content and content[-1] == "## General Information": content.pop()


    # Remove the last empty line if it exists and content was actually added
    if content and content[-1] == "" and total_processed_count > 0 :
        content.pop()

    # Add generation info
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generation_info = f"<!-- Generated by LLMS.txt Generator on {now}"
    if use_puppeteer:
        generation_info += " with JavaScript rendering"
    if use_llm:
        generation_info += f" and AI descriptions ({llm_model})"
    generation_info += " -->"
    content.append(generation_info)

    return "\n".join(content)

def get_download_link(content, filename="llms.txt"):
    """Generate a download link for the text content."""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="download-btn">Download {filename}</a>'
    return href

def check_llm_crawler_accessibility(domain):
    """Check if various LLM crawlers are blocked in robots.txt."""
    # List of LLM crawlers
    llm_crawlers = [
        "AI2Bot",
        "Ai2Bot-Dolma",
        "Amazonbot",
        "anthropic-ai",
        "Applebot",
        "Applebot-Extended",
        "Brightbot 1.0",
        "Bytespider",
        "CCBot",
        "ChatGPT-User",
        "Claude-Web",
        "ClaudeBot",
        "cohere-ai",
        "cohere-training-data-crawler",
        "Crawlspace",
        "Diffbot",
        "DuckAssistBot",
        "FacebookBot",
        "FriendlyCrawler",
        "Google-Extended",
        "GoogleOther",
        "GoogleOther-Image",
        "GoogleOther-Video",
        "GPTBot",
        "iaskspider/2.0",
        "ICC-Crawler",
        "ImagesiftBot",
        "img2dataset",
        "ISSCyberRiskCrawler",
        "Kangaroo Bot",
        "Meta-ExternalAgent",
        "Meta-ExternalFetcher",
        "OAI-SearchBot",
        "omgili",
        "omgilibot",
        "PanguBot",
        "PerplexityBot",
        "Perplexity‑User",
        "PetalBot",
        "Scrapy",
        "SemrushBot-OCOB",
        "SemrushBot-SWA",
        "Sidetrade indexer bot",
        "Timpibot",
        "VelenPublicWebCrawler",
        "Webzio-Extended",
        "YouBot"
    ]
    
    blocked_crawlers = []
    
    # Check robots.txt
    try:
        robots_url = f"https://{domain}/robots.txt"
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            robots_content = response.text.split('\n')
            current_user_agent = None
            disallow_rules = []
            
            for line in robots_content:
                line = line.strip()
                if line.lower().startswith('user-agent:'):
                    current_user_agent = line.split(':', 1)[1].strip()
                    disallow_rules = []
                elif line.lower().startswith('disallow:') and current_user_agent:
                    disallow_rules.append(line.split(':', 1)[1].strip())
                    
                    # Check if this user agent matches any of our crawlers
                    for crawler in llm_crawlers:
                        if (current_user_agent == '*' or 
                            crawler.lower() in current_user_agent.lower() or 
                            current_user_agent.lower() in crawler.lower()):
                            if any(rule == '/' for rule in disallow_rules):
                                if crawler not in blocked_crawlers:
                                    blocked_crawlers.append(crawler)
    except Exception as e:
        st.error(f"Error checking robots.txt: {str(e)}")
    
    return blocked_crawlers

def display_crawler_results(blocked_crawlers):
    """Display the crawler blocking results in a nice format."""
    st.subheader("✅ Robots.txt Check")
    st.markdown("""
    This tool checks if any LLM crawlers are blocked in your robots.txt file.
    """)
    
    if blocked_crawlers:
        st.warning("⚠️ The following crawlers are blocked in your robots.txt file:")
        for crawler in blocked_crawlers:
            st.markdown(f"- {crawler}")
        st.info("To allow these crawlers, please remove their entries from your robots.txt file.")
    else:
        st.success("✅ No LLM crawlers are blocked in your robots.txt file!")
        st.info("Your site is accessible to all LLM crawlers according to robots.txt rules.")

def main():
    """Main application function."""
    st.title("🤖 LLMS.txt Generator")
    
    with st.expander("About LLMS.txt", expanded=False):
        st.markdown("""
        The `llms.txt` file is a standard proposed by [Answer.AI](https://github.com/AnswerDotAI/llms-txt) to help Large Language Models (LLMs) better understand and use website content. 
        
        Similar to how `robots.txt` provides directives to search engines, `llms.txt` offers structured information to LLMs about your website's most important content, documentation, and resources.
        
        This tool helps you generate a well-formatted `llms.txt` file for your website by analyzing your sitemap or a list of URLs.
        """)
    
    # Create tabs with clear labels
    tab1, tab2 = st.tabs(["📄 Generate LLMS.txt", "🔍 Check Crawler Access"])
    
    with tab1:
        st.subheader("Generate LLMS.txt File")

        # Main configuration
        col1, col2 = st.columns([3, 2])

        with col1:
            st.subheader("Website Information")
            site_name = st.text_input("Website Name", placeholder="My Website")
            site_description = st.text_area("Website Description",
                                           placeholder="A brief description of what your website is about",
                                           height=100)

        with col2:
            st.subheader("URL Source")
            input_type = st.radio("Select input type:", ["Sitemap URL", "CSV Upload"])

            if input_type == "Sitemap URL":
                sitemap_url = st.text_input("Sitemap URL", placeholder="https://example.com/sitemap.xml")
                input_ready = sitemap_url.strip() != ""
            else:
                uploaded_file = st.file_uploader("Upload CSV with URLs", type=['csv'])
                input_ready = uploaded_file is not None

        # Enhanced features section
        st.subheader("🚀 Enhanced Features")

        col3, col4 = st.columns([1, 1])

        with col3:
            st.markdown("**JavaScript Rendering**")
            use_puppeteer = st.checkbox(
                "Use Puppeteer for JavaScript-heavy pages",
                help="Enable this for pages that require JavaScript to load content. This will be slower but more accurate for dynamic sites."
            )

        with col4:
            st.markdown("**AI-Generated Descriptions**")
            use_llm = st.checkbox(
                "Generate descriptions using AI",
                help="Use OpenRouter API to generate intelligent descriptions of page content instead of just meta descriptions."
            )

        # LLM Configuration (only show if LLM is enabled)
        if use_llm:
            st.markdown("**LLM Configuration**")

            # API Key input
            api_key = st.text_input(
                "OpenRouter API Key",
                type="password",
                placeholder="sk-or-v1-...",
                help="Get your API key from https://openrouter.ai/keys"
            )

            # Model selection with categorized options
            col5, col6 = st.columns([2, 1])

            with col5:
                # Create categorized options for the selectbox
                model_options = []
                model_values = []

                # Add categorized models
                for provider, models in CATEGORIZED_LLM_MODELS.items():
                    for model in models:
                        display_name = f"{provider}: {get_model_display_name(model)}"
                        model_options.append(display_name)
                        model_values.append(model)

                # Add custom model option
                model_options.append("Custom Model")
                model_values.append("custom")

                # Find default model index
                default_index = 0
                if DEFAULT_MODEL in model_values:
                    default_index = model_values.index(DEFAULT_MODEL)

                selected_model_display = st.selectbox(
                    "LLM Model",
                    options=model_options,
                    index=default_index,
                    help="Choose the AI model for generating descriptions"
                )

                # Get the actual model value
                selected_index = model_options.index(selected_model_display)
                selected_model_value = model_values[selected_index]

            with col6:
                # Show model info
                if selected_model_value != "custom":
                    # Extract provider from model name
                    provider = selected_model_value.split('/')[0] if '/' in selected_model_value else "Unknown"
                    st.info(f"**Provider:** {provider.title()}")

                    # Show if it's a free model
                    if ':free' in selected_model_value:
                        st.success("🆓 Free Model")
                    elif ':thinking' in selected_model_value:
                        st.info("🧠 Thinking Model")
                else:
                    st.info("💡 Custom Model")

            # Custom model input (only show if custom is selected)
            if selected_model_value == "custom":
                custom_model = st.text_input(
                    "Custom Model Name",
                    placeholder="provider/model-name or provider/model-name:variant",
                    help="Enter any OpenRouter-compatible model identifier (e.g., 'anthropic/claude-3-opus', 'openai/gpt-4:turbo')"
                )

                # Validate custom model format
                if custom_model:
                    if validate_custom_model(custom_model):
                        st.success(f"✅ Valid model format: `{custom_model}`")
                        llm_model = custom_model
                    else:
                        st.error("❌ Invalid model format. Use: `provider/model-name` or `provider/model-name:variant`")
                        llm_model = DEFAULT_MODEL
                else:
                    st.warning("⚠️ Please enter a custom model name.")
                    llm_model = DEFAULT_MODEL
            else:
                llm_model = selected_model_value

            if not api_key:
                st.warning("⚠️ Please provide an OpenRouter API key to use AI-generated descriptions.")
                use_llm = False
        
        # Set default values for LLM configuration if not using LLM
        if not use_llm:
            api_key = None
            llm_model = DEFAULT_MODEL

        if st.button("Generate LLMS.txt", disabled=not input_ready, type="primary"):
            with st.spinner("Processing URLs..."):
                # Extract URLs based on the selected input type
                if input_type == "Sitemap URL":
                    urls = extract_urls_from_sitemap(sitemap_url)
                else:
                    urls = extract_urls_from_csv(uploaded_file)

                if not urls:
                    st.error("No valid URLs found. Please check your input.")
                else:
                    st.success(f"Found {len(urls)} URLs.")

                    # Use default values if not provided
                    if not site_name:
                        domain = urlparse(urls[0]).netloc
                        site_name = domain.split('.')[-2].capitalize() if len(domain.split('.')) > 1 else domain

                    if not site_description:
                        site_description = f"Information about {site_name}"

                    # Show feature summary
                    features_used = []
                    if use_puppeteer:
                        features_used.append("JavaScript rendering")
                    if use_llm and api_key:
                        features_used.append(f"AI descriptions ({llm_model})")

                    if features_used:
                        st.info(f"🚀 Using enhanced features: {', '.join(features_used)}")

                    # Process URLs and generate llms.txt with enhanced features
                    status_container = st.empty()
                    with st.spinner("Generating LLMS.txt..."):
                        llms_txt_content = generate_llms_txt(
                            urls,
                            site_name,
                            site_description,
                            status_container,
                            use_puppeteer=use_puppeteer,
                            use_llm=use_llm and api_key is not None,
                            llm_model=llm_model,
                            api_key=api_key
                        )

                    status_container.success("LLMS.txt generated successfully!")

                    # Display the generated content
                    st.subheader("Generated LLMS.txt")
                    st.text_area("Content", llms_txt_content, height=400)

                    # Provide download link
                    st.markdown(get_download_link(llms_txt_content), unsafe_allow_html=True)

                    # Usage instructions
                    st.info("### How to use your llms.txt file\n\n"
                           "1. Download the generated file\n"
                           "2. Upload it to your website's root directory\n"
                           "3. Make sure it's accessible at https://yourdomain.com/llms.txt\n"
                           "4. Verify it with the [llms.txt validator](https://llmstxt.org/validator)")

                    # Display enhanced stats
                    st.subheader("Statistics")
                    col_stats1, col_stats2, col_stats3 = st.columns(3)

                    with col_stats1:
                        st.metric("Total URLs", len(urls))

                    with col_stats2:
                        if use_puppeteer:
                            st.metric("JavaScript Rendering", "✅ Enabled")
                        else:
                            st.metric("JavaScript Rendering", "❌ Disabled")

                    with col_stats3:
                        if use_llm and api_key:
                            st.metric("AI Descriptions", "✅ Enabled")
                        else:
                            st.metric("AI Descriptions", "❌ Disabled")
    
    with tab2:
        st.subheader("🔍 Check LLM Crawler Accessibility")
        st.markdown("""
        This tool helps you check if various LLM crawlers can access your website. It will:
        - Check your robots.txt file for any blocked crawlers
        - Test accessibility for 24 different LLM crawlers
        - Show detailed results for each crawler
        """)
        
        domain = st.text_input("Enter your domain (e.g., example.com)", 
                             placeholder="example.com",
                             help="Enter your domain without http:// or https://")
        
        if st.button("Check Crawler Accessibility", 
                    disabled=not domain.strip(),
                    type="primary",
                    help="Click to check if LLM crawlers can access your site"):
            with st.spinner("Checking crawler accessibility..."):
                blocked_crawlers = check_llm_crawler_accessibility(domain)
                display_crawler_results(blocked_crawlers)

    # Add sidebar with additional information
    with st.sidebar:
        st.header("LLMS.txt Generator")
        st.markdown("This tool generates an `llms.txt` file according to the [AnswerDotAI specification](https://github.com/AnswerDotAI/llms-txt).")

        st.subheader("🚀 New Features")
        st.markdown("""
        - **JavaScript Rendering**: Use Puppeteer to render dynamic content
        - **AI Descriptions**: Generate intelligent descriptions using OpenRouter
        - **Main Content Extraction**: Focus on primary content, exclude headers/footers
        - **Enhanced Processing**: Better handling of modern web pages
        """)

        st.subheader("Benefits of llms.txt")
        st.markdown("""
        - 🤖 Helps AI models understand your website
        - 📚 Organizes your content for better discoverability
        - 🔍 Improves responses from AI assistants about your content
        - 🚀 Future-proofs your website for AI interactions
        """)

        st.subheader("Setup Guide")
        with st.expander("OpenRouter API Setup"):
            st.markdown("""
            1. Visit [OpenRouter](https://openrouter.ai/keys)
            2. Create an account and get your API key
            3. Enter the key in the AI configuration section
            4. Choose your preferred model
            5. Enable AI descriptions for better results
            """)

        st.subheader("Resources")
        st.markdown("""
        - [Official llms.txt Specification](https://llmstxt.org/)
        - [AnswerDotAI Repository](https://github.com/AnswerDotAI/llms-txt)
        - [OpenRouter API](https://openrouter.ai/)
        """)

        st.markdown("---")
        st.caption("© 2025 LLMS.txt Generator | Adnan Akram")

if __name__ == "__main__":
    main()
