"""
HTML Preprocessing Module

Cleans and preprocesses HTML content before sending to LLM for article extraction.
Significantly reduces token usage and improves processing efficiency.
"""

import re
from typing import Optional, List, Dict, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def preprocess_html_for_llm(html_content: str, max_length: int = 8000, preprocessed_format: str = 'markdown') -> str:
    """
    Preprocess HTML content for LLM consumption.

    Args:
        html_content: Raw HTML content
        max_length: Maximum length of processed content
        preprocessed_format: Output format - 'markdown', 'simple_tags', or 'urls'

    Returns:
        Clean, structured text suitable for LLM processing
    """
    if not html_content:
        return ""

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Process based on requested format
    if preprocessed_format == 'simple_tags':
        # Extract and clean HTML content while preserving key tags
        clean_content = _extract_clean_html_with_tags(soup)
        structured_content = _structure_html_content(clean_content)
    elif preprocessed_format == 'urls':
        # Extract and format all URLs from the HTML
        structured_content = _format_urls_for_llm(html_content)
    else:
        # Default markdown format
        # Extract and preserve link information before processing
        link_info = _extract_link_information(soup)

        # Remove unwanted elements that add noise
        _remove_noise_elements(soup)

        clean_text = _extract_clean_text(soup)
        structured_content = _structure_content(clean_text)

        # Integrate link information into the structured content
        structured_content = _integrate_link_info(structured_content, link_info)

    # Truncate if too long
    if len(structured_content) > max_length:
        structured_content = structured_content[:max_length] + \
            "\n\n[Content truncated...]"

    return structured_content.strip()


def _remove_noise_elements(soup: BeautifulSoup) -> None:
    """Remove elements that add noise but no value for article extraction."""
    # Elements to completely remove
    noise_selectors = [
        'script', 'style', 'noscript', 'iframe', 'embed', 'object',
        'nav', 'header', 'footer', 'aside', '.sidebar', '.navigation',
        '.advertisement', '.ads', '.social-share', '.comments',
        '.cookie-banner', '.popup', '.modal',
        'svg', 'canvas', 'video', 'audio',
        '.hidden', '[style*="display:none"]', '[style*="display: none"]'
    ]

    for selector in noise_selectors:
        try:
            # Handle both tag names and CSS selectors
            if selector.startswith('.'):
                elements = soup.select(selector)
            else:
                elements = soup.find_all(selector)

            for element in elements:
                element.decompose()
        except Exception:
            # Skip problematic selectors
            continue

    # Remove elements with very short text (likely navigation items)
    for tag in soup.find_all():
        if tag.name in ['a', 'span', 'div'] and len(tag.get_text(strip=True)) < 3:
            tag.decompose()


def _convert_html_to_markdown(soup: BeautifulSoup) -> str:
    """
    Convert HTML structure to markdown format while preserving content hierarchy.

    Args:
        soup: BeautifulSoup object with cleaned HTML

    Returns:
        Markdown formatted text
    """
    markdown_parts = []

    def process_element(element, indent_level=0):
        """Recursively process HTML elements and convert to markdown."""
        if element.name is None:
            # Text node
            text = element.string
            if text and text.strip():
                return text.strip()
            return ""

        # Handle different HTML tags
        tag_name = element.name.lower()
        content = ""

        # Process children first
        for child in element.children:
            child_content = process_element(child, indent_level)
            if child_content:
                content += child_content + " "

        content = content.strip()

        if not content:
            return ""

        # Convert tags to markdown
        if tag_name in ['h1']:
            return f"\n# {content}\n\n"
        elif tag_name in ['h2']:
            return f"\n## {content}\n\n"
        elif tag_name in ['h3']:
            return f"\n### {content}\n\n"
        elif tag_name in ['h4']:
            return f"\n#### {content}\n\n"
        elif tag_name in ['h5']:
            return f"\n##### {content}\n\n"
        elif tag_name in ['h6']:
            return f"\n###### {content}\n\n"
        elif tag_name in ['p']:
            return f"{content}\n\n"
        elif tag_name in ['br']:
            return "\n"
        elif tag_name in ['strong', 'b']:
            return f"**{content}**"
        elif tag_name in ['em', 'i']:
            return f"*{content}*"
        elif tag_name in ['ul']:
            return f"\n{content}\n"
        elif tag_name in ['ol']:
            return f"\n{content}\n"
        elif tag_name in ['li']:
            marker = "  " * indent_level + "- "
            return f"{marker}{content}\n"
        elif tag_name in ['blockquote']:
            lines = content.split('\n')
            quoted_lines = [f"> {line}" for line in lines if line.strip()]
            return "\n".join(quoted_lines) + "\n\n"
        elif tag_name in ['div', 'section', 'article', 'main', 'aside', 'header', 'footer']:
            # For container elements, just return their content
            return content + "\n\n"
        elif tag_name in ['span']:
            # For spans, just return content (they're usually for styling)
            return content
        else:
            # For unknown tags, return content as-is
            return content + " "

    # Process the entire document body or the soup itself
    if soup.body:
        result = process_element(soup.body)
    else:
        result = process_element(soup)

    return result.strip()


