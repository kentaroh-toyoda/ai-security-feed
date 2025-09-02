#!/usr/bin/env python3
"""
Example script demonstrating how to search articles stored in Qdrant.

This script shows how to:
1. Connect to Qdrant
2. Search articles by semantic similarity
3. Filter by categories, sources, or date ranges
4. Display search results

Usage:
    python examples/search_qdrant.py "artificial intelligence"

Requirements:
    - Articles must be stored in Qdrant first using: python main.py sources.json --qdrant
    - Qdrant configuration in .env file
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.qdrant_storage import QdrantStorage


def search_articles_example():
    """Demonstrate basic article search functionality."""

    print("🔍 Qdrant Article Search Example")
    print("=" * 50)

    # Initialize Qdrant storage
    qdrant = QdrantStorage(verbose=True)

    # Get collection info
    info = qdrant.get_collection_info()
    if info:
        print("📊 Collection Info:")
        print(f"   Name: {info['name']}")
        print(f"   Articles: {info['points_count']}")
        print(f"   Status: {info['status']}")
    else:
        print("❌ Could not retrieve collection info")
        return

    print("\n" + "=" * 50)

    # Example searches
    queries = [
        "artificial intelligence",
        "machine learning",
        "technology trends",
        "climate change"
    ]

    for query in queries:
        print(f"\n🔎 Searching for: '{query}'")
        print("-" * 40)

        # Search by combined embedding (title + summary + content)
        results = qdrant.search_articles(
            query=query,
            limit=3,
            search_type="combined"
        )

        if results:
            for i, result in enumerate(results, 1):
                article = result['article']
                score = result['score']

                print(f"{i}. {article['title'][:60]}{'...' if len(article['title']) > 60 else ''}")
                print(f"   Score: {score:.2f}")
                print(f"   Categories: {', '.join(article.get('categories', []))}")
                print(f"   Source: {article.get('source_title', 'Unknown')}")
                print(f"   URL: {article.get('link', '')}")
                if article.get('summary'):
                    print(f"   Summary: {article['summary'][:100]}{'...' if len(article['summary']) > 100 else ''}")
                print()
        else:
            print("No results found")

    print("\n" + "=" * 50)
    print("✅ Search example completed!")


def search_with_filters_example():
    """Demonstrate search with filters."""

    print("\n🔍 Advanced Search with Filters Example")
    print("=" * 50)

    qdrant = QdrantStorage(verbose=False)

    # Get indexed fields info
    indexed_fields = qdrant.get_indexed_fields()
    if indexed_fields:
        print("📊 Indexed Fields:")
        print("Vector Indexes:")
        for field, info in indexed_fields.get('vector_indexes', {}).items():
            print(f"  • {field}: {info['type']}, distance: {info['distance']}, size: {info['size']}")

        print("\nPayload Indexes:")
        for field, info in indexed_fields.get('payload_indexes', {}).items():
            print(f"  • {field}: {info['type']}, schema: {info['schema_type']}")

    # Example filtered searches
    print("\n🔎 Filtered Search Examples:")
    print("-" * 40)

    # Example 1: Filter by category
    filters = {"categories": ["technology", "ai"]}
    results = qdrant.search_articles(
        query="artificial intelligence",
        limit=3,
        filters=filters
    )
    print(f"\n1. Search for 'artificial intelligence' in technology/ai categories:")
    print(f"   Found {len(results)} results")
    if results:
        for i, result in enumerate(results[:2], 1):
            article = result['article']
            print(f"   {i}. {article['title'][:50]}... (Score: {result['score']:.2f})")

    # Example 2: Filter by date range
    from datetime import datetime, timedelta
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    filters = {"date_from": week_ago}
    results = qdrant.search_articles(
        query="machine learning",
        limit=3,
        filters=filters
    )
    print(f"\n2. Search for 'machine learning' from last week:")
    print(f"   Found {len(results)} results")
    if results:
        for i, result in enumerate(results[:2], 1):
            article = result['article']
            print(f"   {i}. {article['title'][:50]}... (Score: {result['score']:.2f})")

    # Example 3: Filter by source
    filters = {"source_title": "TechCrunch"}
    results = qdrant.search_articles(
        query="startup",
        limit=3,
        filters=filters
    )
    print(f"\n3. Search for 'startup' from TechCrunch:")
    print(f"   Found {len(results)} results")
    if results:
        for i, result in enumerate(results[:2], 1):
            article = result['article']
            print(f"   {i}. {article['title'][:50]}... (Score: {result['score']:.2f})")

    # Example 4: Combined filters
    filters = {
        "categories": ["business"],
        "date_from": week_ago,
        "author": "John Doe"
    }
    results = qdrant.search_articles(
        query="economy",
        limit=3,
        filters=filters
    )
    print(f"\n4. Combined filters - business category, recent, specific author:")
    print(f"   Found {len(results)} results")
    if results:
        for i, result in enumerate(results[:2], 1):
            article = result['article']
            print(f"   {i}. {article['title'][:50]}... (Score: {result['score']:.2f})")

    print("\n✅ Advanced filtering examples completed!")


if __name__ == "__main__":
    try:
        search_articles_example()
        search_with_filters_example()
    except KeyboardInterrupt:
        print("\n🛑 Search interrupted by user")
    except Exception as e:
        print(f"❌ Error during search: {e}")
