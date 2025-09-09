"""
Browser-based HTML Fetcher Module

Handles dynamic content loading using Selenium WebDriver.
Provides fallback mechanisms and content quality detection.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserFetcher:
    """
    Handles dynamic content fetching using headless browsers.
    """

    def __init__(self, browser: str = "chrome", headless: bool = True,
                 wait_time: int = 5, scroll_attempts: int = 3,
                 max_scroll_wait: int = 2):
        """
        Initialize the browser fetcher.

        Args:
            browser: Browser to use ('chrome' or 'firefox')
            headless: Run in headless mode
            wait_time: Initial wait time after page load (seconds)
            scroll_attempts: Number of scroll attempts for infinite scroll
            max_scroll_wait: Wait time between scrolls (seconds)
        """
        self.browser = browser.lower()
        self.headless = headless
        self.wait_time = wait_time
        self.scroll_attempts = scroll_attempts
        self.max_scroll_wait = max_scroll_wait
        self.driver = None

    def __enter__(self):
        """Context manager entry."""
        self._setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._cleanup_driver()

    def _setup_driver(self):
        """Set up the WebDriver instance."""
        try:
            if self.browser == "chrome":
                options = ChromeOptions()
                if self.headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

                service = ChromeService(ChromeDriverManager(chrome_binary_path="/usr/bin/chrome").install())
                self.driver = webdriver.Chrome(service=service, options=options)

            elif self.browser == "firefox":
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                options.set_preference("general.useragent.override",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")

                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)

            else:
                raise ValueError(f"Unsupported browser: {self.browser}")

            # Set implicit wait
            self.driver.implicitly_wait(10)

        except Exception as e:
            logger.error(f"Failed to setup {self.browser} driver: {e}")
            raise

    def _cleanup_driver(self):
        """Clean up the WebDriver instance."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error cleaning up driver: {e}")
            finally:
                self.driver = None

    def fetch_page(self, url: str, scroll_for_content: bool = True) -> Tuple[str, Dict[str, Any]]:
        """
        Fetch page content using browser automation.

        Args:
            url: URL to fetch
            scroll_for_content: Whether to scroll for additional content

        Returns:
            Tuple of (html_content, metadata_dict)
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use as context manager.")

        metadata = {
            'url': url,
            'browser': self.browser,
            'headless': self.headless,
            'dynamic_content_loaded': False,
            'scroll_attempts_made': 0,
            'page_load_time': 0,
            'final_scroll_height': 0,
            'error': None
        }

        try:
            start_time = time.time()

            # Navigate to the page
            logger.info(f"Fetching {url} with {self.browser}")
            self.driver.get(url)

            # Wait for initial page load
            time.sleep(self.wait_time)

            # Try to wait for body element
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for body element")

            initial_height = self.driver.execute_script("return document.body.scrollHeight")

            # Scroll for additional content if enabled
            if scroll_for_content:
                final_height = self._scroll_for_content()
                metadata['scroll_attempts_made'] = self.scroll_attempts
                metadata['final_scroll_height'] = final_height

                if final_height > initial_height:
                    metadata['dynamic_content_loaded'] = True
                    logger.info(f"Dynamic content loaded: {initial_height} → {final_height} pixels")

            # Get final page source
            html_content = self.driver.page_source
            metadata['page_load_time'] = time.time() - start_time

            logger.info(".2f")
            return html_content, metadata

        except Exception as e:
            error_msg = f"Browser fetch failed: {str(e)}"
            logger.error(error_msg)
            metadata['error'] = error_msg
            return "", metadata

    def _scroll_for_content(self) -> int:
        """
        Scroll the page to load dynamic content.

        Returns:
            Final scroll height
        """
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for attempt in range(self.scroll_attempts):
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for content to load
            time.sleep(self.max_scroll_wait)

            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # Break if no new content loaded
            if new_height == last_height:
                break

            last_height = new_height

        return last_height


class ContentQualityDetector:
    """
    Detects if content appears to be dynamically loaded and incomplete.
    """

    @staticmethod
    def needs_dynamic_rendering(html_content: str, url: str = "") -> bool:
        """
        Determine if content likely needs dynamic rendering.

        Args:
            html_content: Static HTML content
            url: Source URL (for additional heuristics)

        Returns:
            True if dynamic rendering is recommended
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Check for common indicators of dynamic content
        indicators = []

        # 1. Empty or minimal content containers
        content_selectors = ['.content', '.post', '.article', '.entry', '.main-content',
                           '#content', '#main', '.container', '.wrapper']

        empty_containers = 0
        for selector in content_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text_content = element.get_text(strip=True)
                    if len(text_content) < 50:  # Very little content
                        empty_containers += 1
            except:
                continue

        if empty_containers > 2:
            indicators.append(f"{empty_containers} empty content containers")

        # 2. Loading indicators or placeholders
        loading_text = ['loading', 'loading...', 'please wait', 'loading content',
                       'no content', 'content not available', 'empty']

        text_content = soup.get_text().lower()
        loading_matches = sum(1 for text in loading_text if text in text_content)

        if loading_matches > 0:
            indicators.append(f"{loading_matches} loading indicators found")

        # 3. JavaScript-dependent content patterns
        js_patterns = [
            r'document\.getElementById',
            r'document\.querySelector',
            r'fetch\(',
            r'XMLHttpRequest',
            r'\$\.ajax',
            r'\$\.get'
        ]

        scripts = soup.find_all('script')
        js_indicators = 0
        for script in scripts:
            script_content = script.get_text()
            for pattern in js_patterns:
                if re.search(pattern, script_content, re.IGNORECASE):
                    js_indicators += 1
                    break

        if js_indicators > 0:
            indicators.append(f"{js_indicators} JavaScript data-loading patterns")

        # 4. Lazy loading attributes
        lazy_elements = soup.find_all(attrs={'data-src': True})
        if len(lazy_elements) > 3:
            indicators.append(f"{len(lazy_elements)} lazy-loaded images")

        # 5. Infinite scroll indicators
        scroll_indicators = ['infinite', 'scroll', 'load-more', 'show-more', 'next-page']
        for indicator in scroll_indicators:
            if indicator.lower() in text_content:
                indicators.append(f"Infinite scroll indicator: '{indicator}'")
                break

        # 6. Content length check
        total_text = len(text_content)
        if total_text < 500:  # Very little text content
            indicators.append(f"Very low text content: {total_text} characters")

        # Decision logic
        indicator_count = len(indicators)
        needs_dynamic = indicator_count >= 2  # Require at least 2 indicators

        if needs_dynamic:
            logger.info(f"Dynamic rendering recommended for {url}: {', '.join(indicators)}")

        return needs_dynamic

    @staticmethod
    def compare_content_quality(static_html: str, dynamic_html: str) -> Dict[str, Any]:
        """
        Compare static vs dynamic content quality.

        Args:
            static_html: Content from static fetch
            dynamic_html: Content from browser fetch

        Returns:
            Dictionary with comparison metrics
        """
        static_soup = BeautifulSoup(static_html, 'html.parser')
        dynamic_soup = BeautifulSoup(dynamic_html, 'html.parser')

        # Extract text content
        static_text = static_soup.get_text()
        dynamic_text = dynamic_soup.get_text()

        # Calculate metrics
        metrics = {
            'static_length': len(static_text),
            'dynamic_length': len(dynamic_text),
            'length_improvement': len(dynamic_text) - len(static_text),
            'percentage_improvement': 0,
            'better_quality': False
        }

        if metrics['static_length'] > 0:
            metrics['percentage_improvement'] = (metrics['length_improvement'] / metrics['static_length']) * 100

        # Determine if dynamic content is significantly better
        min_improvement = 0.20  # 20% improvement threshold
        min_absolute_improvement = 200  # Minimum 200 characters improvement

        metrics['better_quality'] = (
            metrics['percentage_improvement'] > min_improvement or
            metrics['length_improvement'] > min_absolute_improvement
        )

        return metrics


