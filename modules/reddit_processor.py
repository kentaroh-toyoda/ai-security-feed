"""
Reddit-specific processor for extracting attack techniques from jailbreak posts.

This module handles Reddit RSS feeds with specialized filtering and extraction
for security-related content, particularly jailbreak techniques and attack prompts.
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse
import feedparser
import requests
from config import config
from modules.llm_client import LLMClient


class RedditLLMClient(LLMClient):
    """LLM client specifically for Reddit processing with custom model support"""

    def __init__(self, verbose: bool = False, model: str = None):
        super().__init__(verbose=verbose)
        if model:
            self.model = model
            if self.verbose:
                print(f"🔄 Reddit LLM Client using custom model: {model}")


class RedditProcessor:
    """Specialized processor for Reddit posts with attack technique extraction"""

    def __init__(self, verbose: bool = False, model: str = None):
        self.verbose = verbose

        # Use Reddit-specific model if provided, otherwise use default
        if model:
            self.llm_client = RedditLLMClient(verbose=verbose, model=model)
        else:
            self.llm_client = LLMClient(verbose=verbose)

    def process_reddit_feed(self, url: str, source_name: str = '') -> List[Dict]:
        """
        Process Reddit RSS feed with attack technique filtering.

        Args:
            url: Reddit RSS feed URL
            source_name: Name of the source from sources.json

        Returns:
            List of filtered attack technique articles
        """
        try:
            # Fetch and parse RSS feed
            headers = {
                'User-Agent': config.user_agent,
                'Accept': 'application/rss+xml, application/atom+xml, application/xml'
            }

            response = requests.get(url, headers=headers, timeout=config.request_timeout)

            if response.status_code != 200:
                print(f"Failed to fetch Reddit feed {url}: HTTP {response.status_code}")
                return []

            feed = feedparser.parse(response.text)

            if not feed.entries:
                print(f"No entries found in Reddit feed {url}")
                return []

            articles = []
            attack_techniques = []

            for entry in feed.entries[:config.max_articles_per_source]:
                try:
                    # Extract Reddit-specific post data
                    post_data = self._extract_reddit_post_data(entry)

                    # Filter out NSFW content
                    if self._is_nsfw_content(post_data):
                        if self.verbose:
                            print(f"⏭️ Skipping NSFW post: {post_data.get('title', '')[:50]}...")
                        continue

                    # Check if post contains attack techniques
                    attack_data = self._extract_attack_technique(post_data)

                    if attack_data:
                        # Create formatted content from attack technique data
                        formatted_content = self.format_attack_technique_output(attack_data)

                        # Use source_name if provided, otherwise use Reddit subreddit name
                        reddit_title = f"Reddit - {self._get_subreddit_name(url)}"
                        final_source_name = source_name if source_name else reddit_title

                        # Create enriched article with attack technique data
                        article = {
                            'title': post_data['title'],
                            'link': post_data['link'],
                            'content': formatted_content,
                            'published_date': post_data['published_date'],
                            'source_url': url,
                            'source_name': final_source_name,
                            'source_title': reddit_title,  # Keep original Reddit title for reference
                            'author': post_data.get('author', ''),
                            'guid': post_data.get('guid', post_data['link']),
                            'attack_technique': attack_data,
                            'categories': ['Attack Technique', 'Jailbreak', 'AI Security']
                        }

                        articles.append(article)
                        attack_techniques.append(attack_data)

                        if self.verbose:
                            print(f"✅ Extracted attack technique: {post_data['title'][:50]}...")

                except Exception as e:
                    print(f"Error processing Reddit entry: {e}")
                    continue

            print(f"Extracted {len(attack_techniques)} attack techniques from Reddit feed {url}")
            return articles

        except Exception as e:
            print(f"Error processing Reddit feed {url}: {e}")
            return []

    def _extract_reddit_post_data(self, entry) -> Dict:
        """
        Extract Reddit-specific post data from RSS entry.

        Args:
            entry: FeedParser entry object

        Returns:
            Dictionary with extracted post data
        """
        # Reddit RSS includes additional fields in content
        content = self._extract_content(entry)

        # Extract Reddit-specific metadata from content or tags
        post_data = {
            'title': entry.get('title', '').strip(),
            'link': entry.get('link', ''),
            'content': content,
            'published_date': self._extract_published_date(entry),
            'author': entry.get('author', ''),
            'guid': entry.get('id', entry.get('link', '')),
            'tags': [tag.get('term', '') for tag in entry.get('tags', []) if tag.get('term')],
            'flair': self._extract_flair(entry),
            'nsfw': self._check_reddit_nsfw_flags(entry)
        }

        return post_data

    def _extract_content(self, entry) -> str:
        """Extract content from Reddit RSS entry"""
        # Reddit RSS often has content in different formats
        content_fields = ['content', 'summary', 'description']

        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)

                if isinstance(content, list) and content:
                    content = content[0]

                if isinstance(content, dict) and 'value' in content:
                    return content['value']
                elif isinstance(content, str):
                    return content

        return entry.get('title', '')

    def _extract_published_date(self, entry) -> str:
        """Extract publication date from Reddit entry"""
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

        return ""

    def _extract_flair(self, entry) -> str:
        """Extract post flair from Reddit entry"""
        # Reddit flairs are often in tags or content
        tags = entry.get('tags', [])
        for tag in tags:
            if 'flair' in tag.get('term', '').lower():
                return tag.get('term', '')

        # Try to extract from title or content
        title = entry.get('title', '')
        if '[' in title and ']' in title:
            match = re.search(r'\[([^\]]+)\]', title)
            if match:
                return match.group(1)

        return ""

    def _check_reddit_nsfw_flags(self, entry) -> bool:
        """Check if Reddit post has NSFW flags"""
        # Check tags for NSFW indicators
        tags = [tag.get('term', '').lower() for tag in entry.get('tags', [])]
        nsfw_indicators = ['nsfw', 'adult', 'mature', 'explicit']

        for tag in tags:
            if any(indicator in tag for indicator in nsfw_indicators):
                return True

        # Check content for NSFW indicators
        content = self._extract_content(entry).lower()
        nsfw_keywords = ['nsfw', 'porn', 'sex', 'nude', 'adult content']

        for keyword in nsfw_keywords:
            if keyword in content:
                return True

        return False

    def _is_nsfw_content(self, post_data: Dict) -> bool:
        """
        Determine if post content is NSFW using multiple criteria.

        Args:
            post_data: Post data dictionary

        Returns:
            True if content appears to be NSFW
        """
        # Check Reddit NSFW flags
        if post_data.get('nsfw', False):
            return True

        # Check content for NSFW keywords
        content = post_data.get('content', '').lower()
        title = post_data.get('title', '').lower()

        nsfw_keywords = [
            'nsfw', 'porn', 'sex', 'nude', 'adult', 'xxx', 'erotic',
            'fetish', 'bdsm', 'orgasm', 'masturbat', 'vagina', 'penis',
            'boobs', 'tits', 'ass', 'fuck', 'shit', 'damn', 'bitch'
        ]

        text_to_check = content + ' ' + title

        for keyword in nsfw_keywords:
            if keyword in text_to_check:
                return True

        return False

    def _extract_attack_technique(self, post_data: Dict) -> Optional[Dict]:
        """
        Extract attack technique information from Reddit post.

        Args:
            post_data: Post data dictionary

        Returns:
            Dictionary with attack technique data or None if not found
        """
        title = post_data.get('title', '')
        content = post_data.get('content', '')

        # Quick pre-filter for potential attack content
        if not self._has_attack_indicators(title + ' ' + content):
            return None

        # Use LLM to analyze and extract attack technique
        attack_data = self._analyze_attack_content(title, content)

        return attack_data

    def _has_attack_indicators(self, text: str) -> bool:
        """
        Check if text contains indicators of attack techniques.

        Args:
            text: Text to analyze

        Returns:
            True if text likely contains attack techniques
        """
        attack_indicators = [
            'jailbreak', 'prompt injection', 'dan mode', 'uncensored',
            'bypass', 'exploit', 'vulnerability', 'attack', 'technique',
            'payload', 'malicious', 'hack', 'security', 'breakthrough',
            'override', 'system prompt', 'role play', 'persona',
            'unrestricted', 'developer mode', 'admin', 'root'
        ]

        text_lower = text.lower()

        # Count attack indicators
        indicator_count = sum(1 for indicator in attack_indicators if indicator in text_lower)

        # Must have at least 2 attack indicators or specific jailbreak terms
        if indicator_count >= 2:
            return True

        # Check for specific jailbreak patterns
        jailbreak_patterns = [
            'ignore.*previous.*instructions',
            'developer.*mode',
            'dan.*mode',
            'uncensored.*mode',
            'bypass.*restrictions'
        ]

        for pattern in jailbreak_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False

    def _analyze_attack_content(self, title: str, content: str) -> Optional[Dict]:
        """
        Use LLM to analyze content and extract structured attack technique data.

        Args:
            title: Post title
            content: Post content

        Returns:
            Structured attack technique data or None
        """
        system_message = """You are a security expert analyzing jailbreak attempts and attack techniques against AI models.
        Your task is to identify and extract structured information about attack techniques from Reddit posts.

        Focus on:
        - Jailbreak prompts and techniques
        - Prompt injection methods
        - System prompt overrides
        - Role-playing exploits
        - Unrestricted mode activations

        Only extract information if the content contains a VALID, COMPREHENSIVE attack technique.
        Skip general discussions, questions, or incomplete techniques."""

        prompt = f"""
        Analyze this Reddit post about potential AI jailbreak or attack techniques:

        TITLE: {title}

        CONTENT:
        {content}

        Determine if this post contains a comprehensive, validated attack technique.

        REQUIREMENTS FOR EXTRACTION:
        1. Must contain actual attack prompts/techniques (not just discussion)
        2. Must be comprehensive enough to potentially work
        3. Must target AI models (ChatGPT, GPT, Claude, etc.)

        If it meets the requirements, extract in this EXACT format:

        Type: New Attack
        Attack Prompts (JSON): {{"prompt": "the actual attack prompt text"}}
        Target Models: ["model1", "model2"] or ["NA"]
        Validated: Yes/No
        Description: Brief description of the attack technique

        If it does NOT meet requirements, respond with only: NO_ATTACK_FOUND

        IMPORTANT:
        - Only extract if there's actual working attack content
        - Target Models should list specific models mentioned (GPT-4, ChatGPT, Claude, etc.) or ["NA"]
        - Validated should be "Yes" if the post shows successful validation/testing, "No" otherwise
        """

        response = self.llm_client._call_llm(prompt, system_message)

        if not response or response.strip() == "NO_ATTACK_FOUND":
            return None

        try:
            # Parse the structured response
            attack_data = self._parse_attack_response(response)

            if attack_data:
                # Add additional metadata
                attack_data.update({
                    'source_title': title,
                    'source_content': content,
                    'extraction_timestamp': datetime.now().isoformat(),
                    'confidence_score': self._calculate_confidence_score(attack_data)
                })

                return attack_data

        except Exception as e:
            if self.verbose:
                print(f"Error parsing attack response: {e}")

        return None

    def _parse_attack_response(self, response: str) -> Optional[Dict]:
        """
        Parse LLM response into structured attack technique data.

        Args:
            response: LLM response text

        Returns:
            Structured attack data dictionary
        """
        lines = response.strip().split('\n')
        attack_data = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('Type:'):
                attack_data['type'] = line.replace('Type:', '').strip()

            elif line.startswith('Attack Prompts'):
                # Extract JSON from the prompt field
                json_match = re.search(r'\{.*\}', line, re.DOTALL)
                if json_match:
                    try:
                        prompts_data = json.loads(json_match.group())
                        attack_data['attack_prompts'] = prompts_data
                    except json.JSONDecodeError:
                        attack_data['attack_prompts'] = {'prompt': line.split(':', 1)[1].strip()}

            elif line.startswith('Target Models:'):
                models_text = line.replace('Target Models:', '').strip()
                try:
                    models = json.loads(models_text)
                    attack_data['target_models'] = models
                except json.JSONDecodeError:
                    # Handle non-JSON format
                    if 'NA' in models_text:
                        attack_data['target_models'] = ['NA']
                    else:
                        attack_data['target_models'] = [m.strip() for m in models_text.split(',')]

            elif line.startswith('Validated:'):
                validated = line.replace('Validated:', '').strip().lower()
                attack_data['validated'] = validated == 'yes'

            elif line.startswith('Description:'):
                attack_data['description'] = line.replace('Description:', '').strip()

        # Validate required fields
        required_fields = ['type', 'attack_prompts', 'target_models', 'validated']
        if all(field in attack_data for field in required_fields):
            return attack_data

        return None

    def _calculate_confidence_score(self, attack_data: Dict) -> float:
        """
        Calculate confidence score for extracted attack technique.

        Args:
            attack_data: Attack technique data

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.5  # Base score

        # Increase score for validated techniques
        if attack_data.get('validated', False):
            score += 0.2

        # Increase score for specific target models
        target_models = attack_data.get('target_models', [])
        if target_models and 'NA' not in target_models:
            score += 0.1

        # Increase score for detailed descriptions
        if attack_data.get('description', ''):
            score += 0.1

        # Increase score for comprehensive prompts
        prompts = attack_data.get('attack_prompts', {})
        if isinstance(prompts, dict) and len(str(prompts)) > 100:
            score += 0.1

        return min(score, 1.0)

    def _get_subreddit_name(self, url: str) -> str:
        """Extract subreddit name from Reddit URL"""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'r':
            return path_parts[1]
        return "Unknown"

    def format_attack_technique_output(self, attack_data: Dict) -> str:
        """
        Format attack technique data into the requested output format.

        Args:
            attack_data: Attack technique dictionary

        Returns:
            Formatted output string
        """
        output_lines = []

        # Type
        output_lines.append(f"Type: {attack_data.get('type', 'New Attack')}")

        # Attack Prompts
        prompts = attack_data.get('attack_prompts', {})
        if isinstance(prompts, dict):
            output_lines.append(f"Attack Prompts (JSON): {json.dumps(prompts, indent=2)}")
        else:
            output_lines.append(f"Attack Prompts: {prompts}")

        # Target Models
        target_models = attack_data.get('target_models', ['NA'])
        if isinstance(target_models, list):
            output_lines.append(f"Target models: {target_models}")
        else:
            output_lines.append(f"Target models: [{target_models}]")

        # Validated
        validated = "Yes" if attack_data.get('validated', False) else "No"
        output_lines.append(f"Validated?: {validated}")

        # Add description if available
        description = attack_data.get('description', '')
        if description:
            output_lines.append(f"Description: {description}")

        return '\n'.join(output_lines)
