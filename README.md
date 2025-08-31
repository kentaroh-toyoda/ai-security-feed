# Web Article Collection Agent

A Python tool that collects articles from RSS feeds and custom websites, summarizes them using Large Language Models (LLMs), and generates consolidated RSS feeds.

## Features

- 🔍 **Auto-Detection**: Automatically detects RSS feeds vs custom websites
- 🤖 **LLM Integration**: Uses OpenRouter/LiteLLM for article extraction and summarization
- 📊 **Smart Processing**: Handles both RSS/ATOM feeds and custom HTML pages
- 🏷️ **Topic Classification**: LLM-powered categorization of articles
- 📱 **RSS Generation**: Creates standards-compliant RSS feeds
- ⚡ **Batch Processing**: Efficiently processes multiple sources
- 📈 **Progress Tracking**: Real-time progress bars and statistics

## Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

## Configuration

Create a `.env` file with your LLM settings:

```env
# Required
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-3.5-turbo
LLM_API_KEY=your_api_key_here

# Optional
REQUEST_TIMEOUT=30
MAX_ARTICLES_PER_SOURCE=50
OUTPUT_FILE=articles.rss

# Page Loading (for dynamic content)
ENABLE_PAGE_LOAD_WAIT=true
PAGE_LOAD_WAIT_TIME=30
```

### Page Loading Configuration

Some websites use JavaScript or AJAX to load content dynamically after the initial page load. The page loading configuration allows you to wait for this dynamic content to load before processing:

- **`ENABLE_PAGE_LOAD_WAIT`**: Enable/disable waiting for dynamic content (default: `true`)
- **`PAGE_LOAD_WAIT_TIME`**: Seconds to wait before processing page content (default: `30`)

**Why this matters:**
- Websites like https://sgaisi.sg/resources load content via JavaScript
- Without waiting, you might only get the initial HTML without the actual article content
- The 30-second default provides time for most dynamic content to load
- You can adjust this based on the specific websites you're collecting from

### Browser-based Dynamic Content Fetching

For websites that heavily rely on JavaScript to load content (infinite scroll, lazy loading, AJAX), the tool now includes intelligent browser automation:

```env
# Enable browser fetching for dynamic content
BROWSER_ENABLED=true
BROWSER_TYPE=chrome
BROWSER_HEADLESS=true
BROWSER_WAIT_TIME=5
BROWSER_SCROLL_ATTEMPTS=3
```

**Key Features:**
- **Intelligent Detection**: Automatically detects when dynamic rendering is needed
- **Quality Comparison**: Compares static vs. browser-rendered content and uses the better version
- **Fallback Strategy**: Tries static fetch first (fast), falls back to browser only when necessary
- **Infinite Scroll Support**: Automatically scrolls pages to load additional content
- **Performance Optimized**: Only uses browser when content analysis indicates it's needed

**When it's useful:**
- News sites with infinite scroll (e.g., Twitter/X, Reddit)
- Content loaded via AJAX/API calls
- Single-page applications (SPAs)
- Sites with lazy-loaded images or content
- Any site where initial HTML lacks the actual article content

### Supported LLM Providers

- **OpenRouter** (recommended): Access to 100+ models
- **OpenAI**: GPT-3.5, GPT-4
- **Anthropic**: Claude models
- **Local models**: Ollama, LM Studio
- **And many more** via LiteLLM

## Usage

### 1. Create Sources File

Create a `sources.json` file with your article sources:

```json
[
  {
    "url": "https://example-blog.com/rss.xml"
    "name": "Website A"
  },
  {
    "url": "https://tech-site.com",
    "name": "Website B"
  },
  {
    "url": "https://news-site.com/feed",
    "name": "Website C"
  }
]
```

**Note**: The `type` field is optional - the tool will auto-detect RSS feeds.

### 2. Run Article Collection

```bash
# Basic usage
python main.py sources.json

# With custom output
python main.py sources.json --output my-feed.rss

# Skip LLM processing
python main.py sources.json --no-llm

# Limit articles per source
python main.py sources.json --max-articles 10

# Validate sources file
python main.py sources.json --validate-only
```

### 3. View Results

The tool generates:
- **RSS Feed**: `articles.rss` (or your specified output file)
- **Statistics**: Source counts, categories, date ranges
- **Validation**: Confirms RSS feed is well-formed

## Command Line Options

```
Usage: python main.py [OPTIONS] SOURCES_FILE

Arguments:
  sources_file  Path to JSON file containing source URLs

Options:
  -o, --output TEXT           Output RSS file path
  --no-llm                    Skip LLM processing (no summaries or categories)
  -m, --max-articles INTEGER  Maximum articles per source
  --create-sample             Create a sample sources.json file and exit
  --validate-only             Only validate the sources file format
  --help                      Show this message and exit
```

## Output RSS Format

The generated RSS feed includes:

```xml
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Web Article Collection</title>
    <item>
      <title>Article Title</title>
      <link>https://source.com/article</link>
      <description>LLM-generated summary...</description>
      <category>Technology</category>
      <category>AI</category>
      <pubDate>Wed, 29 Aug 2025 12:00:00 GMT</pubDate>
      <source url="https://source.com">Source Name</source>
    </item>
    <!-- More items... -->
  </channel>
</rss>
```

## How It Works

1. **Source Detection**: Automatically determines if URLs are RSS feeds or custom pages
2. **Content Extraction**:
   - RSS feeds: Parsed directly using feedparser
   - Custom pages: HTML fetched and analyzed by LLM to extract articles
3. **Article Processing**: Each article is summarized and categorized by LLM
4. **RSS Generation**: All articles combined into a single, standards-compliant RSS feed

## Supported Source Types

### RSS/ATOM Feeds
- Standard RSS 2.0 and Atom feeds
- Auto-detected by content-type and XML structure
- Supports all major feed formats

### Custom Websites
- Any HTML webpage containing articles
- LLM extracts article information from page content
- Handles various website structures and layouts

## Examples

### Example 1: Tech News Aggregation

```json
[
  {"url": "https://techcrunch.com/rss"},
  {"url": "https://arstechnica.com/rss"},
  {"url": "https://news.ycombinator.com/rss"}
]
```

### Example 2: Blog Collection

```json
[
  {"url": "https://example-blog.com"},
  {"url": "https://another-blog.com/feed"},
  {"url": "https://tech-blog.net/rss.xml"}
]
```

## Troubleshooting

### Common Issues

1. **LLM API Errors**: Check your API key and quota in `.env`
2. **Empty RSS Feed**: Sources may not have recent articles or be inaccessible
3. **Slow Processing**: Reduce `--max-articles` or add delays between requests
4. **Invalid JSON**: Use `--validate-only` to check your sources file

### Debug Mode

Add logging to see detailed processing:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Requirements

- Python 3.8+
- Internet connection for fetching sources
- LLM API access (OpenRouter, OpenAI, etc.)

## License

MIT License - feel free to use and modify.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues or questions:
1. Check the troubleshooting section
2. Validate your sources file with `--validate-only`
3. Test with a single source first
4. Check API provider status and qu