def _extract_clean_text(soup: BeautifulSoup) -> str:
    """Extract clean, readable text from the processed HTML with markdown formatting."""
    # Convert HTML structure to markdown
    markdown_text = _convert_html_to_markdown(soup)

    # Clean up whitespace
    # Remove excessive newlines
    markdown_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown_text)

    # Remove excessive spaces
    markdown_text = re.sub(r' +', ' ', markdown_text)

    # Remove lines that are too short (likely fragments)
    lines = markdown_text.split('\n')
    filtered_lines = []

    for line in lines:
        line = line.strip()
        # Keep lines that have meaningful content
        if len(line) > 10 or (line and not line.replace('.', '').replace('!', '').replace('?', '').islower()):
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def _structure_content(text: str) -> str:
    """Structure the content to make it more suitable for LLM processing."""
    lines = text.split('\n')

    # Identify potential headings (short lines that might be titles)
    structured_lines = []
    headings = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Potential heading detection (short lines, all caps, etc.)
        if _is_potential_heading(line):
            headings.append(line)
            structured_lines.append(f"## {line}")
        else:
            structured_lines.append(line)

    # Add content summary at the beginning
    content_summary = f"Content Summary: {len(lines)} paragraphs, {len(headings)} potential headings, {len(text)} characters"

    structured_content = [content_summary, ""] + structured_lines

    return '\n'.join(structured_content)


def _extract_link_information(soup: BeautifulSoup) -> list:
    """
    Extract link information before processing.

    Args:
        soup: BeautifulSoup object

    Returns:
        List of dictionaries with link information
    """
    links = []
    for a_tag in soup.find_all('a', href=True):
        link_text = a_tag.get_text(strip=True)
        href = a_tag['href'].strip()

        # Skip empty links or very short text
        if not link_text or len(link_text) < 2:
            continue

        # Skip links that are just URLs or fragments
        if link_text.startswith('http') or link_text.startswith('#'):
            continue

        # Skip navigation-like links
        nav_keywords = ['home', 'about', 'contact',
                        'privacy', 'terms', 'menu', 'navigation']
        if any(keyword in link_text.lower() for keyword in nav_keywords):
            continue

        links.append({
            'text': link_text,
            'url': href,
            'full_text': f"{link_text} [URL: {href}]"
        })

    return links


def _integrate_link_info(text: str, link_info: list) -> str:
    """
    Integrate link information into the processed text.

    Args:
        text: Processed text content
        link_info: List of link information dictionaries

    Returns:
        Text with integrated link information
    """
    if not link_info:
        return text

    # Add a section with all links at the end
    link_section = "\n\n--- ARTICLE LINKS ---\n"

    for i, link in enumerate(link_info, 1):
        link_section += f"{i}. {link['full_text']}\n"

    # Also try to find and replace link text in the main content
    enhanced_text = text
    for link in link_info:
        # Replace occurrences of link text with URL-enhanced version
        # Only replace if the link text appears as a standalone line or with minimal context
        lines = enhanced_text.split('\n')
        updated_lines = []

        for line in lines:
            # If line matches link text exactly or is very similar, enhance it
            if link['text'].lower().strip() == line.lower().strip():
                updated_lines.append(link['full_text'])
            else:
                updated_lines.append(line)

        enhanced_text = '\n'.join(updated_lines)

    return enhanced_text + link_section


def _extract_clean_html_with_tags(soup: BeautifulSoup) -> str:
    """
    Extract HTML content while preserving key structural tags.

    Keeps headings (h1-h6), paragraphs (p), anchor tags (a), and div tags
    while removing unnecessary formatting and converting to clean HTML.

    Args:
        soup: BeautifulSoup object with cleaned HTML

    Returns:
        Clean HTML string with preserved structural tags
    """
    def process_element(element):
        """Recursively process HTML elements and preserve key tags."""
        if element.name is None:
            # Text node
            text = element.string
            if text and text.strip():
                return text.strip()
            return ""

        tag_name = element.name.lower()
        content = ""

        # Process children first
        for child in element.children:
            child_content = process_element(child)
            if child_content:
                if content:
                    content += " "
                content += child_content

        content = content.strip()

        if not content:
            return ""

        # Preserve key structural tags
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return f"<{tag_name}>{content}</{tag_name}>"
        elif tag_name == 'p':
            return f"<p>{content}</p>"
        elif tag_name == 'a' and element.get('href'):
            href = element['href']
            return f'<a href="{href}">{content}</a>'
        elif tag_name == 'div':
            # For divs, preserve if they contain meaningful content
            if len(content) > 20:  # Only keep substantial div content
                return f"<div>{content}</div>"
            else:
                return content  # Return just the content for small divs
        elif tag_name in ['strong', 'b']:
            return f"<strong>{content}</strong>"
        elif tag_name in ['em', 'i']:
            return f"<em>{content}</em>"
        elif tag_name == 'br':
            return "<br>"
        else:
            # For unknown or unwanted tags, return content only
            return content

    # Process the entire document body or the soup itself
    if soup.body:
        result = process_element(soup.body)
    else:
        result = process_element(soup)

    # Clean up the result
    # Remove excessive whitespace
    result = re.sub(r'\s+', ' ', result)
    # Fix spacing around tags
    result = re.sub(r'\s*<', '<', result)
    result = re.sub(r'>\s*', '> ', result)
    result = re.sub(r'\s*$', '', result)

    return result.strip()


