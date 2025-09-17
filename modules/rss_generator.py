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
    fg.title('AI Security Digest')
    fg.description('Curated AI security insights and articles from various sources')
    fg.link(href=config.feed_url, rel='alternate')
    fg.language('en')
    fg.generator(generator='AI Security Digest Agent',
                 uri='https://github.com/your-repo')

    # Set feed metadata
    fg.id(config.feed_url.rstrip('/') + '/articles')
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

            # Set entry content/description with enhanced HTML formatting
            summary = article.get('summary', article.get('content', ''))
            if summary:
                # Create enhanced HTML description
                enhanced_description = _create_enhanced_description(
                    article, summary)
                entry.description(enhanced_description)

            # Set publication date
            pub_date = article.get('published_date', '')
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        # Try to parse the date
                        if 'T' in pub_date:
                            dt = datetime.fromisoformat(
                                pub_date.replace('Z', '+00:00'))
                        else:
                            dt = datetime.strptime(
                                pub_date, '%Y-%m-%d %H:%M:%S')
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
            print(
                f"Error adding article '{article.get('title', 'Unknown')}' to RSS feed: {e}")
            continue

    # Generate RSS feed
    try:
        rss_content = fg.rss_str(pretty=True)

        # Write to file
        with open(output_file, 'wb') as f:
            f.write(rss_content)

        print(
            f"Generated RSS feed with {len(articles)} articles: {output_file}")
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


def _create_enhanced_description(article: Dict, summary: str) -> str:
    """
    Create an enhanced HTML description for RSS feed items.

    Args:
        article: Article dictionary with metadata
        summary: Article summary or content

    Returns:
        HTML-formatted description string
    """
    # Get source information
    source_name = article.get('source_name', article.get(
        'source_title', 'Unknown Source'))
    author = article.get('author', '')
    published_date = article.get('published_date', '')
    categories = article.get('categories', [])

    # Format published date if available
    if published_date:
        try:
            if isinstance(published_date, str):
                if 'T' in published_date:
                    dt = datetime.fromisoformat(
                        published_date.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(published_date, '%Y-%m-%d %H:%M:%S')
                formatted_date = dt.strftime('%B %d, %Y')
            else:
                formatted_date = published_date
        except:
            formatted_date = published_date
    else:
        formatted_date = ''

    # Build HTML description
    html_parts = []

    # Add source header with styling
    html_parts.append(
        '<div style="border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 8px 0; background-color: #f9f9f9;">')
    html_parts.append(
        '<div style="font-weight: bold; color: #2c3e50; margin-bottom: 8px;">')
    html_parts.append(f'📄 Source: {source_name}')
    html_parts.append('</div>')

    # Add metadata if available
    metadata_items = []
    if author:
        metadata_items.append(
            f'<span style="color: #7f8c8d;">👤 Author: {author}</span>')
    if formatted_date:
        metadata_items.append(
            f'<span style="color: #7f8c8d;">📅 Date: {formatted_date}</span>')

    if metadata_items:
        html_parts.append(
            '<div style="font-size: 0.9em; margin-bottom: 8px;">')
        html_parts.append(' | '.join(metadata_items))
        html_parts.append('</div>')

    # Add categories if available
    if categories and isinstance(categories, list) and categories:
        category_tags = []
        for category in categories[:3]:  # Limit to 3 categories
            if category and isinstance(category, str):
                category_tags.append(
                    f'<span style="background-color: #3498db; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{category}</span>')

        if category_tags:
            html_parts.append('<div style="margin-bottom: 8px;">')
            html_parts.append(' '.join(category_tags))
            html_parts.append('</div>')

    html_parts.append('</div>')

    # Add the main content
    html_parts.append('<div style="line-height: 1.6;">')
    # Escape HTML in summary to prevent issues
    escaped_summary = summary.replace('&', '&').replace(
        '<', '<').replace('>', '>').replace('"', '"')
    html_parts.append(escaped_summary)
    html_parts.append('</div>')

    return '\n'.join(html_parts)


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
    print(
        f"Top sources: {dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5])}")

    if categories:
        print(
            f"Top categories: {dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10])}")

    # Show date range
    dates = []
    for article in articles:
        pub_date = article.get('published_date', '')
        if pub_date:
            try:
                if isinstance(pub_date, str):
                    if 'T' in pub_date:
                        dt = datetime.fromisoformat(
                            pub_date.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
                elif isinstance(pub_date, datetime):
                    dt = pub_date
                else:
                    continue

                # Ensure all datetimes are timezone-aware for comparison
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                dates.append(dt)
            except:
                continue

    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")
