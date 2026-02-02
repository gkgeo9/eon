# Fintel - AI-Powered SEC Filing Analysis Platform

## Resume Project Description

---

## Executive Summary

Designed and built a production-grade AI platform that transforms SEC 10-K filings into actionable investment insights using Google Gemini AI. The system combines Warren Buffett's value investing principles, Nassim Taleb's antifragility framework, and contrarian opportunity detection into a unified analysis engine capable of batch-processing 1,000+ companies with intelligent API key rotation, cross-process rate limiting, and fault-tolerant resume capability.

---

## Technical Highlights

### Core Engineering Achievements

- **Built AI-powered financial analysis platform** processing SEC 10-K filings through Google Gemini API with structured Pydantic v2 outputs, achieving 99%+ format consistency across all analysis types

- **Engineered cross-process rate limiting system** using file-based locking (portalocker) to coordinate API calls across threads, processes, and simultaneous CLI/UI execution, eliminating 503 UNAVAILABLE and 429 RESOURCE_EXHAUSTED errors (cross-platform: Windows, macOS, Linux)

- **Designed scalable batch processing engine** supporting 25+ API keys with intelligent least-used rotation, atomic reservation preventing collisions, and persistent JSON-based usage tracking that survives restarts

- **Implemented fault-tolerant architecture** with automatic resume capability for interrupted analyses, exponential backoff retry logic (3 retries, configurable delays), and SQLite WAL mode enabling concurrent read/write operations

- **Created extensible plugin system** for custom analysis workflows with auto-discovery mechanism, zero-code-modification deployment, and full Pydantic schema validation

- **Developed multi-perspective investment analysis framework** combining three distinct methodologies (value investing, antifragility assessment, contrarian opportunity detection) with unified data access layer

- **Built production-ready Streamlit dashboard** with 6 interactive pages, real-time progress tracking, session state management, and comprehensive settings interface

---

## Architecture Overview

```
                           ┌─────────────────────────────────┐
                           │         User Interface          │
                           │  Streamlit (6 pages) + CLI      │
                           └───────────────┬─────────────────┘
                                           │
                           ┌───────────────▼─────────────────┐
                           │        Service Layer            │
                           │  AnalysisService, BatchQueue,   │
                           │  CancellationToken              │
                           └───────────────┬─────────────────┘
                                           │
        ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
        │                  │               │               │                  │
┌───────▼───────┐  ┌───────▼───────┐ ┌─────▼─────┐ ┌───────▼───────┐  ┌───────▼───────┐
│   Analysis    │  │      AI       │ │   Data    │ │   Database    │  │  Processing   │
│   Engines     │  │  Integration  │ │  Sources  │ │     Layer     │  │    Engine     │
├───────────────┤  ├───────────────┤ ├───────────┤ ├───────────────┤  ├───────────────┤
│ Fundamental   │  │ GeminiProvider│ │ SEC Edgar │ │ SQLite + WAL  │  │ ThreadPool    │
│ Perspectives  │  │ KeyManager    │ │ Downloader│ │ Repository    │  │ Parallel      │
│ Comparative   │  │ RequestQueue  │ │ PDF Extract│ │ Migrations    │  │ Resume        │
│ Custom        │  │ UsageTracker  │ │ Converter │ │ (10 versions) │  │ Progress      │
└───────────────┘  └───────────────┘ └───────────┘ └───────────────┘  └───────────────┘
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| **AnalysisService** | Main orchestrator coordinating filing downloads, AI analysis, and result storage |
| **GeminiProvider** | LLM integration with structured output, retry logic, and thinking budget configuration |
| **APIKeyManager** | Intelligent rotation across 25+ keys with atomic reservation and usage tracking |
| **RequestQueue** | Cross-process serialization using portalocker file locking for rate limit compliance |
| **DatabaseRepository** | SQLite data access with WAL mode, exponential backoff, and connection pooling |
| **CustomWorkflow** | Plugin base class enabling zero-modification extensibility |

### Data Flow

```
SEC Edgar API → Download 10-K/10-Q → Convert HTML→PDF → Extract Text
                                                              │
                                                              ▼
SQLite Storage ← Pydantic Validation ← Gemini AI Analysis ← Prompt + Filing
      │
      ▼
