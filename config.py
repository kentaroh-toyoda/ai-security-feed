import os
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LLMConfig:
    """Configuration for LLM services"""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openrouter"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "openai/gpt-4.1-mini"))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    base_url: Optional[str] = field(default_factory=lambda: os.getenv("LLM_BASE_URL"))
    temperature: float = 0.3
    max_tokens: int = 4096

@dataclass
class BrowserConfig:
    """Configuration for browser-based fetching"""
    enabled: bool = field(default_factory=lambda: os.getenv("BROWSER_ENABLED", "true").lower() == "true")
    browser: str = field(default_factory=lambda: os.getenv("BROWSER_TYPE", "chrome"))
    headless: bool = field(default_factory=lambda: os.getenv("BROWSER_HEADLESS", "true").lower() == "true")
    wait_time: int = field(default_factory=lambda: int(os.getenv("BROWSER_WAIT_TIME", "5")))
    scroll_attempts: int = field(default_factory=lambda: int(os.getenv("BROWSER_SCROLL_ATTEMPTS", "3")))
    max_scroll_wait: int = field(default_factory=lambda: int(os.getenv("BROWSER_MAX_SCROLL_WAIT", "2")))
    static_timeout: int = field(default_factory=lambda: int(os.getenv("STATIC_FETCH_TIMEOUT", "30")))

@dataclass
class FullContentConfig:
    """Configuration for full content fetching"""
    enabled: bool = field(default_factory=lambda: os.getenv("FETCH_FULL_CONTENT", "false").lower() == "true")
    request_delay: float = field(default_factory=lambda: float(os.getenv("REQUEST_DELAY", "3.0")))
    max_article_pages: int = field(default_factory=lambda: int(os.getenv("MAX_ARTICLE_PAGES", "50")))
    skip_existing: bool = field(default_factory=lambda: os.getenv("SKIP_EXISTING_FULL_CONTENT", "true").lower() == "true")

@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database"""
    enabled: bool = field(default_factory=lambda: os.getenv("QDRANT_ENABLED", "false").lower() == "true")
    url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", ""))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("QDRANT_API_KEY"))
    collection: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "web-articles"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    embedding_dimension: int = field(default_factory=lambda: int(os.getenv("EMBEDDING_DIMENSION", "384")))
    batch_size: int = field(default_factory=lambda: int(os.getenv("QDRANT_BATCH_SIZE", "32")))

@dataclass
class AppConfig:
    """Main application configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    full_content: FullContentConfig = field(default_factory=FullContentConfig)
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    request_timeout: int = 120
    max_articles_per_source: int = 1000
    output_file: str = "articles.rss"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    page_load_wait_time: int = field(default_factory=lambda: int(os.getenv("PAGE_LOAD_WAIT_TIME", "10")))
    enable_page_load_wait: bool = field(default_factory=lambda: os.getenv("ENABLE_PAGE_LOAD_WAIT", "true").lower() == "true")

# Global config instance
config = AppConfig()
