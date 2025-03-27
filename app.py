import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
import io
import base64
import os
import time
import logging
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('llms_generator')

# Get environment variables with defaults
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 10))
MAX_URLS_PER_SECTION = int(os.getenv('MAX_URLS_PER_SECTION', 10))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 5))

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
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stProgress > div > div > div {
        background-color: #1565C0;
    }
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
    .download-btn:hover {
        background-color: #0D47A1;
    }
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def extract_urls_from_sitemap(sitemap_url):
    """Extract URLs from an XML sitemap, including sitemap indexes."""
    try:
        response = requests.get(sitemap_url, timeout=REQUEST_TIMEOUT)
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
            logger.info(f"Found sitemap index at {sitemap_url}")
            for sitemap in root.findall('.//sm:sitemap', ns_map):
                loc = sitemap.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    # Recursively process each sitemap
                    child_urls = extract_urls_from_sitemap(loc.text)
                    urls.extend(child_urls)
        else:
            # Regular sitemap
            logger.info(f"Processing regular sitemap at {sitemap_url}")
            for url in root.findall('.//sm:url', ns_map):
                loc = url.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    urls.append(loc.text)
        
        return urls
    except Exception as e:
        logger.error(f"Error processing sitemap {sitemap_url}: {str(e)}")
        st.error(f"Error processing sitemap: {str(e)}")
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
        logger.error(f"Error processing CSV: {str(e)}")
        st.error(f"Error processing CSV: {str(e)}")
        return []

