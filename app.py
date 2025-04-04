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

def get_page_content(url):
    """Fetch content from a URL with error handling."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException:
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
    except Exception:
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
        # Also check the full URL for categorization
        full_url = url.lower()
        
        # Documentation patterns
        if any(keyword in full_url for keyword in ['doc', 'documentation', 'manual', 'faq', 'help', 'support', 'knowledge']):
            categorized["docs"].append(url)
        # Example patterns
        elif any(keyword in full_url for keyword in ['example', 'demo', 'sample', 'showcase', 'trial']):
            categorized["examples"].append(url)
        # API patterns
        elif any(keyword in full_url for keyword in ['api', 'reference', 'schema', 'endpoint', 'swagger', 'openapi', 'graphql']):
            categorized["api"].append(url)
        # Guide patterns
        elif any(keyword in full_url for keyword in ['guide', 'tutorial', 'learn', 'how-to', 'howto', 'getting-started', 'quickstart']):
            categorized["guides"].append(url)
        else:
            categorized["other"].append(url)
    
    return categorized

def process_url(url, default_desc="Resource"):
    """Process a single URL to get title and description."""
    page_html = get_page_content(url)
    title, desc = extract_title_and_description(page_html, url)
    title = title if title else url.split('/')[-1]
    desc = desc if desc else default_desc
    return title, desc, url

def batch_process_urls(urls, category_desc="Resource", max_workers=5):
    """Process multiple URLs in parallel."""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(process_url, url, category_desc): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                title, desc, _ = future.result()
                results.append((title, desc, url))
            except Exception:
                # Fallback for errors
                path = urlparse(url).path
                filename = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
                title = filename if filename else url.split('/')[-1]
                results.append((title, category_desc, url))
    
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

def generate_llms_txt(urls, site_name, site_description, status_placeholder=None):
    """Generate the llms.txt content from a list of URLs."""
    if not urls:
        return "No valid URLs provided."
    
    # Generate status updates
    if status_placeholder:
        status_placeholder.write("Processing URLs...")
    
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
    
    # Add Docs section
    content.append("## Docs")
    content.append("")
    
    # Process all URLs
    if status_placeholder:
        status_placeholder.write("Processing URLs...")
    
    processed_urls = batch_process_urls(urls, "Resource information")
    
    # Add all URLs to content
    for title, desc, url in processed_urls:
        content.append(f"- [{title}]({url}): {clean_description(desc)}")
    
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
                    
                    # Process URLs and generate llms.txt
                    status_container = st.empty()
                    with st.spinner("Generating LLMS.txt..."):
                        llms_txt_content = generate_llms_txt(urls, site_name, site_description, status_container)
                    
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
                    
                    # Display simple stats
                    st.subheader("Statistics")
                    st.metric("Total URLs", len(urls))
    
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
        """)
        
        st.markdown("---")
        st.caption("© 2025 LLMS.txt Generator | Adnan Akram")

if __name__ == "__main__":
    main()
