#!/usr/bin/env python3
"""
Web Article Collection Agent

A tool to collect articles from RSS feeds and custom websites,
summarize them using LLM, and generate RSS feeds.

Usage:
    python main.py sources.json
    python main.py --help
"""

from modules.qdrant_storage import QdrantStorage
from modules.rss_generator import (
    generate_rss_feed,
    validate_rss_feed,
    print_feed_stats
)
from modules.rss_processor import (
    process_rss_feed,
    process_custom_page,
    fetch_individual_articles,
    enrich_articles_with_llm
)
from modules.feed_detector import detect_feed_type
from modules.reddit_processor import RedditProcessor
from config import config
import json
import sys
import os
from typing import List, Dict
from pathlib import Path
import click
from tqdm import tqdm

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_sources_from_file(file_path: str) -> List[Dict]:
    """
    Load sources from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        List of source dictionaries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle both array and object formats
        if isinstance(data, list):
            sources = data
        elif isinstance(data, dict) and 'sources' in data:
            sources = data['sources']
        else:
            print(
                f"Invalid JSON format in {file_path}. Expected array or object with 'sources' key.")
            return []

        # Validate sources
        validated_sources = []
        for source in sources:
            if isinstance(source, dict) and 'url' in source:
                validated_sources.append(source)
            elif isinstance(source, str):
                # Handle simple URL strings
                validated_sources.append({'url': source})

        print(f"Loaded {len(validated_sources)} sources from {file_path}")
        return validated_sources

    except FileNotFoundError:
        print(f"Source file not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error loading sources: {e}")
        return []


def process_source(source: Dict, use_llm: bool = True, verbose: bool = False, html_format: str = 'urls') -> List[Dict]:
    """
    Process a single source and return articles.

    Args:
        source: Source dictionary with 'url' and 'name' keys
        use_llm: Whether to use LLM for custom page processing
        verbose: Whether to print detailed output including HTML content
        html_format: HTML preprocessing format ('urls (default)', 'markdown' or 'simple_tags')

    Returns:
        List of article dictionaries
    """
    url = source.get('url', '').strip()
    source_name = source.get('name', '').strip()
    if not url:
        print("Skipping source with empty URL")
        return []

    print(f"\nProcessing source: {url} ({source_name})")

    # Check if this is a Reddit source
    if _is_reddit_source(url):
        print("Detected Reddit source - using specialized Reddit processor")

        # Check for Reddit-specific model configuration
        reddit_model = os.getenv("REDDIT_LLM_MODEL")
        if reddit_model:
            print(f"Using Reddit-specific model: {reddit_model}")
            reddit_processor = RedditProcessor(verbose=verbose, model=reddit_model)
        else:
            print("Using default model for Reddit processing")
            reddit_processor = RedditProcessor(verbose=verbose)

        articles = reddit_processor.process_reddit_feed(url, source_name)
    else:
        # Auto-detect feed type if not specified
        feed_type = source.get('type')
        if not feed_type:
            print("Auto-detecting feed type...")
            feed_type = detect_feed_type(url)
            print(f"Detected type: {feed_type}")

        # Process based on type
        if feed_type == 'rss':
            articles = process_rss_feed(url, source_name)
        else:
            articles = process_custom_page(url, use_llm, verbose, html_format, source_name)

    print(f"Found {len(articles)} articles")
    return articles


def _is_reddit_source(url: str) -> bool:
    """
    Check if the URL is from Reddit.

    Args:
        url: URL to check

    Returns:
        True if URL is from Reddit
    """
    return 'reddit.com' in url.lower()


@click.command()
@click.argument('sources_file', type=click.Path(exists=False))
@click.option('--output', '-o', default=None, help='Output RSS file path')
@click.option('--no-llm', is_flag=True, help='Skip LLM processing (no summaries or categories)')
@click.option('--max-articles-per-feed', '-m', default=None, type=int, help='Maximum articles per source/feed (default: 1000)')
@click.option('--verbose', '-v', is_flag=True, help='Print detailed output including HTML content')
@click.option('--validate-only', is_flag=True, help='Only validate the sources file format')
@click.option('--html-format', type=click.Choice(['markdown', 'simple_tags', 'urls']), default='urls',
              help='HTML preprocessing format: markdown, simple_tags, or urls (default)')
@click.option('--fetch-full-content', is_flag=True, help='Fetch full content from individual article pages')
@click.option('--request-delay', type=float, default=None, help='Delay between requests in seconds (default: 3.0)')
@click.option('--max-article-pages', type=int, default=None, help='Maximum individual article pages to fetch per source (default: 50)')
@click.option('--qdrant', is_flag=True, help='Store LLM-enriched articles in Qdrant vector database')
def main(sources_file: str, output: str, no_llm: bool, max_articles_per_feed: int, verbose: bool,
         validate_only: bool, html_format: str, fetch_full_content: bool, request_delay: float,
         max_article_pages: int, qdrant: bool):
    """
    Web Article Collection Agent

    Collect articles from RSS feeds and custom websites, summarize them with LLM,
    and generate a consolidated RSS feed.

    SOURCES_FILE: Path to JSON file containing source URLs
    """

    # Check if sources file exists
    if not os.path.exists(sources_file):
        print(f"Sources file not found: {sources_file}")
        sys.exit(1)

    # Validate sources file
    print(f"Loading sources from: {sources_file}")
    sources = load_sources_from_file(sources_file)

    if not sources:
        print("No valid sources found.")
        sys.exit(1)

    if validate_only:
        print(f"✓ Sources file is valid. Found {len(sources)} sources.")
        for source in sources:
            url = source.get('url', '')
            feed_type = source.get('type', 'auto-detect')
            print(f"  - {url} (type: {feed_type})")
        return

    # Update config if options provided
    if max_articles_per_feed:
        config.max_articles_per_source = max_articles_per_feed
    if output:
        config.output_file = output
    if fetch_full_content:
        config.full_content.enabled = True
    if request_delay is not None:
        config.full_content.request_delay = request_delay
    if max_article_pages is not None:
        config.full_content.max_article_pages = max_article_pages
    if qdrant:
        config.qdrant.enabled = True

    print(f"\nStarting article collection...")
    print(f"Output file: {config.output_file}")
    print(f"LLM processing: {'Disabled' if no_llm else 'Enabled'}")
    print(
        f"Qdrant storage: {'Enabled' if config.qdrant.enabled else 'Disabled'}")
    print(f"Max articles per feed: {config.max_articles_per_source}")
    if config.full_content.enabled:
        print(f"Full content fetching: Enabled")
        print(f"Request delay: {config.full_content.request_delay}s")
        print(
            f"Max article pages per source: {config.full_content.max_article_pages}")

    # Process all sources
    all_articles = []
    with tqdm(total=len(sources), desc="Processing sources") as pbar:
        for source in sources:
            articles = process_source(
                source, use_llm=not no_llm, verbose=verbose, html_format=html_format)

            # Apply max articles per source limit as additional safety (should already be applied in processors)
            if len(articles) > config.max_articles_per_source:
                print(
                    f"Applying additional limit: reducing {len(articles)} to {config.max_articles_per_source} articles from source")
                articles = articles[:config.max_articles_per_source]

            all_articles.extend(articles)
            pbar.update(1)

    if not all_articles:
        print("\nNo articles found from any source.")
        sys.exit(1)

    print(f"\nCollected {len(all_articles)} total articles")

    # Check for duplicates against Qdrant before expensive processing
    if config.qdrant.enabled and all_articles:
        print(f"\n🔍 Checking for duplicates in Qdrant...")
        qdrant_storage = QdrantStorage(verbose=verbose)

        filtered_articles = []
        duplicates_skipped = 0

        for article in all_articles:
            is_duplicate, reason = qdrant_storage._check_for_duplicate(article)
            if not is_duplicate:
                filtered_articles.append(article)
            else:
                duplicates_skipped += 1
                if verbose:
                    print(
                        f"⏭️ Skipping duplicate: {article.get('title', '')[:50]}... ({reason})")

        all_articles = filtered_articles
        print(
            f"✅ Duplicate check complete: {duplicates_skipped} duplicates skipped, {len(all_articles)} articles to process")

        # If all articles were duplicates, exit successfully without further processing
        if not all_articles:
            print(
                f"\n✅ All collected articles were duplicates - no further processing needed")
            print("🎉 Job completed successfully!")
            sys.exit(0)

    # Fetch full content from individual article pages if enabled
    if config.full_content.enabled:
        print(f"\nFetching full content from individual article pages...")
        all_articles = fetch_individual_articles(all_articles, verbose=verbose)

    # Enrich with LLM if enabled
    if not no_llm:
        print("\nEnriching articles with LLM...")
        with tqdm(total=len(all_articles), desc="LLM processing") as pbar:
            # Process in batches to avoid overwhelming the LLM
            batch_size = 5
            enriched_articles = []

            for i in range(0, len(all_articles), batch_size):
                batch = all_articles[i:i + batch_size]
                enriched_batch = enrich_articles_with_llm(
                    batch, verbose=verbose)
                enriched_articles.extend(enriched_batch)
                pbar.update(len(batch))

        all_articles = enriched_articles

    # Generate RSS feed
    print("\nGenerating RSS feed...")
    output_path = generate_rss_feed(all_articles, output)

    if not output_path:
        print("Failed to generate RSS feed.")
        sys.exit(1)

    # Validate the generated feed
    print("Validating RSS feed...")
    if validate_rss_feed(output_path):
        print("✓ RSS feed validation successful")
    else:
        print("⚠ RSS feed validation failed")

    # Print statistics
    print_feed_stats(all_articles)

    print(f"\n🎉 Success! RSS feed generated: {output_path}")
    print(f"You can now use this RSS feed in any RSS reader.")


if __name__ == '__main__':
    main()
