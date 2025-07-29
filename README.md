# 🌟 AgentHub Registry

> **The universal package registry for AI-native agents, tools, chains, and prompts**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)

Welcome to the **AgentHub Registry** – the backend service powering the universal package manager for AI agents, tools, chains, and prompts. This registry enables developers to discover, publish, and manage AI-native components with ease.

🌐 **Live at**: [registry.agenthubcli.com](https://registry.agenthubcli.com)

## 🚀 What is AgentHub Registry?

AgentHub Registry is the central hub where AI developers can:

- **📦 Publish** their agents, tools, chains, and prompts
- **🔍 Discover** community-built AI components
- **⚡ Install** packages with semantic versioning
- **🔐 Authenticate** securely via GitHub OAuth
- **🌐 Browse** through a beautiful web interface

Think of it as "npm for AI" – but specifically designed for the unique needs of AI-native development.

## ✨ Features

### 🎯 Current Features

### 🚧 In Development

- [ ] **Package Storage & Retrieval** - Store and serve AI packages with metadata
- [ ] **Search API** - Fast, semantic search across all packages
- [ ] **Version Management** - Full semantic versioning support
- [ ] **RESTful API** - Clean, documented API endpoints
- [ ] **Package Validation** - Schema validation for all package types
- [ ] **Web UI** - Beautiful public interface for browsing packages
- [ ] **GitHub OAuth** - Secure authentication for publishing
- [ ] **Advanced Search** - Filter by type, tags, popularity, etc.
- [ ] **Package Analytics** - Download stats and usage metrics
- [ ] **Documentation Hub** - Auto-generated docs from package metadata

### 🔮 Planned Features

- [ ] **Package Dependencies** - Dependency resolution and management
- [ ] **Private Registries** - Enterprise support for private packages
- [ ] **CI/CD Integration** - GitHub Actions for automated publishing
- [ ] **Package Security** - Vulnerability scanning and security badges
- [ ] **Community Features** - Reviews, ratings, and discussions

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL with async support
- **Search**: Elasticsearch for fast package discovery
- **Authentication**: GitHub OAuth 2.0
- **Storage**: Object storage for package artifacts

## 📚 API Documentation

### Core Endpoints

| Method | Endpoint                   | Description                                   |
| ------ | -------------------------- | --------------------------------------------- |
| `GET`  | `/search`                  | Search packages by name, description, or tags |
| `GET`  | `/package/{name}`          | Get package details and metadata              |
| `GET`  | `/package/{name}/versions` | List all versions of a package                |
| `POST` | `/publish`                 | Publish a new package version                 |
| `GET`  | `/browse`                  | Browse packages by category                   |
| `GET`  | `/stats`                   | Registry statistics and metrics               |

### Package Types

AgentHub Registry supports multiple package types:

```yaml
# Agent Package
type: agent
spec_version: "1.0"
metadata:
  name: "data-analyst-bot"
  version: "1.2.0"
  description: "AI agent for data analysis and insights"
  author: "jane@example.com"
  license: "MIT"
  runtime: "python"
  entry_point: "main.py"
  dependencies:
    pandas-tool: "^2.0.0"
    chart-generator: "^1.5.0"
    data-validator: "~1.0.0"
  environment:
    PYTHON_VERSION: "3.9+"
    MAX_MEMORY: "2GB"
    TIMEOUT: "300"
  config:
    max_rows: 100000
    output_format: "json"
    enable_caching: true
  tags: ["data", "analytics", "python", "pandas"]
```

```yaml
# Tool Package
type: tool
spec_version: "1.0"
metadata:
  name: "web-scraper"
  version: "0.5.0"
  description: "Intelligent web scraping tool with rate limiting"
  author: "dev@example.com"
  license: "Apache-2.0"
  runtime: "python"
  entry_point: "scraper.py"
  schema:
    input:
      url:
        type: "string"
        description: "URL to scrape"
        required: true
      selector:
        type: "string"
        description: "CSS selector for elements"
        required: false
        default: "body"
      wait_time:
        type: "integer"
        description: "Wait time between requests (ms)"
        required: false
        default: 1000
    output:
      content:
        type: "string"
        description: "Scraped content"
      elements:
        type: "array"
        description: "List of scraped elements"
      metadata:
        type: "object"
        description: "Scraping metadata"
  config:
    user_agent: "AgentHub-Scraper/1.0"
    max_retries: 3
    timeout: 30
  tags: ["web", "scraping", "data-extraction"]
```

```yaml
# Chain Package
type: chain
spec_version: "1.0"
metadata:
  name: "customer-support-flow"
  version: "2.1.0"
  description: "Multi-step customer support automation chain"
  author: "support-team@example.com"
  license: "MIT"
  steps:
    - name: "classify_intent"
      type: "agent"
      package: "intent-classifier@1.0.0"
      config:
        confidence_threshold: 0.8
      inputs:
        message: "{{user_input}}"
      outputs:
        intent: "classified_intent"
        confidence: "classification_confidence"
    - name: "route_to_specialist"
      type: "tool"
      package: "routing-tool@2.1.0"
      condition: "{{classification_confidence}} > 0.8"
      config:
        fallback_queue: "general_support"
      inputs:
        intent: "{{classified_intent}}"
        priority: "{{user_priority}}"
      outputs:
        specialist_id: "assigned_specialist"
        queue_position: "queue_pos"
    - name: "generate_response"
      type: "prompt"
      package: "support-response@1.5.0"
      inputs:
        intent: "{{classified_intent}}"
        specialist: "{{assigned_specialist}}"
        context: "{{conversation_history}}"
      outputs:
        response: "generated_response"
  config:
    max_execution_time: 120
    retry_failed_steps: true
    log_level: "info"
  tags: ["customer-support", "automation", "nlp", "workflow"]
```

````yaml
# Prompt Package
type: prompt
spec_version: "1.0"
metadata:
  name: "code-reviewer"
  version: "1.0.0"
  description: "AI prompt for code review assistance"
  author: "developer@example.com"
  license: "MIT"
  template: |
    You are an expert code reviewer. Please review the following code:

    ```{{language}}
    {{code}}
    ```

    Focus on: {{focus_areas}}
    Provide feedback on: {{feedback_type}}
  variables:
    - name: "language"
      type: "string"
      description: "Programming language of the code"
      required: true
    - name: "code"
      type: "string"
      description: "Code to be reviewed"
      required: true
    - name: "focus_areas"
      type: "string"
      description: "Areas to focus the review on"
      required: false
      default: "security, performance, readability"
    - name: "feedback_type"
      type: "string"
      description: "Type of feedback to provide"
      required: false
      default: "constructive suggestions"
  examples:
    - name: "python_function_review"
      inputs:
        language: "python"
        code: "def add(a, b): return a + b"
        focus_areas: "type hints, documentation"
      expected: "Consider adding type hints and a docstring..."
  tags: ["code-review", "ai-assistant", "development"]
````

```yaml
# Dataset Package
type: dataset
spec_version: "1.0"
metadata:
  name: "customer-feedback"
  version: "2.0.0"
  description: "Customer feedback dataset for sentiment analysis"
  author: "data-team@example.com"
  license: "CC-BY-4.0"
  format: "csv"
  schema:
    columns:
      - name: "feedback_id"
        type: "integer"
        description: "Unique feedback identifier"
        nullable: false
      - name: "customer_id"
        type: "string"
        description: "Customer identifier"
        nullable: false
      - name: "feedback_text"
        type: "string"
        description: "Customer feedback content"
        nullable: false
      - name: "sentiment_score"
        type: "float"
        description: "Sentiment score (-1 to 1)"
        nullable: true
      - name: "created_at"
        type: "datetime"
        description: "Feedback creation timestamp"
        nullable: false
  files:
    - name: "feedback_2023.csv"
      path: "data/feedback_2023.csv"
      size: 15728640
      hash: "sha256:a8b2c3d4e5f6..."
    - name: "feedback_2024.csv"
      path: "data/feedback_2024.csv"
      size: 18291456
      hash: "sha256:f6e5d4c3b2a1..."
  tags: ["sentiment", "customer-data", "nlp", "machine-learning"]
```

### Example API Usage

```bash
# Search for packages
curl "https://registry.agenthubcli.com/search?q=data%20analysis"

# Get package details
curl "https://registry.agenthubcli.com/package/data-analyst-bot"

# Browse by category
curl "https://registry.agenthubcli.com/browse?type=agent&tag=nlp"
```

## 🏃‍♂️ Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis (for caching)
- Docker (optional)

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/agenthub-dev/registry.git
   cd registry
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

6. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Docker Setup

#### Database Only (Recommended for Development)

For local development, you can run just the PostgreSQL database using Docker Compose:

```bash
# Start the database
docker-compose up -d

# View database logs
docker-compose logs db

# Stop the database
docker-compose down

# Remove database and all data
docker-compose down -v
```

The database will be available at `localhost:5432` with:

- **Database**: `agenthub_registry`
- **Username**: `username`
- **Password**: `password`

Your existing `DATABASE_URL` environment variable will work seamlessly:

```
DATABASE_URL=postgresql://username:password@localhost:5432/agenthub_registry
```

#### Full Application

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in production mode
docker-compose -f docker-compose.prod.yml up -d
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_search.py
```

## 📖 Package Publishing

### CLI Publishing (Recommended)

```bash
# Install the CLI
## Homebrew (macOS & Linux):
brew tap agenthubcli/tap
brew install agenthub

## Scoop (Windows):
scoop bucket add agenthub https://github.com/agenthubcli/scoop-agenthub
scoop install agenthub

## Chocolatey (Windows):
choco install agenthub

# Login with GitHub
agenthub auth login

# Publish your package
agenthub publish
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**: Follow our coding standards
4. **Add tests**: Ensure your code is well-tested
5. **Run the test suite**: `pytest`
6. **Submit a pull request**: We'll review it ASAP!

### Development Guidelines

- **Code Style**: We use Black for formatting and flake8 for linting
- **Type Hints**: All functions should have proper type annotations
- **Documentation**: Add docstrings for all public functions
- **Testing**: Maintain >90% test coverage
- **Security**: Follow security best practices

## 📊 Project Status

- 🟡 **Core API**: In active development
- 🟡 **Web UI**: In active development
- 🔴 **GitHub OAuth**: Planned for Q3 2025
- 🔴 **Advanced Search**: Planned for Q2 2026

## 🔗 Related Projects

- [**AgentHub CLI**](https://github.com/agenthubcli/agenthub) - Command-line interface

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ by the AgentHub community
- Powered by [FastAPI](https://fastapi.tiangolo.com/)
- Inspired by npm, PyPI, and Docker Hub
- Special thanks to all our contributors!

## 📞 Support & Community

- 🐛 **Issues**: [Report bugs](https://github.com/agenthubcli/registry/issues)
- 📧 **Email**: neil[att]agenthubcli.com

---

<div align="center">
  <strong>🤖 Building the future of AI development, one package at a time</strong>
</div>