Streamlit UI / JSON Export / CLI Output
```

---

## Technologies Used

### AI/ML
- **Google Gemini API** (gemini-2.5-flash) - Primary LLM for analysis
- **Pydantic v2** - Structured output schemas with full validation
- **Thinking Budget** - 4,096 token extended reasoning capability

### Backend
- **Python 3.10+** - Core language with modern type hints
- **SQLAlchemy** - ORM for database operations
- **SQLite WAL** - Concurrent-access database with write-ahead logging
- **portalocker** - Cross-platform file locking for cross-process synchronization (Windows, macOS, Linux)

### Frontend
- **Streamlit 1.30+** - Interactive web dashboard
- **Pandas/Polars** - Data manipulation and display
- **Rich** - Terminal formatting for CLI

### Data Processing
- **PyPDF2** - PDF text extraction
- **Selenium + Chrome** - HTML to PDF conversion
- **SEC Edgar API** - Official SEC filing downloads

### DevOps & Quality
- **Black** - Code formatting (100 char line length)
- **Ruff** - Fast Python linting (E, W, F, I, B, C4, UP rules)
- **MyPy** - Static type checking
- **pytest** - Test framework with coverage tracking
- **pre-commit** - Git hooks for quality enforcement

---

## Metrics & Scale

| Metric | Value |
|--------|-------|
| **Total Python Files** | 104 |
| **Lines of Code** | ~15,000 |
| **API Keys Supported** | 25+ |
| **Batch Processing Capacity** | 1,000+ companies |
| **Database Migrations** | 10 schema versions |
| **Built-in Analysis Types** | 8 |
| **Custom Workflows** | Unlimited (plugin architecture) |
| **Streamlit Pages** | 6 |
| **CLI Commands** | 4 |

---

## Problem-Solution Highlights

### Challenge 1: API Rate Limiting in Parallel Processing

**Problem:** Running batch analyses with multiple workers caused frequent 503 UNAVAILABLE and 429 RESOURCE_EXHAUSTED errors from Gemini API.

**Solution:** Implemented global request serialization using `portalocker` cross-platform file locking that works across:
- Multiple threads (ThreadPoolExecutor)
- Multiple processes (ProcessPoolExecutor)
- Simultaneous CLI and UI execution
- Mixed execution modes

**Result:** Zero rate limit errors with enforced 65-second intervals between requests.

### Challenge 2: Analysis Interruption Recovery

**Problem:** Long-running batch analyses (processing 100+ companies over multiple hours) would lose all progress if interrupted.

**Solution:** Implemented granular progress tracking:
- Per-year completion tracking stored in database
- Last activity timestamps for smart resumption
- Automatic detection of interrupted analyses
- One-click resume from Analysis History page

**Result:** Analyses can be interrupted and resumed without re-processing completed work.

### Challenge 3: Type Consistency in AI Outputs

**Problem:** LLM responses varied in format, causing downstream parsing failures.

**Solution:** Full Pydantic v2 integration with structured outputs:
- Schema definitions for all 8 analysis types
- Validation at response time, not post-processing
- Custom exception hierarchy for granular error handling

**Result:** 99%+ format consistency across all analysis outputs.

---

## Key Differentiators

1. **Production-Grade Reliability** - Not a prototype; handles edge cases, failures, and scale
2. **Multi-Perspective Analysis** - Unique combination of three investment philosophies in one system
3. **True Extensibility** - Plugin architecture with auto-discovery, not just configuration files
4. **Cross-Process Safety** - Solves real concurrency problems that simpler implementations ignore
5. **Comprehensive Tooling** - Both web UI and CLI, with full feature parity

---

## Usage Context

This platform is designed for:
- **Investment Research** - Systematic analysis of public company filings
- **Due Diligence** - Multi-perspective evaluation before investment decisions
- **Screening** - Batch processing to identify opportunities across large universes
- **Pattern Recognition** - Comparing companies against proven performers

---

## Sample Resume Bullet Points

For a **Software Engineer** role:
> Engineered cross-process rate limiting system using file-based locking to coordinate API calls across threads and processes, eliminating quota errors in parallel batch processing

For a **Full-Stack Developer** role:
> Built production Streamlit dashboard with 6 interactive pages, real-time progress tracking, session state management, and SQLite persistence layer supporting concurrent access

For a **ML/AI Engineer** role:
> Designed type-safe AI output pipeline using Pydantic v2 structured outputs with Google Gemini API, achieving 99%+ format consistency across 8 analysis types

For a **Backend Engineer** role:
> Implemented fault-tolerant batch processing engine supporting 25+ API keys with intelligent rotation, atomic reservation, and automatic resume capability for interrupted analyses

For a **Data Engineer** role:
> Created SEC filing ingestion pipeline processing 10-K/10-Q documents through download, HTML-to-PDF conversion, text extraction, and AI analysis with comprehensive caching

---

## Links

- **Repository:** [Private]
- **Documentation:** See `docs/` directory
- **Custom Workflows Guide:** `docs/CUSTOM_WORKFLOWS.md`
