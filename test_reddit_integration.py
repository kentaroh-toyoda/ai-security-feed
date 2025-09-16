#!/usr/bin/env python3
"""
Test script for Reddit integration functionality.
Tests the Reddit processor independently.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.reddit_processor import RedditProcessor

def test_reddit_processor():
    """Test the Reddit processor with the ChatGPTJailbreak subreddit"""

    print("🧪 Testing Reddit Processor Integration")
    print("=" * 50)

    # Initialize processor
    processor = RedditProcessor(verbose=True)

    # Test Reddit RSS URL
    reddit_url = "https://www.reddit.com/r/ChatGPTJailbreak/new.rss"

    print(f"📡 Testing Reddit RSS feed: {reddit_url}")
    print("-" * 40)

    try:
        # Process the Reddit feed
        articles = processor.process_reddit_feed(reddit_url)

        print(f"\n📊 Results:")
        print(f"   Articles found: {len(articles)}")

        if articles:
            print("\n📝 Sample Article:")
            article = articles[0]
            print(f"   Title: {article.get('title', 'N/A')}")
            print(f"   Link: {article.get('link', 'N/A')}")
            print(f"   Categories: {article.get('categories', [])}")

            # Show attack technique data if available
            attack_technique = article.get('attack_technique')
            if attack_technique:
                print("\n🔒 Attack Technique Data:")
                print(f"   Type: {attack_technique.get('type', 'N/A')}")
                print(f"   Target Models: {attack_technique.get('target_models', 'N/A')}")
                print(f"   Validated: {attack_technique.get('validated', 'N/A')}")
                print(f"   Confidence: {attack_technique.get('confidence_score', 'N/A'):.2f}")

                # Show formatted content
                formatted = processor.format_attack_technique_output(attack_technique)
                print(f"\n📄 Formatted Output:\n{formatted}")
        else:
            print("❌ No attack techniques found in the feed")

    except Exception as e:
        print(f"❌ Error testing Reddit processor: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("✅ Reddit Processor Test Complete")

if __name__ == "__main__":
    test_reddit_processor()