def _structure_html_content(html_content: str) -> str:
    """
    Structure HTML content for better LLM processing.

    Args:
        html_content: Clean HTML content with preserved tags

    Returns:
        Structured HTML content with summary information
    """
    if not html_content:
        return ""

    # Parse the HTML to count elements
    soup = BeautifulSoup(html_content, 'html.parser')

    # Count different element types
    headings = len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
    paragraphs = len(soup.find_all('p'))
    links = len(soup.find_all('a'))
    divs = len(soup.find_all('div'))

    # Clean up the HTML content
    # Remove excessive whitespace between tags
    html_content = re.sub(r'>\s+<', '><', html_content)
    # Ensure proper spacing between elements
    html_content = re.sub(r'><([^/])', r'> <\1', html_content)
    # Remove multiple spaces
    html_content = re.sub(r' +', ' ', html_content)

    # Add content summary at the beginning
    content_summary = f"Content Summary: {paragraphs} paragraphs, {headings} headings, {links} links, {divs} content sections, {len(html_content)} characters"

    structured_content = [content_summary, "", html_content]

    return '\n'.join(structured_content)


def _is_potential_heading(line: str) -> bool:
    """Determine if a line is likely a heading."""
    line = line.strip()

    # Criteria for potential headings:
    # 1. Short length (likely titles)
    # 2. All caps or title case
    # 3. No punctuation at the end (except colon)
    # 4. Contains alphabetic characters

    if len(line) > 80 or len(line) < 3:
        return False

    if not any(c.isalpha() for c in line):
        return False

    # Check for ending punctuation (headings usually don't end with period)
    if line.endswith('.') and not line.endswith('...'):
        return False

    # Check if it's all caps or title case
    words = line.split()
    if len(words) <= 6:  # Headings are usually short
        caps_words = sum(1 for word in words if word.isupper()
                         and len(word) > 1)
        if caps_words / len(words) > 0.5:  # More than 50% capitalized words
            return True

    return False


def extract_all_urls_from_html(html_content: str, base_url: str = None,
                              include_fragments: bool = False,
                              include_duplicates: bool = False) -> Dict[str, List[Dict]]:
    """
    Extract all URLs from HTML content with comprehensive coverage.

    This function extracts URLs from various HTML elements including:
    - Anchor tags (a href)
    - Image sources (img src)
    - Script sources (script src)
    - Stylesheet links (link href)
    - Iframe sources (iframe src)
    - Form actions (form action)
    - Video/audio sources
    - Meta refresh URLs
    - CSS background images (from style attributes)
    - JavaScript URLs (onclick, etc.)

    Args:
        html_content: Raw HTML content to parse
        base_url: Base URL for resolving relative URLs (optional)
        include_fragments: Whether to include fragment URLs (#anchor)
        include_duplicates: Whether to include duplicate URLs

    Returns:
        Dictionary with categorized URL lists:
        {
            'anchors': [...],
            'images': [...],
            'scripts': [...],
            'stylesheets': [...],
            'iframes': [...],
            'forms': [...],
            'media': [...],
            'meta_redirects': [...],
            'css_images': [...],
            'javascript_urls': [...]
        }

        Each URL entry is a dict with:
        {
            'url': 'full URL',
            'original_url': 'original URL as found in HTML',
            'element': 'HTML element name',
            'attribute': 'attribute name',
            'text': 'associated text (for anchors)',
            'category': 'URL category',
            'is_external': bool,
            'domain': 'domain name',
            'file_extension': 'file extension if applicable'
        }
    """
    if not html_content:
        return {category: [] for category in _get_url_categories()}

    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract URLs from different element types
    url_data = {
        'anchors': _extract_anchor_urls(soup, base_url),
        'images': _extract_image_urls(soup, base_url),
        'scripts': _extract_script_urls(soup, base_url),
        'stylesheets': _extract_stylesheet_urls(soup, base_url),
        'iframes': _extract_iframe_urls(soup, base_url),
        'forms': _extract_form_urls(soup, base_url),
        'media': _extract_media_urls(soup, base_url),
        'meta_redirects': _extract_meta_redirect_urls(soup, base_url),
        'css_images': _extract_css_background_urls(soup, base_url),
        'javascript_urls': _extract_javascript_urls(soup, base_url)
    }

    # Filter fragments if requested
    if not include_fragments:
        for category in url_data:
            url_data[category] = [url for url in url_data[category]
                                if not url['original_url'].startswith('#')]

    # Remove duplicates if requested
    if not include_duplicates:
        for category in url_data:
            seen_urls = set()
            unique_urls = []
            for url in url_data[category]:
                url_key = url['url']
                if url_key not in seen_urls:
                    seen_urls.add(url_key)
                    unique_urls.append(url)
            url_data[category] = unique_urls

    return url_data