def fetch_with_fallback(url: str, browser_config: Dict[str, Any],
                       static_timeout: int = 30) -> Tuple[str, Dict[str, Any]]:
    """
    Fetch content with intelligent fallback from static to dynamic.

    Args:
        url: URL to fetch
        browser_config: Browser configuration dictionary
        static_timeout: Timeout for static fetch attempt

    Returns:
        Tuple of (html_content, metadata_dict)
    """
    import requests

    metadata = {
        'url': url,
        'fetch_method': 'unknown',
        'fetch_time': 0,
        'content_length': 0,
        'dynamic_rendering_used': False,
        'quality_improvement': 0,
        'error': None
    }

    start_time = time.time()

    try:
        # First attempt: Static fetch
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=static_timeout)
        response.raise_for_status()
        static_html = response.text

        metadata['fetch_method'] = 'static'
        metadata['content_length'] = len(static_html)
        metadata['fetch_time'] = time.time() - start_time

        # Check if dynamic rendering is needed
        if ContentQualityDetector.needs_dynamic_rendering(static_html, url):
            logger.info(f"Dynamic rendering detected as needed for {url}")

            # Second attempt: Browser fetch
            try:
                with BrowserFetcher(**browser_config) as fetcher:
                    dynamic_html, browser_metadata = fetcher.fetch_page(url)

                    if dynamic_html and not browser_metadata.get('error'):
                        # Compare content quality
                        quality_metrics = ContentQualityDetector.compare_content_quality(static_html, dynamic_html)

                        if quality_metrics['better_quality']:
                            metadata.update({
                                'fetch_method': 'dynamic',
                                'dynamic_rendering_used': True,
                                'quality_improvement': quality_metrics['percentage_improvement'],
                                'content_length': len(dynamic_html),
                                'browser_metadata': browser_metadata
                            })
                            metadata['fetch_time'] = time.time() - start_time
                            logger.info(".1f")
                            return dynamic_html, metadata
                        else:
                            logger.info("Dynamic content not significantly better, using static")

            except Exception as e:
                logger.warning(f"Browser fetch failed, falling back to static: {e}")

        # Return static content
        return static_html, metadata

    except requests.RequestException as e:
        error_msg = f"Static fetch failed: {str(e)}"

        # Last resort: Try browser fetch
        try:
            with BrowserFetcher(**browser_config) as fetcher:
                dynamic_html, browser_metadata = fetcher.fetch_page(url)

                if dynamic_html and not browser_metadata.get('error'):
                    metadata.update({
                        'fetch_method': 'dynamic_fallback',
                        'dynamic_rendering_used': True,
                        'content_length': len(dynamic_html),
                        'browser_metadata': browser_metadata,
                        'error': error_msg
                    })
                    metadata['fetch_time'] = time.time() - start_time
                    return dynamic_html, metadata

        except Exception as browser_error:
            metadata['error'] = f"Both static and browser fetch failed: {error_msg} | {str(browser_error)}"

    except Exception as e:
        metadata['error'] = f"Unexpected error: {str(e)}"

    metadata['fetch_time'] = time.time() - start_time
    return "", metadata
