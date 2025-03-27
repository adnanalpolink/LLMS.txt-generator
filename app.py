import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import re
import io
import base64
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time

st.set_page_config(
    page_title="LLMS.txt Generator",
    page_icon="📄",
    layout="wide"
)

def extract_urls_from_sitemap(sitemap_url):
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
            for sitemap in root.findall('.//sm:sitemap', ns_map):
                loc = sitemap.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    # Recursively process each sitemap
                    child_urls = extract_urls_from_sitemap(loc.text)
                    urls.extend(child_urls)
        else:
            # Regular sitemap
            for url in root.findall('.//sm:url', ns_map):
                loc = url.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    urls.append(loc.text)
        
        return urls
    except Exception as e:
        st.error(f"Error processing sitemap: {str(e)}")
        return []

def extract_urls_from_csv(csv_file):
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
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.warning(f"Could not fetch {url}: {str(e)}")
        return ""

def extract_title_and_description(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get title
        title = soup.title.string if soup.title else ""
        title = title.strip() if title else ""
        
        # Get meta description
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc.get("content").strip()
        
        return title, description
    except Exception as e:
        return "", ""

def categorize_urls(urls):
    categorized = {
        "docs": [],
        "examples": [],
        "api": [],
        "guides": [],
        "other": []
    }
    
    for url in urls:
        path = urlparse(url).path.lower()
        
        if any(keyword in path for keyword in ['/docs/', '/documentation/', '/doc/']):
            categorized["docs"].append(url)
        elif any(keyword in path for keyword in ['/example/', '/examples/', '/demo/', '/demos/']):
            categorized["examples"].append(url)
        elif any(keyword in path for keyword in ['/api/', '/apis/', '/reference/']):
            categorized["api"].append(url)
        elif any(keyword in path for keyword in ['/guide/', '/guides/', '/tutorial/', '/tutorials/']):
            categorized["guides"].append(url)
        else:
            categorized["other"].append(url)
    
    return categorized

def generate_llms_txt(urls, site_name, site_description):
    if not urls:
        return "No valid URLs provided."
    
    # Get the base URL from the first URL
    base_url = urlparse(urls[0]).netloc
    
    # Categorize URLs
    categorized = categorize_urls(urls)
    
    # Start building the llms.txt content
    content = []
    
    # Add header
    content.append(f"# {site_name}")
    content.append(f"> {site_description}")
    content.append("")
    
    # Process each category
    sections_added = 0
    
    # Docs section
    if categorized["docs"]:
        content.append("## Documentation")
        for url in categorized["docs"][:10]:  # Limit to 10 entries per section
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "Documentation resource"
            content.append(f"- [{title}]({url}): {desc}")
        content.append("")
        sections_added += 1
    
    # API section
    if categorized["api"]:
        content.append("## API Reference")
        for url in categorized["api"][:10]:
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "API documentation"
            content.append(f"- [{title}]({url}): {desc}")
        content.append("")
        sections_added += 1
    
    # Examples section
    if categorized["examples"]:
        content.append("## Examples")
        for url in categorized["examples"][:10]:
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "Example or demo"
            content.append(f"- [{title}]({url}): {desc}")
        content.append("")
        sections_added += 1
    
    # Guides section
    if categorized["guides"]:
        content.append("## Guides & Tutorials")
        for url in categorized["guides"][:10]:
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "Guide or tutorial"
            content.append(f"- [{title}]({url}): {desc}")
        content.append("")
        sections_added += 1
    
    # If no specific sections were added or there are other URLs, add a general resources section
    if sections_added == 0 or categorized["other"]:
        content.append("## Resources")
        urls_to_process = categorized["other"] if sections_added > 0 else urls
        for url in urls_to_process[:20]:  # Process more if this is the only section
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "Resource"
            content.append(f"- [{title}]({url}): {desc}")
        content.append("")
    
    return "\n".join(content)

def get_download_link(content, filename="llms.txt"):
    """Generate a download link for the text content"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">Download {filename}</a>'
    return href

def main():
    st.title("LLMS.txt Generator")
    st.markdown("""
    This app generates an `llms.txt` file for your website based on the [Answer.AI specification](https://github.com/AnswerDotAI/llms-txt).
    You can provide either an XML sitemap URL or upload a CSV file containing URLs.
    """)
    
    col1, col2 = st.columns(2)
    
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
    
    if st.button("Generate LLMS.txt", disabled=not input_ready):
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
                
                # Process a sample of URLs for preview
                with st.status("Generating LLMS.txt...") as status:
                    progress_bar = st.progress(0)
                    
                    # Create a sample of URLs for preview (up to 50)
                    sample_size = min(50, len(urls))
                    sample_urls = urls[:sample_size]
                    
                    # Update progress as we process URLs
                    for i, _ in enumerate(sample_urls):
                        time.sleep(0.05)  # Simulate processing time
                        progress_bar.progress((i + 1) / sample_size)
                    
                    # Generate the llms.txt content
                    llms_txt_content = generate_llms_txt(urls, site_name, site_description)
                    status.update(label="LLMS.txt generated successfully!", state="complete")
                
                # Display the generated content
                st.subheader("Generated LLMS.txt")
                st.text_area("Content", llms_txt_content, height=400)
                
                # Provide download link
                st.markdown(get_download_link(llms_txt_content), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
