import feedparser
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse
from config import config
from modules.llm_client import LLMClient
from modules.html_processor import preprocess_html_for_llm, get_html_stats, extract_all_urls_from_html
from modules.browser_fetcher import fetch_with_fallback

def resolve_url(base_url: str, url: str) -> str:
    """
    Convert relative URLs to absolute URLs using the base URL.

    Args:
        base_url: The base URL (e.g., "https://example.com/blog")
        url: The URL to resolve (can be relative or absolute)

    Returns:
        Absolute URL string
    """
    if not url:
        return base_url

    # If URL is already absolute (has scheme), return as-is
    if urlparse(url).scheme:
        return url

    # Use urljoin to properly handle relative URLs
    absolute_url = urljoin(base_url, url)

    # Ensure the result has a scheme (in case base_url was relative)
    if not urlparse(absolute_url).scheme:
        # If base_url doesn't have a scheme, assume https
        if not base_url.startswith(('http://', 'https://')):
            base_url = 'https://' + base_url.lstrip('/')
        absolute_url = urljoin(base_url, url)

    return absolute_url

def process_rss_feed(url: str) -> List[Dict]:
    """
    Process an RSS/ATOM feed and extract articles.

    Args:
        url: The RSS feed URL

    Returns:
        List of article dictionaries
    """
    try:
        headers = {
            'User-Agent': config.user_agent,
            'Accept': 'application/rss+xml, application/atom+xml, application/xml'
        }

        response = requests.get(url, headers=headers, timeout=config.request_timeout)

        if response.status_code != 200:
            print(f"Failed to fetch RSS feed {url}: HTTP {response.status_code}")
            return []

        # Parse the feed
        feed = feedparser.parse(response.text)

        if not feed.entries:
            print(f"No entries found in RSS feed {url}")
            return []

        articles = []

        for entry in feed.entries[:config.max_articles_per_source]:
            try:
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
                    'content': _extract_content(entry),
                    'published_date': _extract_published_date(entry),
                    'source_url': url,
                    'source_title': feed.feed.get('title', ''),
                    'author': entry.get('author', ''),
                    'guid': entry.get('id', entry.get('link', ''))
                }

                # Skip articles without title or content
                if not article['title'] or not article['content']:
                    continue

                articles.append(article)

            except Exception as e:
                print(f"Error processing RSS entry: {e}")
                continue

        print(f"Extracted {len(articles)} articles from RSS feed {url}")
        return articles

    except Exception as e:
        print(f"Error processing RSS feed {url}: {e}")
        return []

def _extract_content(entry) -> str:
    """
    Extract content from RSS entry with fallback logic.

    Args:
        entry: FeedParser entry object

    Returns:
        Extracted content as string
    """
    # Try different content fields in order of preference
    content_fields = [
        'content',
        'summary',
        'description',
        'summary_detail',
        'content_detail'
    ]

    for field in content_fields:
        if hasattr(entry, field):
            content = getattr(entry, field)

            # Handle different content formats
            if isinstance(content, list) and content:
                content = content[0]

            if isinstance(content, dict) and 'value' in content:
                return content['value']
            elif isinstance(content, str):
                return content

    # If no content found, try to get a summary from title
    if hasattr(entry, 'title'):
        return f"Article: {entry.title}"

    return ""

def _extract_published_date(entry) -> str:
    """
    Extract publication date from RSS entry.

    Args:
        entry: FeedParser entry object

    Returns:
        ISO format date string or empty string
    """
    date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

    for field in date_fields:
        if hasattr(entry, field):
            date_tuple = getattr(entry, field)
            if date_tuple:
                try:
                    dt = datetime(*date_tuple[:6])
                    return dt.isoformat()
                except (ValueError, TypeError):
                    continue

    # Try string date fields
    string_date_fields = ['published', 'updated', 'created']
    for field in string_date_fields:
        if hasattr(entry, field):
            date_str = getattr(entry, field)
            if date_str:
                try:
                    dt = parsedate_to_datetime(date_str)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    continue

    return ""

