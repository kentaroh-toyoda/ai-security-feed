#!/usr/bin/env python3
"""
Script to create payload indexes on existing Qdrant collection.

This script adds payload indexes to enable efficient filtering for chatbot integration.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.qdrant_storage import QdrantStorage


def main():
    """Create payload indexes on existing collection."""
    print("🔧 Creating Payload Indexes for Existing Collection")
    print("=" * 60)

    # Initialize Qdrant storage
    qdrant = QdrantStorage(verbose=True)

    # Create payload indexes
    print("\n📝 Creating payload indexes for chatbot filtering...")
    success = qdrant._create_payload_indexes()

    if success:
        print("\n✅ Payload indexes created successfully!")
        print("\n🔍 Verifying indexes...")

        # Check if indexes were created
        indexed_fields = qdrant.get_indexed_fields()
        if indexed_fields and indexed_fields.get('payload_indexes'):
            payload_indexes = indexed_fields['payload_indexes']
            print(f"✅ Found {len(payload_indexes)} payload indexes:")
            for field, info in payload_indexes.items():
                print(f"   • {field}: {info['schema_type']}")
        else:
            print("⚠️  Indexes may take a moment to become active")

    else:
        print("\n❌ Failed to create payload indexes")
        return

    print("\n" + "=" * 60)
    print("🎉 Index creation completed!")
    print("\nYour collection now supports efficient filtering by:")
    print("• Categories, Authors, Sources")
    print("• Publication dates")
    print("• Text content in titles, summaries, and full content")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Index creation interrupted by user")
    except Exception as e:
        print(f"❌ Error during index creation: {e}")
