import requests
import feedparser
from urllib.parse import urlparse
from typing import Literal
from config import config

FeedType = Literal['rss', 'custom']

def detect_feed_type(url: str) -> FeedType:
    """
    Automatically detect if a URL points to an RSS feed or a custom webpage.

    Args:
        url: The URL to check

    Returns:
        'rss' if it's an RSS/ATOM feed, 'custom' otherwise
    """
    try:
        headers = {
            'User-Agent': config.user_agent,
            'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, text/html, */*'
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=config.request_timeout,
            allow_redirects=True
        )

        if response.status_code != 200:
            return 'custom'

        content_type = response.headers.get('content-type', '').lower()

        # Check content type for RSS/ATOM indicators
        rss_indicators = ['rss', 'atom', 'xml']
        if any(indicator in content_type for indicator in rss_indicators):
            return 'rss'

        # Check content for RSS/ATOM patterns
        content = response.text[:2000]  # First 2000 characters should be enough

        rss_patterns = [
            '<rss',
            '<feed',
            '<channel',
            '<item>',
            '<entry>',
            'xmlns="http://www.w3.org/2005/Atom"'
        ]

        if any(pattern in content for pattern in rss_patterns):
            # Double-check by trying to parse with feedparser
            feed = feedparser.parse(content)
            if feed.entries or feed.feed.get('title'):
                return 'rss'

        return 'custom'

    except Exception as e:
        print(f"Error detecting feed type for {url}: {e}")
        return 'custom'

def is_valid_feed(url: str) -> bool:
    """
    Check if a URL contains a valid RSS/ATOM feed.

    Args:
        url: The URL to validate

    Returns:
        True if valid feed, False otherwise
    """
    try:
        headers = {'User-Agent': config.user_agent}
        response = requests.get(url, headers=headers, timeout=config.request_timeout)

        if response.status_code != 200:
            return False

        feed = feedparser.parse(response.text)

        # Check if feed has entries or a title
        return bool(feed.entries or feed.feed.get('title'))

    except Exception:
        return False

def extract_feed_title(url: str) -> str:
    """
    Extract the title from an RSS feed.

    Args:
        url: The feed URL

    Returns:
        Feed title or domain name if extraction fails
    """
    try:
        headers = {'User-Agent': config.user_agent}
        response = requests.get(url, headers=headers, timeout=config.request_timeout)

        if response.status_code == 200:
            feed = feedparser.parse(response.text)
            if feed.feed.get('title'):
                return feed.feed.title

        # Fallback to domain name
        domain = urlparse(url).netloc
        return domain.replace('www.', '')

    except Exception:
        domain = urlparse(url).netloc
        return domain.replace('www.', '')