def get_page_content(url):
    """Fetch content from a URL with error handling."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch {url}: {str(e)}")
        return ""

def extract_title_and_description(html_content, url=""):
    """Extract title and meta description from HTML content."""
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
    except Exception as e:
        logger.error(f"Error extracting content: {str(e)}")
        return f"Page at {url.split('/')[-1]}", "Resource information"

def categorize_urls(urls):
    """Categorize URLs into sections based on their path."""
    categorized = {
        "docs": [],
        "examples": [],
        "api": [],
        "guides": [],
        "other": []
    }
    
    for url in urls:
        path = urlparse(url).path.lower()
        
        if any(keyword in path for keyword in ['/docs/', '/documentation/', '/doc/', '/manual/']):
            categorized["docs"].append(url)
        elif any(keyword in path for keyword in ['/example/', '/examples/', '/demo/', '/demos/', '/sample/', '/samples/']):
            categorized["examples"].append(url)
        elif any(keyword in path for keyword in ['/api/', '/apis/', '/reference/', '/schema/', '/endpoint/']):
            categorized["api"].append(url)
        elif any(keyword in path for keyword in ['/guide/', '/guides/', '/tutorial/', '/tutorials/', '/how-to/', '/learn/']):
            categorized["guides"].append(url)
        else:
            categorized["other"].append(url)
    
    return categorized

def process_url(url):
    """Process a single URL to get title and description."""
    page_html = get_page_content(url)
    title, desc = extract_title_and_description(page_html, url)
    title = title if title else url.split('/')[-1]
    desc = desc if desc else "Resource information"
    return title, desc, url

def generate_llms_txt(urls, site_name, site_description, progress_callback=None):
    """Generate the llms.txt content from a list of URLs."""
    if not urls:
        return "No valid URLs provided."
    
    # Get the base URL from the first URL
    base_url = urlparse(urls[0]).netloc
    
    # Add protocol if missing in site name
    if not site_name:
        site_name = base_url.split('.')[-2].capitalize() if len(base_url.split('.')) > 1 else base_url
    
    # Categorize URLs
    categorized = categorize_urls(urls)
    
    # Start building the llms.txt content
    content = []
    
    # Add header
    content.append(f"# {site_name}")
    content.append(f"> {site_description}")
    content.append("")
    
    # Process each category with parallel processing
    sections_added = 0
    processed_count = 0
    total_to_process = sum(min(len(categorized[cat]), MAX_URLS_PER_SECTION) for cat in categorized)
    
    category_configs = [
        {"key": "docs", "title": "Documentation", "default_desc": "Documentation resource"},
        {"key": "api", "title": "API Reference", "default_desc": "API documentation"},
        {"key": "examples", "title": "Examples", "default_desc": "Example or demo"},
        {"key": "guides", "title": "Guides & Tutorials", "default_desc": "Guide or tutorial"}
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for config in category_configs:
            cat_key = config["key"]
            if categorized[cat_key]:
                content.append(f"## {config['title']}")
                
                # Process URLs in this category
                futures = {executor.submit(process_url, url): url for url in categorized[cat_key][:MAX_URLS_PER_SECTION]}
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        title, desc, url = future.result()
                        # Append to content
                        content.append(f"- [{title}]({url}): {desc}")
                        # Update progress
                        processed_count += 1
                        if progress_callback:
                            progress_callback(processed_count / total_to_process)
                    except Exception as e:
                        url = futures[future]
                        logger.error(f"Error processing {url}: {str(e)}")
                        # Add with minimal info
                        path = urlparse(url).path
                        filename = os.path.basename(path) if path else "resource"
                        title = filename.replace('-', ' ').replace('_', ' ').title()
                        content.append(f"- [{title}]({url}): {config['default_desc']}")
                        processed_count += 1
                        if progress_callback:
                            progress_callback(processed_count / total_to_process)
                
                content.append("")
                sections_added += 1
    
    # If no specific sections were added or there are other URLs, add a general resources section
    if sections_added == 0 or categorized["other"]:
        content.append("## Resources")
        urls_to_process = categorized["other"] if sections_added > 0 else urls
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Process up to 20 URLs if this is the only section
            limit = 20 if sections_added == 0 else MAX_URLS_PER_SECTION
            futures = {executor.submit(process_url, url): url for url in urls_to_process[:limit]}
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    title, desc, url = future.result()
                    content.append(f"- [{title}]({url}): {desc}")
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count / total_to_process)
                except Exception as e:
                    url = futures[future]
                    logger.error(f"Error processing {url}: {str(e)}")
                    path = urlparse(url).path
                    filename = os.path.basename(path) if path else "resource"
                    title = filename.replace('-', ' ').replace('_', ' ').title()
                    content.append(f"- [{title}]({url}): Resource")
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count / total_to_process)
        
        content.append("")
    
    # Add timestamp at the end
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content.append(f"<!-- Generated by LLMS.txt Generator on {now} -->")
    
    return "\n".join(content)

def get_download_link(content, filename="llms.txt"):
    """Generate a download link for the text content."""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" class="download-btn">Download {filename}</a>'
    return href

def main():
    """Main application function."""
    st.title("🤖 LLMS.txt Generator")
    
    with st.expander("About LLMS.txt", expanded=False):
        st.markdown("""
        The `llms.txt` file is a standard proposed by [Answer.AI](https://github.com/AnswerDotAI/llms-txt) to help Large Language Models (LLMs) better understand and use website content. 
        
        Similar to how `robots.txt` provides directives to search engines, `llms.txt` offers structured information to LLMs about your website's most important content, documentation, and resources.
        
        This tool helps you generate a well-formatted `llms.txt` file for your website by analyzing your sitemap or a list of URLs.
        """)
    
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
                
                # Process URLs for preview
                with st.status("Generating LLMS.txt...") as status:
                    progress_bar = st.progress(0)
                    
                    def update_progress(progress):
                        progress_bar.progress(progress)
                    
                    # Generate the llms.txt content
                    llms_txt_content = generate_llms_txt(urls, site_name, site_description, update_progress)
                    status.update(label="LLMS.txt generated successfully!", state="complete")
                
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
                
                # Display stats
                st.subheader("Statistics")
                col_stats1, col_stats2 = st.columns(2)
                
                # Calculate statistics
                categorized = categorize_urls(urls)
                
                with col_stats1:
                    st.metric("Total URLs Processed", len(urls))
                    st.metric("Documentation URLs", len(categorized["docs"]))
                    st.metric("API Reference URLs", len(categorized["api"]))
                
                with col_stats2:
                    st.metric("Example URLs", len(categorized["examples"]))
                    st.metric("Guide URLs", len(categorized["guides"]))
                    st.metric("Other URLs", len(categorized["other"]))

    # Add sidebar with additional information
    with st.sidebar:
        st.header("LLMS.txt Generator")
        st.markdown("This tool generates an `llms.txt` file according to the [AnswerDotAI specification](https://github.com/AnswerDotAI/llms-txt).")
        
        st.subheader("Benefits of llms.txt")
        st.markdown("""
        - 🤖 Helps AI models understand your website
        - 📚 Organizes your content for better discoverability
        - 🔍 Improves responses from AI assistants about your content
        - 🚀 Future-proofs your website for AI interactions
        """)
        
        st.subheader("Resources")
        st.markdown("""
        - [Official llms.txt Specification](https://llmstxt.org/)
        - [AnswerDotAI Repository](https://github.com/AnswerDotAI/llms-txt)
        - [llms.txt Generator on GitHub](https://github.com/yourusername/llms-txt-generator)
        """)
        
        st.markdown("---")
        st.caption("© 2025 LLMS.txt Generator")

if __name__ == "__main__":
    main()
