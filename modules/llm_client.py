import requests
from typing import List, Dict, Optional, Tuple
from config import config
import json
import os
from modules.html_processor import preprocess_html_for_llm

class LLMClient:
    """Client for LLM operations using direct API calls"""

    def __init__(self, verbose: bool = False):
        self.provider = config.llm.provider
        self.model = config.llm.model
        self.api_key = config.llm.api_key
        self.base_url = config.llm.base_url
        self.temperature = config.llm.temperature
        self.timeout = config.request_timeout
        self.verbose = verbose
        # Increase max tokens for URL filtering to prevent truncation
        self.max_tokens = max(config.llm.max_tokens, 4096)  # Minimum 2000 tokens

    def _call_openrouter(self, prompt: str, system_message: str = "") -> str:
        """Direct call to OpenRouter API"""
        try:
            if self.verbose:
                print("🔗 OpenRouter API Call Debug:")
                print(f"   Model: {self.model}")
                print(f"   API Key present: {'Yes' if self.api_key else 'No'}")
                print(f"   Prompt length: {len(prompt)} characters")
                print(f"   System message length: {len(system_message) if system_message else 0} characters")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-domain.com",
                "X-Title": "Web Article Collection Agent"
            }

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Handle different parameter names for different providers
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature
            }

            # Use max_completion_tokens for Azure models, max_tokens for others
            if "azure" in self.model.lower():
                data["max_completion_tokens"] = self.max_tokens
                if self.verbose:
                    print(f"   Using max_completion_tokens for Azure model: {self.max_tokens}")
            else:
                data["max_tokens"] = self.max_tokens
                if self.verbose:
                    print(f"   Using max_tokens: {self.max_tokens}")

            if self.verbose:
                print(f"   Request data size: {len(str(data))} characters")

            # Use custom base URL if provided, otherwise use default OpenRouter URL
            base_url = self.base_url or "https://openrouter.ai/api/v1"
            api_url = f"{base_url}/chat/completions"
            if self.verbose:
                print(f"   Making API request to: {api_url}")

            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            if self.verbose:
                print(f"   Response status: {response.status_code}")
                print(f"   Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                if self.verbose:
                    print("   ✅ API call successful")
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                if self.verbose:
                    print(f"   Response content length: {len(content)} characters")
                return content
            else:
                if self.verbose:
                    print(f"   ❌ OpenRouter API error: {response.status_code}")
                    print(f"   Response text: {response.text}")

                    # Try to parse error details if available
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            print(f"   Error details: {error_data['error']}")
                    except:
                        pass

                return ""

        except requests.exceptions.Timeout:
            print(f"   ❌ OpenRouter call failed: Request timeout ({self.timeout}s)")
            return ""
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ OpenRouter call failed: Connection error - {e}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"   ❌ OpenRouter call failed: Request error - {e}")
            return ""
        except Exception as e:
            print(f"   ❌ OpenRouter call failed: Unexpected error - {e}")
            print(f"   Exception type: {type(e).__name__}")
            return ""

    def _call_custom_http(self, prompt: str, system_message: str = "") -> str:
        """Direct HTTP call to custom LLM endpoint"""
        try:
            if self.verbose:
                print("🔗 Custom HTTP API Call Debug:")
                print(f"   Model: {self.model}")
                print(f"   Base URL: {self.base_url}")
                print(f"   API Key present: {'Yes' if self.api_key else 'No'}")
                print(f"   Prompt length: {len(prompt)} characters")
                print(f"   System message length: {len(system_message) if system_message else 0} characters")

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Handle different parameter names for different providers
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature
            }

            # Use max_completion_tokens for Azure models, max_tokens for others
            if "azure" in self.model.lower():
                data["max_completion_tokens"] = self.max_tokens
                if self.verbose:
                    print(f"   Using max_completion_tokens for Azure model: {self.max_tokens}")
            else:
                data["max_tokens"] = self.max_tokens
                if self.verbose:
                    print(f"   Using max_tokens: {self.max_tokens}")

            if self.verbose:
                print(f"   Request data size: {len(str(data))} characters")

            # Construct the full API URL
            # Remove trailing slash from base_url if present
            base_url = self.base_url.rstrip('/')
            api_url = f"{base_url}/v1/chat/completions"
            if self.verbose:
                print(f"   Making API request to: {api_url}")

            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )

            if self.verbose:
                print(f"   Response status: {response.status_code}")
                print(f"   Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                if self.verbose:
                    print("   ✅ Custom HTTP call successful")
                result = response.json()
                content = result["choices"][0]["message"]["content"].strip()
                if self.verbose:
                    print(f"   Response content length: {len(content)} characters")
                return content
            else:
                if self.verbose:
                    print(f"   ❌ Custom HTTP API error: {response.status_code}")
                    print(f"   Response text: {response.text}")

                    # Try to parse error details if available
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            print(f"   Error details: {error_data['error']}")
                    except:
                        pass

                return ""

        except requests.exceptions.Timeout:
            print(f"   ❌ Custom HTTP call failed: Request timeout ({self.timeout}s)")
            return ""
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ Custom HTTP call failed: Connection error - {e}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Custom HTTP call failed: Request error - {e}")
            return ""
        except Exception as e:
            print(f"   ❌ Custom HTTP call failed: Unexpected error - {e}")
            print(f"   Exception type: {type(e).__name__}")
            return ""

    def _call_litellm(self, prompt: str, system_message: str = "") -> str:
        """Fallback to LiteLLM for other providers"""
        try:
            import litellm
            litellm.drop_params = True

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            # Prepare completion parameters
            completion_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "api_key": self.api_key
            }

            # Add custom base URL if provided
            if self.base_url:
                completion_params["base_url"] = self.base_url

            response = litellm.completion(**completion_params)

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"LiteLLM call failed: {e}")
            return ""

    def _call_llm(self, prompt: str, system_message: str = "") -> str:
        """Route to appropriate LLM provider"""
        if self.provider.lower() == "openrouter":
            return self._call_openrouter(prompt, system_message)
        elif self.base_url:
            # Use direct HTTP for custom base URLs
            return self._call_custom_http(prompt, system_message)
        else:
            # Fall back to LiteLLM for standard providers
            return self._call_litellm(prompt, system_message)

    def extract_articles_from_html(self, html_content: str, url: str, html_format: str = 'markdown') -> List[Dict]:
        """
        Extract articles from HTML content using LLM.

        This method now uses the improved workflow:
        1. Preprocess HTML to specified format (markdown or simple_tags)
        2. Extract articles from the content using specialized parsing

        Args:
            html_content: The HTML content of the webpage
            url: The source URL
            html_format: HTML preprocessing format ('markdown' or 'simple_tags')

        Returns:
            List of article dictionaries with title, link, content, etc.
        """
        # Preprocess HTML to specified format for better structure preservation
        processed_content = preprocess_html_for_llm(html_content, max_length=6000, preprocessed_format=html_format)

        # Extract articles from the processed content using the appropriate method
        return self.extract_articles_from_content(processed_content, url, content_format=html_format)

    def extract_articles_from_markdown(self, markdown_content: str, url: str) -> List[Dict]:
        """
        Extract articles from markdown content using LLM.

        Args:
            markdown_content: The markdown content of the webpage
            url: The source URL

        Returns:
            List of article dictionaries with title, link, content, etc.
        """
        system_message = """You are an expert at extracting article information from markdown content.
        Given markdown content with headings (# ## ###) and structured text, identify and extract individual articles or blog posts.
        Pay special attention to the heading hierarchy to understand article structure and relationships.
        Return the information in JSON format."""

        prompt = f"""
        Analyze this markdown content from {url} and extract all articles/blog posts you can find.

        The content uses markdown formatting:
        - # for main headings (usually page title)
        - ## for section headings
        - ### for article titles
        - Regular paragraphs for content

        For each article, extract:
        - title: The article headline (usually from ### headings)
        - link: The URL to the full article (look for [URL: /path/to/article] markers)
        - content: A brief excerpt or summary from the following paragraphs
        - published_date: Publication date if available (ISO format or human readable)

        Return ONLY a JSON array of objects with these fields. If no articles are found, return an empty array.
        Focus on actual articles, not navigation items or advertisements.

        IMPORTANT: Look for article links in the format "Article Title [URL: /path/to/article]" in the markdown content.
        Use these URLs when extracting articles to ensure you capture the correct link for each article.

        Markdown Content:
        {markdown_content}

        JSON Response:"""

        response = self._call_llm(prompt, system_message)

        try:
            # Clean the response to extract JSON
            json_start = response.find('[')
            json_end = response.rfind(']') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                articles = json.loads(json_str)

                # Validate and clean the articles
                cleaned_articles = []
                for article in articles:
                    if isinstance(article, dict) and article.get('title'):
                        # Set default values and clean data
                        cleaned_article = {
                            'title': article.get('title', '').strip(),
                            'link': article.get('link', url),
                            'content': article.get('content', '').strip(),
                            'published_date': article.get('published_date', ''),
                            'source_url': url
                        }
                        cleaned_articles.append(cleaned_article)

                return cleaned_articles

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response}")

        return []

    def extract_articles_from_content(self, content: str, url: str, content_format: str = 'markdown') -> List[Dict]:
        """
        Extract articles from content using LLM, adapting to the content format.

        Args:
            content: The processed content (markdown or HTML with simple tags)
            url: The source URL
            content_format: Format of the content ('markdown' or 'simple_tags')

        Returns:
            List of article dictionaries with title, link, content, etc.
        """
        if content_format == 'simple_tags':
            # Use HTML-specific prompts and instructions
            system_message = """You are an expert at extracting article information from HTML content with simple tags.
            Given HTML content with tags like <h1>, <h2>, <h3>, <p>, <a href="...">, identify and extract individual articles or blog posts.
            Pay special attention to heading hierarchy and link structures.
            Return the information in JSON format."""

            prompt = f"""
            Analyze this HTML content from {url} and extract all articles/blog posts you can find.

            The content uses simple HTML tags:
            - <h1>, <h2>, <h3>, <h4>, <h5>, <h6> for headings
            - <p> for paragraphs
            - <a href="..."> for links
            - <div> for content sections

            For each article, extract:
            - title: The article headline (usually from <h1>, <h2>, or <h3> tags)
            - link: The URL to the full article (look for href attributes in <a> tags or [URL: /path/to/article] markers)
            - content: A brief excerpt or summary from the following <p> tags
            - published_date: Publication date if available (ISO format or human readable)

            Return ONLY a JSON array of objects with these fields. If no articles are found, return an empty array.
            Focus on actual articles, not navigation items or advertisements.

            IMPORTANT: Look for article links in <a href="..."> tags or "Article Title [URL: /path/to/article]" patterns.
            Use these URLs when extracting articles to ensure you capture the correct link for each article.

            HTML Content:
            {content}

            JSON Response:"""
        else:
            # Use markdown prompts (existing logic)
            system_message = """You are an expert at extracting article information from markdown content.
            Given markdown content with headings (# ## ###) and structured text, identify and extract individual articles or blog posts.
            Pay special attention to the heading hierarchy to understand article structure and relationships.
            Return the information in JSON format."""

            prompt = f"""
            Analyze this markdown content from {url} and extract all articles/blog posts you can find.

            The content uses markdown formatting:
            - # for main headings (usually page title)
            - ## for section headings
            - ### for article titles
            - Regular paragraphs for content

            For each article, extract:
            - title: The article headline (usually from ### headings)
            - link: The URL to the full article (look for [URL: /path/to/article] markers)
            - content: A brief excerpt or summary from the following paragraphs
            - published_date: Publication date if available (ISO format or human readable)

            Return ONLY a JSON array of objects with these fields. If no articles are found, return an empty array.
            Focus on actual articles, not navigation items or advertisements.

            IMPORTANT: Look for article links in the format "Article Title [URL: /path/to/article]" in the markdown content.
            Use these URLs when extracting articles to ensure you capture the correct link for each article.

            Markdown Content:
            {content}

            JSON Response:"""

        response = self._call_llm(prompt, system_message)

        try:
            # Clean the response to extract JSON
            json_start = response.find('[')
            json_end = response.rfind(']') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                articles = json.loads(json_str)

                # Validate and clean the articles
                cleaned_articles = []
                for article in articles:
                    if isinstance(article, dict) and article.get('title'):
                        # Set default values and clean data
                        cleaned_article = {
                            'title': article.get('title', '').strip(),
                            'link': article.get('link', url),
                            'content': article.get('content', '').strip(),
                            'published_date': article.get('published_date', ''),
                            'source_url': url
                        }
                        cleaned_articles.append(cleaned_article)

                return cleaned_articles

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            print(f"Raw response: {response}")

        return []

    def summarize_and_categorize_article(self, title: str, content: str) -> Tuple[str, List[str]]:
        """
        Generate a summary and determine categories for an article.

        Args:
            title: Article title
            content: Article content

        Returns:
            Tuple of (summary, list_of_categories)
        """
        system_message = """You are an expert at summarizing articles and categorizing content.
        Provide concise, informative summaries and relevant categories."""

        prompt = f"""
        Analyze this article and provide:

        1. A concise summary (2-3 sentences)
        2. Relevant categories/topics (3-5 categories)

        Article Title: {title}

        Article Content:
        {content[:4000]}

        Respond in JSON format:
        {{
            "summary": "your summary here",
            "categories": ["category1", "category2", "category3"]
        }}
        """

        response = self._call_llm(prompt, system_message)

        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)

                summary = result.get('summary', '').strip()
                categories = result.get('categories', [])

                # Ensure we have valid data
                if not summary:
                    summary = content[:300] + "..." if len(content) > 300 else content

                if not categories:
                    categories = ["General"]

                return summary, categories

        except json.JSONDecodeError as e:
            print(f"Failed to parse summary response: {e}")

        # Fallback
        summary = content[:300] + "..." if len(content) > 300 else content
        return summary, ["General"]

    def filter_blog_urls(self, urls_data: List[Dict]) -> List[Dict]:
        """
        Use LLM to filter URLs and keep only those likely to be blog or article content.

        Args:
            urls_data: List of URL dictionaries with keys: url, text, etc.

        Returns:
            Filtered list of blog/article URLs only
        """
        if not urls_data:
            return []

        if self.verbose:
            print("🔍 LLM URL FILTERING DEBUG INFO:")
            print(f"   Provider: {self.provider}")

            # Show which method will be used
            if self.provider.lower() == "openrouter":
                method = "OpenRouter API"
            elif self.base_url:
                method = "Custom HTTP"
            else:
                method = "LiteLLM"

            print(f"   Method: {method}")
            print(f"   Model: {self.model}")
            print(f"   Base URL: {self.base_url or 'Default (not set)'}")
            print(f"   Temperature: {self.temperature}")
            print(f"   Max tokens: {self.max_tokens}")
            print(f"   URLs to filter: {len(urls_data)}")
            print(f"   API Key configured: {'Yes' if self.api_key else 'No'}")

        system_message = """You are an expert at identifying blog posts, articles, and content-rich web pages.
        Analyze URLs and their associated text to determine if they likely contain blog posts, articles, tutorials, guides, or other substantial content.
        Focus on content quality and relevance, not just URL patterns."""

        # Format URLs for LLM analysis
        urls_text = "\n".join([
            f"{i+1}. Title: \"{url_info.get('text', '')}\" | URL: {url_info.get('url', '')}"
            for i, url_info in enumerate(urls_data)
        ])

        prompt = f"""
        Analyze this list of URLs and their titles/text. Identify which ones are MOST LIKELY to contain blog posts, articles, tutorials, guides, or other substantial content.

        For each URL, consider:
        - URL patterns: /blog/, /article/, /news/, /guide/, /tutorial/, /2024/, /2023/, etc.
        - Title semantics: "guide", "tutorial", "analysis", "breaking news", "how-to", "tips"
        - Content indicators: dates, article-like language, educational terms
        - Exclude: navigation pages (home, about, contact), social media, admin pages

        CRITICAL: Return your response as a JSON array of STRINGS containing ONLY the URLs.
        Do NOT return objects with url/text properties. Return ONLY the URL strings.

        REQUIRED FORMAT:
        [
          "./blog/example-article",
          "./blog/another-article"
        ]

        IMPORTANT: Be inclusive of date-based content (even without explicit "blog" in URL) and content-rich pages.

        URLs to analyze:
        {urls_text}

        Return ONLY a valid JSON array of URL strings:
        """

        if self.verbose:
            print(f"   Prompt length: {len(prompt)} characters")
            print(f"   System message length: {len(system_message)} characters")

        response = self._call_llm(prompt, system_message)

        if self.verbose:
            print(f"   LLM response received: {'Yes' if response else 'No'}")
            print(f"   Response length: {len(response) if response else 0} characters")

            if response:
                print(f"   Full response content ({len(response)} characters):")
                print(f"   {response}")
                print(f"   Response starts with: {response[:50]}...")
                print(f"   Response ends with: ...{response[-50:]}")

        try:
            # Parse JSON response
            json_start = response.find('[')
            json_end = response.rfind(']') + 1

            if self.verbose:
                print(f"   JSON parsing: json_start={json_start}, json_end={json_end}")

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                if self.verbose:
                    print(f"   Extracted JSON string length: {len(json_str)}")
                    print(f"   JSON string: {json_str[:200]}{'...' if len(json_str) > 200 else ''}")

                filtered_urls = json.loads(json_str)

                # Validate that we got back the expected format (array of strings)
                if isinstance(filtered_urls, list):
                    if self.verbose:
                        print(f"   Successfully parsed {len(filtered_urls)} URLs from LLM response")

                    # Create a lookup map for faster URL matching
                    url_map = {url_info['url']: url_info for url_info in urls_data}

                    # Filter to ensure we only return URLs that were in the original list
                    validated_urls = []
                    for url_string in filtered_urls:
                        if isinstance(url_string, str) and url_string in url_map:
                            validated_urls.append(url_map[url_string])

                    if self.verbose:
                        print(f"   After validation: {len(validated_urls)} URLs retained")
                    return validated_urls
                else:
                    if self.verbose:
                        print(f"   ERROR: LLM response is not a list, got {type(filtered_urls)}")
            else:
                if self.verbose:
                    print("   ERROR: Could not find JSON array markers in response")

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            if self.verbose:
                print(f"   ERROR: Failed to parse LLM URL filtering response: {e}")
                print(f"   Exception type: {type(e).__name__}")
                if hasattr(e, 'pos'):
                    print(f"   Error position: {e.pos}")
                if hasattr(e, 'lineno'):
                    print(f"   Error line: {e.lineno}")
                if hasattr(e, 'colno'):
                    print(f"   Error column: {e.colno}")

        except Exception as e:
            if self.verbose:
                print(f"   ERROR: Unexpected error during URL filtering: {e}")
                print(f"   Exception type: {type(e).__name__}")

        # Fallback: return all URLs if LLM filtering fails
        if self.verbose:
            print("   FALLBACK: LLM filtering failed, returning all URLs")
            print("   END DEBUG INFO")
        return urls_data

# Global LLM client instance - will be updated with verbose flag when needed
llm_client = None