def _get_url_categories() -> List[str]:
    """Get list of URL categories."""
    return [
        'anchors', 'images', 'scripts', 'stylesheets', 'iframes',
        'forms', 'media', 'meta_redirects', 'css_images', 'javascript_urls'
    ]


def _extract_anchor_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from anchor tags."""
    urls = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href'].strip()
        if href:
            urls.append(_create_url_entry(
                url=_resolve_url(href, base_url),
                original_url=href,
                element='a',
                attribute='href',
                text=a_tag.get_text(strip=True, separator=' '),
                category='anchor'
            ))
    return urls


def _extract_image_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from image sources."""
    urls = []
    for img_tag in soup.find_all('img', src=True):
        src = img_tag['src'].strip()
        if src:
            urls.append(_create_url_entry(
                url=_resolve_url(src, base_url),
                original_url=src,
                element='img',
                attribute='src',
                text=img_tag.get('alt', ''),
                category='image'
            ))

    # Also check for data-src attributes (lazy loading)
    for img_tag in soup.find_all('img', {'data-src': True}):
        data_src = img_tag['data-src'].strip()
        if data_src:
            urls.append(_create_url_entry(
                url=_resolve_url(data_src, base_url),
                original_url=data_src,
                element='img',
                attribute='data-src',
                text=img_tag.get('alt', ''),
                category='image'
            ))
    return urls


def _extract_script_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from script sources."""
    urls = []
    for script_tag in soup.find_all('script', src=True):
        src = script_tag['src'].strip()
        if src:
            urls.append(_create_url_entry(
                url=_resolve_url(src, base_url),
                original_url=src,
                element='script',
                attribute='src',
                category='script'
            ))
    return urls


def _extract_stylesheet_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from stylesheet links."""
    urls = []
    for link_tag in soup.find_all('link', rel='stylesheet', href=True):
        href = link_tag['href'].strip()
        if href:
            urls.append(_create_url_entry(
                url=_resolve_url(href, base_url),
                original_url=href,
                element='link',
                attribute='href',
                category='stylesheet'
            ))
    return urls


def _extract_iframe_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from iframe sources."""
    urls = []
    for iframe_tag in soup.find_all('iframe', src=True):
        src = iframe_tag['src'].strip()
        if src:
            urls.append(_create_url_entry(
                url=_resolve_url(src, base_url),
                original_url=src,
                element='iframe',
                attribute='src',
                category='iframe'
            ))
    return urls


def _extract_form_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from form actions."""
    urls = []
    for form_tag in soup.find_all('form', action=True):
        action = form_tag['action'].strip()
        if action:
            urls.append(_create_url_entry(
                url=_resolve_url(action, base_url),
                original_url=action,
                element='form',
                attribute='action',
                category='form'
            ))
    return urls


def _extract_media_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from video/audio sources."""
    urls = []
    media_tags = ['video', 'audio', 'source']

    for tag_name in media_tags:
        for tag in soup.find_all(tag_name, src=True):
            src = tag['src'].strip()
            if src:
                urls.append(_create_url_entry(
                    url=_resolve_url(src, base_url),
                    original_url=src,
                    element=tag_name,
                    attribute='src',
                    category='media'
                ))
    return urls


def _extract_meta_redirect_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from meta refresh redirects."""
    urls = []
    for meta_tag in soup.find_all('meta', {'http-equiv': 'refresh'}):
        content = meta_tag.get('content', '')
        if content:
            # Extract URL from refresh content (format: "5; url=http://example.com")
            url_match = re.search(r'url\s*=\s*([^\s;]+)', content, re.IGNORECASE)
            if url_match:
                url = url_match.group(1).strip()
                if url:
                    urls.append(_create_url_entry(
                        url=_resolve_url(url, base_url),
                        original_url=url,
                        element='meta',
                        attribute='content',
                        category='meta_redirect'
                    ))
    return urls