def process_custom_page(url: str, use_llm: bool = True, verbose: bool = False, html_format: str = 'markdown') -> List[Dict]:
    """
    Process a custom webpage by fetching HTML and optionally using LLM to extract articles.

    Args:
        url: The webpage URL
        use_llm: Whether to use LLM for article extraction
        verbose: Whether to print detailed output including HTML content
        html_format: HTML preprocessing format ('markdown' or 'simple_tags')

    Returns:
        List of article dictionaries
    """
    # Create LLM client instance with verbose flag
    llm_client = LLMClient(verbose=verbose)

    # Prepare browser configuration
    browser_config = {
        'browser': config.browser.browser,
        'headless': config.browser.headless,
        'wait_time': config.browser.wait_time,
        'scroll_attempts': config.browser.scroll_attempts,
        'max_scroll_wait': config.browser.max_scroll_wait
    }

    try:
        # Use intelligent fetching with fallback from static to browser
        if config.browser.enabled:
            print(f"Fetching {url} with intelligent content detection...")
            html_content, fetch_metadata = fetch_with_fallback(url, browser_config, config.browser.static_timeout)

            if not html_content:
                print(f"Failed to fetch webpage {url}")
                return []

            # Log fetch method used
            fetch_method = fetch_metadata.get('fetch_method', 'unknown')
            if fetch_metadata.get('dynamic_rendering_used'):
                quality_improvement = fetch_metadata.get('quality_improvement', 0)
                print(f"Dynamic rendering used for {url} (quality improvement: {quality_improvement:.1f}%)")
            else:
                print(f"Using static fetch for {url}")
        else:
            # Fallback to original static-only method
            print(f"Fetching {url} (static only, browser disabled)...")
            headers = {
                'User-Agent': config.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            response = requests.get(url, headers=headers, timeout=config.request_timeout)
            if response.status_code != 200:
                print(f"Failed to fetch webpage {url}: HTTP {response.status_code}")
                return []
            html_content = response.text

            # Legacy wait mechanism for backward compatibility
            if config.enable_page_load_wait and config.page_load_wait_time > 0:
                print(f"Waiting {config.page_load_wait_time} seconds for page content to load...")
                time.sleep(config.page_load_wait_time)
                print("Wait completed, proceeding with content processing.")

        # Print HTML content if verbose mode is enabled
        if verbose:
            print(f"\n{'='*80}")
            print(f"VERBOSE: HTML content from {url}")
            print(f"{'='*80}")

            # Show original HTML statistics
            print("📄 ORIGINAL HTML:")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"Content-Length: {len(html_content)} characters")
            print(f"First 2000 characters of raw HTML:")
            print(f"{'-'*40}")
            print(html_content[:2000])
            if len(html_content) > 2000:
                print(f"... ({len(html_content) - 2000} more characters)")

            # Pre-process HTML and show statistics
            print(f"\n🔄 HTML PREPROCESSING:")
            processed_content = preprocess_html_for_llm(html_content, max_length=6000, preprocessed_format=html_format)
            stats = get_html_stats(html_content)

            print(f"Reduction: {stats['reduction_percent']}% ({stats['original_length']} → {stats['processed_length']} characters)")
            print(f"Elements removed: {stats['script_tags']} scripts, {stats['style_tags']} styles, {stats['link_tags']} links")
            print(f"Processed lines: {stats['processed_lines']}")

            print(f"\n📝 PROCESSED CONTENT (sent to LLM):")
            print(f"{'-'*40}")
            print(processed_content)
            print(f"{'='*80}\n")

        # Extract all URLs from the HTML content
        url_data = extract_all_urls_from_html(html_content, base_url=url)

        if use_llm:
            # Use LLM to extract articles from HTML
            articles = llm_client.extract_articles_from_html(html_content, url, html_format)
        else:
            # Fallback: create a single article from the page title and URL
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract page title
            title = soup.title.string if soup.title else "Untitled Page"
            title = title.strip() if title else "Untitled Page"

            # Create a basic article entry
            articles = [{
                'title': title,
                'link': url,
                'content': f"Content from {url}",
                'published_date': '',
                'source_url': url,
                'source_title': title,
                'guid': url
            }]

        # Resolve relative URLs to absolute URLs
        for article in articles:
            if 'link' in article and article['link']:
                original_link = article['link']
                resolved_link = resolve_url(url, original_link)
                article['link'] = resolved_link
                if original_link != resolved_link:
                    print(f"   Resolved URL: {original_link} → {resolved_link}")

        print(f"Extracted {len(articles)} articles from custom page {url}")
        return articles

    except Exception as e:
        print(f"Error processing custom page {url}: {e}")
        return []

def enrich_articles_with_llm(articles: List[Dict], verbose: bool = False) -> List[Dict]:
    """
    Enrich articles with LLM-generated summaries and categories.

    Args:
        articles: List of article dictionaries
        verbose: Whether to show LLM debug information

    Returns:
        List of enriched article dictionaries
    """
    # Create LLM client instance with verbose flag
    llm_client = LLMClient(verbose=verbose)
    enriched_articles = []

    for article in articles:
        try:
            title = article.get('title', '')
            content = article.get('content', '')

            if not title or not content:
                # Skip articles without sufficient content
                enriched_articles.append(article)
                continue

            # Generate summary and categories using LLM
            summary, categories = llm_client.summarize_and_categorize_article(title, content)

            # Add LLM-generated data to article
            enriched_article = article.copy()
            enriched_article['summary'] = summary
            enriched_article['categories'] = categories

            enriched_articles.append(enriched_article)

            print(f"Processed article: {title[:50]}...")

        except Exception as e:
            print(f"Error enriching article {article.get('title', 'Unknown')}: {e}")
            # Add the original article if enrichment fails
            enriched_articles.append(article)

    return enriched_articles
