#!/usr/bin/env python3
"""
Script to check existence of specific article entries by title and URL.

This script checks if the specified title and URL exist in the Qdrant database.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.qdrant_storage import QdrantStorage


def check_entry_existence():
    """Check if specific entries exist in the database."""
    print("🔍 Checking Entry Existence")
    print("=" * 50)

    # Initialize Qdrant storage
    qdrant = QdrantStorage(verbose=False)

    # Test entries to check
    test_title = "The Future of AI Reliability Is Open and Collaborative: Introducing Guardrails Hub"
    test_link = "https://www.guardrailsai.com/blog/the-future-of-ai-reliability-is-open-and-collaborative-introducing-guardrails-hub"

    # Test 1: Check title existence
    print("\n1️⃣ Checking title existence...")
    print(f"   Title: {test_title}")
    results = qdrant.check_entry_existence(title=test_title, limit=5)

    if results:
        print(f"   ✅ Title found! {len(results)} matching result(s)")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            article = result['article']
            print(f"      Result {i+1}:")
            print(f"         ID: {result['id']}")
            print(f"         Title: {article.get('title', 'N/A')}")
            print(f"         Link: {article.get('link', 'N/A')}")
            print(f"         Source: {article.get('source_title', 'N/A')}")
            print(f"         Published: {article.get('published_date', 'N/A')}")
            print(f"         Categories: {', '.join(article.get('categories', []))}")
    else:
        print("   ❌ Title not found")

    # Test 2: Check URL existence
    print("\n2️⃣ Checking URL existence...")
    print(f"   URL: {test_link}")
    results = qdrant.check_entry_existence(link=test_link, limit=5)

    if results:
        print(f"   ✅ URL found! {len(results)} matching result(s)")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            article = result['article']
            print(f"      Result {i+1}:")
            print(f"         ID: {result['id']}")
            print(f"         Title: {article.get('title', 'N/A')}")
            print(f"         Link: {article.get('link', 'N/A')}")
            print(f"         Source: {article.get('source_title', 'N/A')}")
            print(f"         Published: {article.get('published_date', 'N/A')}")
            print(f"         Categories: {', '.join(article.get('categories', []))}")
    else:
        print("   ❌ URL not found")

    print("\n" + "=" * 50)
    print("✅ Entry existence check completed!")


def main():
    """Main function."""
    try:
        check_entry_existence()
    except KeyboardInterrupt:
        print("\n🛑 Check interrupted by user")
    except Exception as e:
        print(f"❌ Error during check: {e}")


if __name__ == "__main__":
    main()