def _extract_css_background_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from CSS background-image properties in style attributes."""
    urls = []
    for tag in soup.find_all(style=True):
        style_content = tag['style']
        # Find background-image URLs in CSS
        url_matches = re.findall(r'background-image\s*:\s*url\(["\']?([^"\']+)["\']?\)', style_content, re.IGNORECASE)
        for url in url_matches:
            if url:
                urls.append(_create_url_entry(
                    url=_resolve_url(url, base_url),
                    original_url=url,
                    element=tag.name,
                    attribute='style',
                    category='css_image'
                ))
    return urls


def _extract_javascript_urls(soup: BeautifulSoup, base_url: str = None) -> List[Dict]:
    """Extract URLs from JavaScript event handlers and attributes."""
    urls = []
    js_attributes = ['onclick', 'onload', 'onmouseover', 'onmouseout', 'href']

    for attr in js_attributes:
        for tag in soup.find_all(attrs={attr: True}):
            attr_value = tag[attr]
            if attr_value:
                # Extract URLs from JavaScript code
                url_matches = re.findall(r'["\']((?:https?://|//|/)[^"\']+)["\']', attr_value)
                for url in url_matches:
                    if url:
                        urls.append(_create_url_entry(
                            url=_resolve_url(url, base_url),
                            original_url=url,
                            element=tag.name,
                            attribute=attr,
                            category='javascript_url'
                        ))
    return urls


def _create_url_entry(url: str, original_url: str, element: str, attribute: str,
                     text: str = '', category: str = '') -> Dict:
    """Create a standardized URL entry dictionary."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    is_external = bool(domain and parsed_url.scheme in ['http', 'https'])

    # Extract file extension
    path_parts = parsed_url.path.split('.')
    file_extension = path_parts[-1].lower() if len(path_parts) > 1 else ''

    return {
        'url': url,
        'original_url': original_url,
        'element': element,
        'attribute': attribute,
        'text': text,
        'category': category,
        'is_external': is_external,
        'domain': domain,
        'file_extension': file_extension
    }


def _format_urls_for_llm(html_content: str, base_url: str = None) -> str:
    """
    Format extracted URLs for LLM consumption.
    Uses LLM to filter and return only blog/resource-related anchor links in compact markdown href format.

    Args:
        html_content: Raw HTML content to extract URLs from
        base_url: Base URL for resolving relative URLs (optional)

    Returns:
        Compact markdown-formatted anchor links for LLM processing
    """
    if not html_content:
        return "No HTML content provided for URL extraction."

    # Extract only anchor URLs from the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    anchor_urls = _extract_anchor_urls(soup, base_url)

    # Filter out fragment links (#anchors) and empty URLs
    valid_anchors = [url for url in anchor_urls if url['url'] and not url['original_url'].startswith('#')]

    if not valid_anchors:
        return "No anchor links found in the content."

    # Use LLM to intelligently filter blog/resource-related URLs
    from modules.llm_client import LLMClient
    try:
        # Create LLM client instance (verbose=False for html_processor)
        llm_client = LLMClient(verbose=False)
        filtered_anchors = llm_client.filter_blog_urls(valid_anchors)
    except Exception as e:
        print(f"LLM URL filtering failed: {e}, falling back to rule-based filtering")
        # Fallback to rule-based filtering if LLM fails
        filtered_anchors = []
        for url_info in valid_anchors:
            if _is_blog_resource_url(url_info):
                filtered_anchors.append(url_info)

    if not filtered_anchors:
        return "No blog or resource-related links found in the content."

    # Build compact output
    output_parts = []
    output_parts.append(f"BLOG/RESOURCE LINKS FOUND: {len(filtered_anchors)}")

    for url_info in filtered_anchors:
        # Parse and format the text with commas
        raw_text = url_info['text'].strip() if url_info['text'].strip() else url_info['url']
        formatted_text = _parse_and_format_link_text(raw_text)
        url = url_info['url']

        # Format as markdown link with comma-separated components
        output_parts.append(f"- [{formatted_text}]({url})")

    return '\n'.join(output_parts)


