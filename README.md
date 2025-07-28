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

- [ ] **Package Storage & Retrieval** - Store and serve AI packages with metadata
- [ ] **Search API** - Fast, semantic search across all packages
- [ ] **Version Management** - Full semantic versioning support
- [ ] **RESTful API** - Clean, documented API endpoints
- [ ] **Package Validation** - Schema validation for all package types

### 🚧 In Development

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
- **Deployment**: Docker + Kubernetes
- **Monitoring**: Prometheus + Grafana

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
  tags: ["data", "analytics", "python"]
```

```yaml
# Tool Package
type: tool
spec_version: "1.0"
metadata:
  name: "web-scraper"
  version: "0.5.0"
  description: "Intelligent web scraping tool"
  runtime: "python"
```

```yaml
# Chain Package
type: chain
spec_version: "1.0"
metadata:
  name: "customer-support-flow"
  version: "2.1.0"
  description: "Multi-step customer support automation"
  components: ["classifier@1.0.0", "responder@2.0.0"]
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
