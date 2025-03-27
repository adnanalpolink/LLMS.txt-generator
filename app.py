import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import base64
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import concurrent.futures
import time

st.set_page_config(page_title="LLMS.txt Generator", page_icon="📄", layout="wide")

def extract_urls_from_sitemap(sitemap_url):
    try:
        response = requests.get(sitemap_url, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        ns_map = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        urls = []
        
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('.//sm:sitemap', ns_map):
                loc = sitemap.find('./sm:loc', ns_map)
                if loc is not None and loc.text:
                    child_urls = extract_urls_from_sitemap(loc.text)
                    urls.extend(child_urls)
        else:
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
        
        possible_url_columns = [col for col in df.columns if any(url_key in col.lower() for url_key in ['url', 'link', 'href', 'path'])]
        
        if possible_url_columns:
            url_column = possible_url_columns[0]
            urls = df[url_column].tolist()
            urls = [url for url in urls if isinstance(url, str) and url.strip().startswith(('http://', 'https://'))]
            return urls
        else:
            first_col = df.iloc[:, 0]
            urls = first_col.tolist()
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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""

def extract_title_and_description(html_content, url=""):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        title = soup.title.string if soup.title else ""
        title = title.strip() if title else ""
        
        if not title and url:
            path = urlparse(url).path
            title = path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ').title()
            if not title:
                title = urlparse(url).netloc
        
        description = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc.get("content").strip()
        
        if not description:
            first_p = soup.find('p')
            if first_p:
                description = first_p.get_text().strip()
                if len(description) > 150:
                    description = description[:147] + "..."
        
        return title, description
    except Exception:
        return f"Page at {url.split('/')[-1]}", "Resource information"

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
        
        if any(keyword in path for keyword in ['/docs/', '/documentation/', '/doc/', '/manual/']):
            categorized["docs"].append(url)
        elif any(keyword in path for keyword in ['/example/', '/examples/', '/demo/', '/demos/', '/sample/']):
            categorized["examples"].append(url)
        elif any(keyword in path for keyword in ['/api/', '/apis/', '/reference/', '/schema/']):
            categorized["api"].append(url)
        elif any(keyword in path for keyword in ['/guide/', '/guides/', '/tutorial/', '/tutorials/', '/how-to/']):
            categorized["guides"].append(url)
        else:
            categorized["other"].append(url)
    
    return categorized

def process_url(url):
    page_html = get_page_content(url)
    title, desc = extract_title_and_description(page_html, url)
    title = title if title else url.split('/')[-1]
    desc = desc if desc else "Resource information"
    return title, desc, url

def generate_llms_txt(urls, site_name, site_description):
    if not urls:
        return "No valid URLs provided."
    
    base_url = urlparse(urls[0]).netloc
    
    if not site_name:
        site_name = base_url.split('.')[-2].capitalize() if len(base_url.split('.')) > 1 else base_url
    
    if not site_description:
        site_description = f"Information about {site_name}"
    
    categorized = categorize_urls(urls)
    content = []
    content.append(f"# {site_name}")
    content.append(f"> {site_description}")
    content.append("")
    
    sections_added = 0
    max_urls = 10
    
    categories = [
        {"key": "docs", "title": "Documentation", "default_desc": "Documentation resource"},
        {"key": "api", "title": "API Reference", "default_desc": "API documentation"},
        {"key": "examples", "title": "Examples", "default_desc": "Example or demo"},
        {"key": "guides", "title": "Guides & Tutorials", "default_desc": "Guide or tutorial"}
    ]
    
    for config in categories:
        key = config["key"]
        if categorized[key]:
            content.append(f"## {config['title']}")
            
            results = []
            for url in categorized[key][:max_urls]:
                page_html = get_page_content(url)
                title, desc = extract_title_and_description(page_html, url)
                title = title if title else url.split('/')[-1]
                desc = desc if desc else config["default_desc"]
                results.append(f"- [{title}]({url}): {desc}")
            
            content.extend(results)
            content.append("")
            sections_added += 1
    
    # General resources section if needed
    if sections_added == 0 or categorized["other"]:
        content.append("## Resources")
        urls_to_process = categorized["other"] if sections_added > 0 else urls
        
        results = []
        for url in urls_to_process[:20 if sections_added == 0 else max_urls]:
            page_html = get_page_content(url)
            title, desc = extract_title_and_description(page_html, url)
            title = title if title else url.split('/')[-1]
            desc = desc if desc else "Resource"
            results.append(f"- [{title}]({url}): {desc}")
        
        content.extend(results)
        content.append("")
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    content.append(f"<!-- Generated by LLMS.txt Generator on {now} -->")
    
    return "\n".join(content)

def get_download_link(content, filename="llms.txt"):
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}" style="display:inline-block;padding:0.5em 1em;background-color:#1565C0;color:white;text-decoration:none;border-radius:4px;margin-top:1em;">Download {filename}</a>'
    return href

def main():
    st.title("🤖 LLMS.txt Generator")
    
    with st.expander("About LLMS.txt"):
        st.markdown("""
        The `llms.txt` file is a standard proposed by [Answer.AI](https://github.com/AnswerDotAI/llms-txt) to help Large Language Models (LLMs) better understand and use website content.
        
        Similar to how `robots.txt` provides directives to search engines, `llms.txt` offers structured information to LLMs about your website's most important content, documentation, and resources.
        """)
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Website Information")
        site_name = st.text_input("Website Name", placeholder="My Website")
        site_description = st.text_area("Website Description", placeholder="A brief description of what your website is about", height=100)
    
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
            if input_type == "Sitemap URL":
                urls = extract_urls_from_sitemap(sitemap_url)
            else:
                urls = extract_urls_from_csv(uploaded_file)
            
            if not urls:
                st.error("No valid URLs found. Please check your input.")
            else:
                st.success(f"Found {len(urls)} URLs.")
                
                with st.spinner("Generating LLMS.txt..."):
                    llms_txt_content = generate_llms_txt(urls, site_name, site_description)
                
                st.subheader("Generated LLMS.txt")
                st.text_area("Content", llms_txt_content, height=400)
                
                st.markdown(get_download_link(llms_txt_content), unsafe_allow_html=True)
                
                st.info("### How to use your llms.txt file\n\n"
                       "1. Download the generated file\n"
                       "2. Upload it to your website's root directory\n"
                       "3. Make sure it's accessible at https://yourdomain.com/llms.txt\n"
                       "4. Verify it works by visiting the URL directly")
                
                # Display stats
                st.subheader("Statistics")
                col_stats1, col_stats2 = st.columns(2)
                
                categorized = categorize_urls(urls)
                
                with col_stats1:
                    st.metric("Total URLs Processed", len(urls))
                    st.metric("Documentation URLs", len(categorized["docs"]))
                    st.metric("API Reference URLs", len(categorized["api"]))
                
                with col_stats2:
                    st.metric("Example URLs", len(categorized["examples"]))
                    st.metric("Guide URLs", len(categorized["guides"]))
                    st.metric("Other URLs", len(categorized["other"]))

    with st.sidebar:
        st.header("LLMS.txt Generator")
        st.markdown("This tool generates an `llms.txt` file according to the [AnswerDotAI specification](https://github.com/AnswerDotAI/llms-txt).")
        
        st.markdown("""
        ### Benefits of llms.txt
        - 🤖 Helps AI models understand your website
        - 📚 Organizes your content for better discoverability
        - 🔍 Improves responses from AI assistants about your content
        """)

if __name__ == "__main__":
    main()