def _is_blog_resource_url(url_info: Dict) -> bool:
    """
    Determine if a URL is blog or resource-related using smart filtering.

    Uses multiple criteria:
    - URL patterns (blog, article, dates, etc.)
    - Text content analysis
    - Negative filtering (navigation, social media)

    Args:
        url_info: URL information dictionary from _create_url_entry

    Returns:
        True if URL appears to be blog/resource-related
    """
    url = url_info['url'].lower()
    original_url = url_info['original_url'].lower()
    text = url_info['text'].lower().strip() if url_info['text'] else ''
    domain = url_info['domain'].lower() if url_info['domain'] else ''

    # Scoring system: positive points for content, negative for navigation
    score = 0

    # === URL PATTERN ANALYSIS (High weight) ===

    # Date patterns (very inclusive - user specifically requested this)
    date_patterns = [
        r'/20\d{2}/',  # /2024/, /2023/, etc.
        r'/20\d{2}-\d{1,2}',  # /2024-01, /2024-12, etc.
        r'/20\d{2}-\d{1,2}-\d{1,2}',  # /2024-01-15, /2023-12-25, etc.
        r'/\d{1,2}-\d{1,2}-20\d{2}',  # /01-15-2024, /12-25-2023, etc.
        r'/\d{4}/\d{1,2}/\d{1,2}',  # /2024/01/15, /2023/12/25, etc.
        r'/news/20\d{2}',  # /news/2024, /news/2023, etc.
        r'/articles/20\d{2}',  # /articles/2024, /articles/2023, etc.
    ]

    for pattern in date_patterns:
        if re.search(pattern, original_url):
            score += 3  # High weight for date patterns

    # Blog/Resource patterns
    content_patterns = [
        r'/blog/', r'/article/', r'/post/', r'/news/', r'/resource/',
        r'/guide/', r'/tutorial/', r'/docs/', r'/help/', r'/learn/',
        r'/research/', r'/study/', r'/analysis/', r'/review/',
        r'/case-study/', r'/whitepaper/', r'/ebook/', r'/webinar/',
        r'/podcast/', r'/video/', r'/course/', r'/training/',
        r'/insight/', r'/report/', r'/update/', r'/announcement/'
    ]

    for pattern in content_patterns:
        if pattern in original_url:
            score += 2  # Good weight for content patterns

    # === TEXT CONTENT ANALYSIS ===

    # Content keywords in text
    content_keywords = [
        'guide', 'tutorial', 'how-to', 'tips', 'analysis', 'review',
        'case study', 'research', 'study', 'announcement', 'update',
        'breaking', 'latest', 'new', 'complete', 'comprehensive',
        'introduction', 'overview', 'deep dive', 'explained',
        'understanding', 'master', 'beginner', 'advanced'
    ]

    for keyword in content_keywords:
        if keyword in text:
            score += 1

    # Date keywords in text
    date_keywords = [
        '2024', '2023', '2025', 'january', 'february', 'march', 'april',
        'may', 'june', 'july', 'august', 'september', 'october',
        'november', 'december', 'q1', 'q2', 'q3', 'q4', 'quarter'
    ]

    for keyword in date_keywords:
        if keyword in text:
            score += 1

    # Long text (likely article titles)
    if len(text.split()) > 5:
        score += 1

    # === NEGATIVE FILTERING (Navigation, Social Media, Admin) ===

    # Navigation keywords
    nav_keywords = [
        'home', 'about', 'contact', 'about us', 'our team', 'careers',
        'jobs', 'locations', 'offices', 'support', 'help center',
        'faq', 'frequently asked questions', 'pricing', 'plans',
        'login', 'sign in', 'register', 'sign up', 'account',
        'profile', 'settings', 'dashboard', 'admin', 'administrator',
        'privacy', 'privacy policy', 'terms', 'terms of service',
        'cookie policy', 'legal', 'imprint', 'sitemap'
    ]

    for keyword in nav_keywords:
        if keyword in text or keyword in original_url:
            score -= 2

    # Social media domains
    social_domains = [
        'twitter.com', 'facebook.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'tiktok.com', 'snapchat.com', 'pinterest.com',
        'reddit.com', 'discord.com', 'telegram.org', 'whatsapp.com',
        'github.com'  # GitHub can be both - we'll be lenient
    ]

    if domain in social_domains and domain != 'github.com':
        score -= 3

    # Generic paths that are usually not content
    generic_paths = [
        '/', '/index', '/home', '/default', '/main', '/page',
        '/category', '/tag', '/author', '/search', '/archive',
        '/rss', '/feed', '/sitemap', '/robots.txt'
    ]

    for path in generic_paths:
        if original_url == path or original_url.endswith(path):
            score -= 2

    # === DECISION LOGIC ===

    # Require minimum score of 1 (inclusive approach)
    # This means even URLs with dates but no explicit content keywords will pass
    return score >= 1


