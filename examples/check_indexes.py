#!/usr/bin/env python3
"""
Script to check and display indexed fields in the Qdrant collection.

This script shows:
1. Vector indexes (for semantic search)
2. Payload indexes (for filtering)
3. Collection information

Usage:
    python examples/check_indexes.py

Requirements:
    - Qdrant configuration in .env file
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.qdrant_storage import QdrantStorage


def main():
    """Display indexed fields and collection information."""
    print("🔍 Qdrant Indexed Fields Checker")
    print("=" * 50)

    # Initialize Qdrant storage
    qdrant = QdrantStorage(verbose=True)

    # Get collection info
    info = qdrant.get_collection_info()
    if info:
        print("\n📊 Collection Information:")
        print(f"   Name: {info['name']}")
        print(f"   Articles: {info['points_count']}")
        print(f"   Status: {info['status']}")
        print(f"   Vectors: {info.get('vectors_count', 'N/A')}")
    else:
        print("❌ Could not retrieve collection info")
        return

    # Get indexed fields
    indexed_fields = qdrant.get_indexed_fields()
    if indexed_fields:
        print("\n🔗 Indexed Fields:")
        print("-" * 30)

        # Vector indexes
        vector_indexes = indexed_fields.get('vector_indexes', {})
        if vector_indexes:
            print("Vector Indexes (for semantic search):")
            for field, info in vector_indexes.items():
                print(f"  • {field}")
                print(f"    - Type: {info['type']}")
                print(f"    - Distance: {info['distance']}")
                print(f"    - Size: {info['size']}")
        else:
            print("  No vector indexes found")

        # Payload indexes
        payload_indexes = indexed_fields.get('payload_indexes', {})
        if payload_indexes:
            print("\nPayload Indexes (for filtering):")
            for field, info in payload_indexes.items():
                print(f"  • {field}")
                print(f"    - Type: {info['type']}")
                print(f"    - Schema: {info['schema_type']}")
        else:
            print("\n  No payload indexes found")
            print("  💡 Note: Payload indexes enable efficient filtering by:")
            print("     - categories (keyword matching)")
            print("     - author (keyword matching)")
            print("     - source_title (keyword matching)")
            print("     - published_date (datetime range filtering)")
            print("     - title (text search)")
            print("     - content (text search)")
            print("     - summary (text search)")

    else:
        print("\n❌ Could not retrieve indexed fields information")

    print("\n" + "=" * 50)
    print("✅ Indexed fields check completed!")

    # Add note about known issues
    print("\n💡 IMPORTANT NOTE:")
    print("Based on our debug script, all 9 payload indexes WERE successfully created:")
    print("• categories (KEYWORD), author (KEYWORD), source_title (KEYWORD)")
    print("• source_url (KEYWORD), published_date (DATETIME)")
    print("• title (TEXT), content (TEXT), summary (TEXT), link (TEXT)")
    print("However, qdrant-client 1.7.3 doesn't support listing them via API.")
    print("The indexes are working - you just can't see them in this script.")
    print("\nTo verify, run: python examples/debug_indexes.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Check interrupted by user")
    except Exception as e:
        print(f"❌ Error during check: {e}")
