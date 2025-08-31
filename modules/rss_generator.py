from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from typing import List, Dict
from config import config
from modules.feed_detector import extract_feed_title

def generate_rss_feed(articles: List[Dict], output_file: str = None) -> str:
    """
    Generate an RSS feed from a list of articles.

    Args:
        articles: List of article dictionaries
        output_file: Output file path (uses config default if None)

    Returns:
        Path to the generated RSS file
    """
    if not articles:
        print("No articles to generate RSS feed from")
        return ""

    if output_file is None:
        output_file = config.output_file

    # Create feed generator
    fg = FeedGenerator()
    fg.title('Web Article Collection')
    fg.description('Collected and summarized articles from various sources')
    fg.link(href='https://your-domain.com/', rel='alternate')
    fg.language('en')
    fg.generator(generator='Web Article Collection Agent', uri='https://github.com/your-repo')

    # Set feed metadata
    fg.id('https://your-domain.com/articles')
    fg.updated(datetime.now(timezone.utc))

    # Add articles to feed
    for article in articles:
        try:
            entry = fg.add_entry()

            # Set entry title
            title = article.get('title', 'Untitled Article')
            entry.title(title)

            # Set entry link
            link = article.get('link', '')
            if link:
                entry.link(href=link, rel='alternate')

            # Set entry ID (GUID)
            guid = article.get('guid', link or title)
            entry.id(guid)

            # Set entry content/description
            summary = article.get('summary', article.get('content', ''))
            if summary:
                entry.description(summary)

            # Set publication date
            pub_date = article.get('published_date', '')
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        # Try to parse the date
                        if 'T' in pub_date:
                            dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
                    elif isinstance(pub_date, datetime):
                        dt = pub_date
                    else:
                        dt = datetime.now(timezone.utc)

                    entry.published(dt)
                    entry.updated(dt)

                except (ValueError, TypeError):
                    # Use current time if date parsing fails
                    now = datetime.now(timezone.utc)
                    entry.published(now)
                    entry.updated(now)
            else:
                now = datetime.now(timezone.utc)
                entry.published(now)
                entry.updated(now)

            # Add categories/topics
            categories = article.get('categories', [])
            if isinstance(categories, list):
                for category in categories:
                    if category and isinstance(category, str):
                        entry.category(term=category.strip())

            # Add author if available
            author = article.get('author', '')
            if author:
                entry.author(name=author)

            # Add source information
            source_url = article.get('source_url', '')
            source_title = article.get('source_title', '')

            if source_url:
                if not source_title:
                    source_title = extract_feed_title(source_url)

                entry.source(url=source_url, title=source_title)

        except Exception as e:
            print(f"Error adding article '{article.get('title', 'Unknown')}' to RSS feed: {e}")
            continue

    # Generate RSS feed
    try:
        rss_content = fg.rss_str(pretty=True)

        # Write to file
        with open(output_file, 'wb') as f:
            f.write(rss_content)

        print(f"Generated RSS feed with {len(articles)} articles: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error generating RSS feed: {e}")
        return ""

def validate_rss_feed(file_path: str) -> bool:
    """
    Validate that the generated RSS file is well-formed.

    Args:
        file_path: Path to the RSS file

    Returns:
        True if valid, False otherwise
    """
    try:
        import xml.etree.ElementTree as ET

        # Parse the XML
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Check for basic RSS structure
        if root.tag != 'rss':
            print(f"Invalid RSS: Root tag is '{root.tag}', expected 'rss'")
            return False

        channel = root.find('channel')
        if channel is None:
            print("Invalid RSS: No channel element found")
            return False

        # Check for required channel elements
        title = channel.find('title')
        if title is None or not title.text:
            print("Invalid RSS: No title in channel")
            return False

        # Check for items
        items = channel.findall('item')
        if not items:
            print("Warning: No items found in RSS feed")
            return True  # Still valid RSS, just empty

        print(f"RSS validation successful: {len(items)} items found")
        return True

    except ET.ParseError as e:
        print(f"RSS validation failed - XML parsing error: {e}")
        return False
    except Exception as e:
        print(f"RSS validation failed: {e}")
        return False

def print_feed_stats(articles: List[Dict]) -> None:
    """
    Print statistics about the generated feed.

    Args:
        articles: List of articles in the feed
    """
    if not articles:
        print("No articles in feed")
        return

    print(f"\nFeed Statistics:")
    print(f"Total articles: {len(articles)}")

    # Count sources
    sources = {}
    categories = {}

    for article in articles:
        source = article.get('source_url', 'Unknown')
        sources[source] = sources.get(source, 0) + 1

        article_categories = article.get('categories', [])
        if isinstance(article_categories, list):
            for category in article_categories:
                if category:
                    categories[category] = categories.get(category, 0) + 1

    print(f"Unique sources: {len(sources)}")
    print(f"Top sources: {dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5])}")

    if categories:
        print(f"Top categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10])}")

    # Show date range
    dates = []
    for article in articles:
        pub_date = article.get('published_date', '')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    if 'T' in pub_date:
                        dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
                    dates.append(dt)
            except:
                continue

    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")