def _parse_and_format_link_text(text: str) -> str:
    """
    Parse link text and format it with commas to separate components.

    Handles text like: "BlogMar 12, 202510 min readUnderstanding Agentic AI: What It Is and How to Build It SecurelyLuka Kamber"
    Converts to: "Blog, Mar 12, 2025, 10 min read, Understanding Agentic AI: What It Is and How to Build It Securely, Luka Kamber"

    Args:
        text: Raw link text to parse

    Returns:
        Formatted text with comma-separated components
    """
    if not text or not text.strip():
        return text

    text = text.strip()

    # If text is already formatted with commas, return as-is
    if ',' in text:
        return text

    # Common content types to look for
    content_types = ['Blog', 'Article', 'News', 'Tutorial', 'Guide', 'Video', 'Podcast', 'Case Study', 'Research']

    # Month abbreviations for date detection
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
              'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
              'September', 'October', 'November', 'December']

    components = []
    remaining_text = text

    # 1. Extract content type (Blog, Article, etc.)
    for content_type in content_types:
        if remaining_text.upper().startswith(content_type.upper()):
            components.append(content_type)
            remaining_text = remaining_text[len(content_type):].strip()
            break

    # 2. Extract date (Mar 12, 2025 format)
    date_pattern = r'^(' + '|'.join(months) + r')\s+(\d{1,2}),?\s+(\d{4})'
    date_match = re.match(date_pattern, remaining_text)
    if date_match:
        month, day, year = date_match.groups()
        components.append(f"{month} {day}, {year}")
        remaining_text = remaining_text[date_match.end():].strip()

    # 3. Extract reading time (10 min read format)
    time_pattern = r'^(\d+)\s+min\s+read'
    time_match = re.match(time_pattern, remaining_text, re.IGNORECASE)
    if time_match:
        minutes = time_match.group(1)
        components.append(f"{minutes} min read")
        remaining_text = remaining_text[time_match.end():].strip()

    # 4. The remaining text is likely the title
    # Look for author name at the end (common pattern)
    if remaining_text:
        # Try to find author (usually at the end, often a person's name)
        # Look for patterns like "by Author Name" or just "Author Name"
        author_patterns = [
            r'\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$',  # "by John Doe"
            r'\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)$'        # "John Doe" at end
        ]

        author = None
        title = remaining_text

        for pattern in author_patterns:
            match = re.search(pattern, remaining_text)
            if match:
                author = match.group(1).strip()
                title = remaining_text[:match.start()].strip()
                break

        if title:
            components.append(title)
        if author:
            components.append(author)

    # If we couldn't parse anything, return original text
    if not components:
        return text

    # Join components with commas
    return ', '.join(components)


def _resolve_url(url: str, base_url: str = None) -> str:
    """Resolve relative URLs to absolute URLs."""
    if not base_url or url.startswith(('http://', 'https://', '//')):
        return url

    try:
        return urljoin(base_url, url)
    except Exception:
        return url


def get_html_stats(html_content: str) -> dict:
    """
    Get statistics about the HTML content before and after preprocessing.

    Args:
        html_content: Raw HTML content

    Returns:
        Dictionary with statistics
    """
    original_length = len(html_content)

    # Count HTML elements
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = len(soup.find_all('script'))
    style_tags = len(soup.find_all('style'))
    link_tags = len(soup.find_all('a'))

    # Preprocess and get new stats
    processed_content = preprocess_html_for_llm(html_content)
    processed_length = len(processed_content)

    return {
        'original_length': original_length,
        'processed_length': processed_length,
        'reduction_percent': round((1 - processed_length / original_length) * 100, 1) if original_length > 0 else 0,
        'script_tags': script_tags,
        'style_tags': style_tags,
        'link_tags': link_tags,
        'processed_lines': len(processed_content.split('\n')) if processed_content else 0
    }


