# Web Article Collection Agent

A tool to collect articles from RSS feeds and custom websites, summarize them using LLM, and generate RSS feeds.

## Features

- RSS feed processing
- Custom website scraping with intelligent content detection
- LLM-powered article summarization and categorization
- Qdrant vector database integration for semantic search
- Automated GitLab CI/CD pipeline

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the collector
python main.py sources.json
```

## GitLab CI/CD Setup

This project includes automated GitLab CI/CD configuration to run the article collection every 5 AM Singapore Time (21:00 UTC).

### Required GitLab CI/CD Variables

Set up the following variables in your GitLab project settings (Settings > CI/CD > Variables):

#### Required Variables
- `LLM_API_KEY` - Your LLM provider API key (masked)
- `LLM_PROVIDER` - LLM provider (e.g., "openrouter", "openai")
- `LLM_MODEL` - Model name (e.g., "openai/gpt-4o-mini")

#### Optional Variables
- `QDRANT_ENABLED` - Enable Qdrant vector storage (default: "false")
- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant API key (masked)
- `FETCH_FULL_CONTENT` - Enable full content fetching (default: "false")
- `GITHUB_TOKEN` - GitHub Personal Access Token for committing to GitHub repository (masked)

### Setting up the Schedule

1. Go to your GitLab project
2. Navigate to **CI/CD > Schedules**
3. Click **New schedule**
4. Set the following:
   - **Description**: "Daily article collection at 5 AM SGT"
   - **Interval Pattern**: `0 21 * * *` (runs at 21:00 UTC daily)
   - **Cron Timezone**: Leave as UTC (the cron pattern accounts for timezone)
   - **Target Branch**: `main`
5. Save the schedule

### GitHub Repository Integration

The pipeline is configured to commit the generated `articles.rss` feed to a separate GitHub repository:

- **GitHub Repository**: `https://github.com/kentaroh-toyoda/ai-security-feed`
- **Target Branch**: `gh-pages` (optimized for GitHub Pages hosting)
- **Authentication**: Uses GitHub Personal Access Token (`GITHUB_TOKEN`)

This setup allows you to:
- Keep source code in GitLab (private/internal)
- Publish the RSS feed publicly on GitHub
- Use GitHub Pages to host the feed
- Maintain separate version control for the feed

### Pipeline Overview

The CI/CD pipeline includes:

1. **Scheduled Run** (`scheduled_run`) - Executes every 5 AM SGT
2. **Manual Run** (`manual_run`) - For testing on main/develop branches
3. **Commit Changes** (`commit_changes`) - Commits updated `articles.rss` to GitHub repository
4. **Failure Notification** (`notify_failure`) - Alerts on pipeline failures

### Testing the Pipeline

Before enabling the scheduled run:

1. Remove the `when: manual` line from the `scheduled_run` job in `.gitlab-ci.yml`
2. Push the changes to trigger a manual pipeline run
3. Verify the pipeline completes successfully
4. Re-enable the schedule

## Configuration

The application uses environment variables for configuration. See `.env.example` for all available options.

### Key Configuration Options

- **Browser Automation**: Enable headless Chrome for dynamic content
- **LLM Integration**: Support for multiple providers (OpenRouter, OpenAI, etc.)
- **Content Processing**: Configurable article limits and processing options
- **Storage**: Optional Qdrant vector database integration

## Project Structure

```
.
├── main.py                 # Main application entry point
├── config.py              # Configuration management
├── sources.json           # RSS feed sources configuration
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── .gitlab-ci.yml       # GitLab CI/CD pipeline
├── modules/              # Core application modules
│   ├── rss_processor.py  # RSS feed processing
│   ├── html_processor.py # HTML content extraction
│   ├── llm_client.py     # LLM integration
│   └── qdrant_storage.py # Vector database storage
└── examples/             # Example scripts and utilities
```

## Usage Examples

### Basic Usage
```bash
python main.py sources.json
```

### With Options
```bash
# Skip LLM processing
python main.py sources.json --no-llm

# Enable verbose output
python main.py sources.json --verbose

# Custom output file
python main.py sources.json --output custom_feed.rss
```

### Testing Sources
```bash
python main.py sources.json --validate-only
```

## Development

### Local Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
4. Configure your API keys and settings in `.env`
5. Run the application:
   ```bash
   python main.py sources.json
   ```

### Docker Development

```bash
# Build the container
docker build -t article-collector .

# Run with your sources
docker run --rm -v $(pwd):/app article-collector python main.py sources.json
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