# Example usage and testing
if __name__ == "__main__":
    sample_html = """
    <html>
    <head>
        <title>Test Page</title>
        <script>console.log('test');</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <nav><a href="/">Home</a> | <a href="/about">About</a> | <a href="/contact">Contact</a></nav>
        <h1>Main Article Title</h1>
        <p>This is the main content of the article.</p>
        <p>It contains multiple paragraphs.</p>

        <h2>Latest News</h2>
        <div class="article-list">
            <h3><a href="/article1">Breaking News: Major Discovery Made</a></h3>
            <p>A groundbreaking scientific discovery was announced today that could change everything we know about...</p>

            <h3><a href="/article2">Technology Advances in AI</a></h3>
            <p>New developments in artificial intelligence are pushing the boundaries of what's possible...</p>

            <h3><a href="/article3">Economic Trends for 2024</a></h3>
            <p>Experts predict significant changes in the global economy over the next year...</p>
        </div>

        <div class="ads">Advertisement</div>
        <footer>Copyright 2023</footer>
    </body>
    </html>
    """

    # Test both output formats
    print("=== HTML Preprocessing Test ===")

    # Test markdown format (default)
    print("\n--- MARKDOWN FORMAT (default) ---")
    processed_markdown = preprocess_html_for_llm(sample_html, preprocessed_format='markdown')
    print(f"Markdown output length: {len(processed_markdown)} characters")
    print(f"First 500 characters:")
    print("-" * 30)
    print(processed_markdown[:500] + ("..." if len(processed_markdown) > 500 else ""))
    print("-" * 30)

    # Test simple_tags format
    print("\n--- SIMPLE TAGS FORMAT ---")
    processed_tags = preprocess_html_for_llm(sample_html, preprocessed_format='simple_tags')
    print(f"Simple tags output length: {len(processed_tags)} characters")
    print(f"First 500 characters:")
    print("-" * 30)
    print(processed_tags[:500] + ("..." if len(processed_tags) > 500 else ""))
    print("-" * 30)

    # Test urls format
    print("\n--- URLS FORMAT ---")
    processed_urls = preprocess_html_for_llm(sample_html, preprocessed_format='urls')
    print(f"URLs output length: {len(processed_urls)} characters")
    print(f"First 500 characters:")
    print("-" * 30)
    print(processed_urls[:500] + ("..." if len(processed_urls) > 500 else ""))
    print("-" * 30)

    # Show statistics
    stats = get_html_stats(sample_html)
    print("\n📊 ORIGINAL HTML STATS:")
    print(f"Length: {stats['original_length']} characters")
    print(f"Script tags: {stats['script_tags']}")
    print(f"Style tags: {stats['style_tags']}")
    print(f"Link tags: {stats['link_tags']}")

    print(f"\n📊 PROCESSING RESULTS:")
    print(f"Markdown reduction: {stats['reduction_percent']}%")
    print(f"Simple tags reduction: {round((1 - len(processed_tags) / stats['original_length']) * 100, 1)}%")

    # Test the comprehensive URL extraction
    print("\n" + "=" * 60)
    print("🔗 COMPREHENSIVE URL EXTRACTION TEST")
    print("=" * 60)

    # Create a more comprehensive HTML sample with various URL types
    comprehensive_html = """
    <html>
    <head>
        <title>Comprehensive URL Test</title>
        <link rel="stylesheet" href="/css/main.css">
        <link rel="stylesheet" href="https://cdn.example.com/style.css">
        <script src="/js/app.js"></script>
        <script src="//ajax.googleapis.com/jquery.js"></script>
        <meta http-equiv="refresh" content="0; url=https://example.com/redirect">
    </head>
    <body style="background-image: url('/images/bg.jpg')">
        <nav>
            <a href="/">Home</a>
            <a href="/about">About</a>
            <a href="https://external.com/page">External Link</a>
            <a href="#section1">Section 1</a>
        </nav>

        <img src="/images/logo.png" alt="Logo">
        <img data-src="https://cdn.example.com/lazy-image.jpg" alt="Lazy Image">

        <iframe src="https://youtube.com/embed/video123" width="560" height="315"></iframe>

        <form action="/submit" method="post">
            <input type="text" name="query">
            <button type="submit">Search</button>
        </form>

        <form action="https://search.example.com/search" method="get">
            <input type="text" name="q">
        </form>

        <video src="/videos/demo.mp4" controls></video>
        <audio src="https://cdn.example.com/audio/podcast.mp3"></audio>

        <div onclick="window.location.href='/redirect'">Click me</div>
        <a href="javascript:openWindow('https://popup.example.com')">Popup</a>

        <div style="background-image: url('https://cdn.example.com/banner.png')">
            Banner content
        </div>
    </body>
    </html>
    """

    base_url = "https://example.com"
    url_data = extract_all_urls_from_html(comprehensive_html, base_url=base_url)

    # Display results by category
    total_urls = 0
    for category, urls in url_data.items():
        if urls:
            print(f"\n📂 {category.upper()} ({len(urls)} URLs):")
            for i, url_info in enumerate(urls, 1):
                url_type = "🔗 EXTERNAL" if url_info['is_external'] else "🏠 INTERNAL"
                print(f"  {i}. {url_type} | {url_info['element']}:{url_info['attribute']}")
                print(f"     URL: {url_info['url']}")
                if url_info['text']:
                    print(f"     Text: {url_info['text']}")
                if url_info['file_extension']:
                    print(f"     File: .{url_info['file_extension']}")
                if url_info['domain']:
                    print(f"     Domain: {url_info['domain']}")
                print()
            total_urls += len(urls)

    print(f"\n📊 SUMMARY:")
    print(f"Total URLs extracted: {total_urls}")
    print(f"Categories with URLs: {sum(1 for urls in url_data.values() if urls)}")

    external_urls = sum(len(urls) for urls in url_data.values() if urls and any(url['is_external'] for url in urls))
    print(f"External URLs: {external_urls}")

    print("\n" + "=" * 60)
    print("✅ Comprehensive URL extraction implemented!")
    print("✅ HTML preprocessing with tag preservation implemented!")
    print("Use preprocessed_format='simple_tags' to keep HTML structure.")
    print("Use preprocessed_format='urls' for compact anchor link analysis.")
    print("=" * 60)
