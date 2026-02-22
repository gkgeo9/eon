# EON: Technical Project Showcase

> A detailed engineering breakdown of the Erebus Observatory Network -- designed for portfolio reviews, technical interviews, and CV discussions.

---

## At a Glance

| | |
|---|---|
| **Project** | AI-powered SEC filing analysis platform for investment research |
| **Scale** | 38,000+ lines of Python across 158 modules |
| **Domain** | Financial technology, NLP/LLM applications, data engineering |
| **Core Problem** | Transform unstructured SEC filings into structured, multi-perspective investment intelligence at scale |
| **Key Challenge** | Reliably process 10,000+ API requests across multi-day batch runs with 25 concurrent API keys, crash recovery, and adaptive rate limiting |

---

## What This Project Demonstrates

### 1. Full-Stack Systems Design

EON is not a script or a prototype. It is a complete, production-grade system with:

- **Web application** (Streamlit with 5 pages, 950+ line main analysis page)
- **CLI application** (Click-based with analyze, batch, scan, export, web commands)
- **Relational database** layer (SQLite with WAL mode, 12 versioned migrations, 8 tables)
- **Background processing** engine (ThreadPoolExecutor + ProcessPoolExecutor)
- **Plugin system** (auto-discovered custom workflows with validation)
- **Monitoring and alerting** (Discord webhooks, disk/memory monitoring, health checks)
- **Multiple storage backends** (JSON for debugging, Parquet for scale, SQLite for metadata)

This is not a toy -- it is designed to run unsupervised for 20+ days processing 1,000 companies.

### 2. Distributed Systems and Concurrency

The most technically demanding aspect of EON is coordinating 25 parallel API keys across threads, processes, and simultaneous application instances (CLI + web UI running at the same time).

#### Three-Layer Concurrency Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  Streamlit UI (multi-threaded) + CLI (process-based) + Batch    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────v─────────────────────────────────────┐
│  Layer 1: Global Semaphore                                      │
│  ─────────────────────────                                      │
│  Limits total concurrent API requests to N (default: 25)        │
│  Prevents overwhelming the API even with many threads           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────v─────────────────────────────────────┐
│  Layer 2: Per-Key File Locks                                    │
│  ─────────────────────────────                                  │
│  portalocker.LOCK_EX on data/api_usage/gemini_request_{hash}    │
│  Ensures no two threads/processes use the same API key          │
│  Cross-platform: Windows, macOS, Linux                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────v─────────────────────────────────────┐
│  Layer 3: Atomic Key Reservation                                │
│  ────────────────────────────                                   │
│  threading.Condition() for wait/notify coordination             │
│  Persistent JSON files track usage per key per day              │
│  Atomic writes via temp file + rename (crash-safe)              │
│  Survives process restarts -- usage data is never lost          │
└─────────────────────────────────────────────────────────────────┘
```

**Why this matters:** Most LLM applications use a single API key and sequential requests. EON manages 25+ keys with true parallelism, cross-process safety, and crash recovery -- problems typically seen in distributed systems, not single-machine applications.

#### Adaptive Rate Limiting

The system doesn't just enforce static rate limits -- it learns from API behavior:

- **After 5 consecutive successes:** Reduce sleep from 65s to 40s (faster throughput)
- **On 429 (rate limit) error:** Increase sleep by 50% (65s → 97.5s)
- **On transient error:** Reset to base sleep duration
- **Result:** Optimal throughput that adapts to real-time API conditions

This is a textbook control-theory feedback loop applied to API rate limiting.

### 3. Fault Tolerance and Reliability Engineering

EON is designed to run for weeks. Every component is built to handle failures gracefully:

#### Resume System (Per-Year Granularity)

```
Batch: AAPL (10 years)
├── 2015 ✅ (saved to DB immediately)
├── 2016 ✅ (saved to DB immediately)
├── 2017 ✅ (saved to DB immediately)
├── 2018 ✅ (saved to DB immediately)
├── 2019 ✅ (saved to DB immediately)
├── 2020 ✅ (saved to DB immediately)
├── 2021 ✅ (saved to DB immediately)
├── 2022 ❌ CRASH / POWER OUTAGE
├── 2023 ⏳ (not started)
└── 2024 ⏳ (not started)

On resume: Starts at 2022, not 2015. Years 2015-2021 are preserved.
```

This is implemented through:
- **SQLite checkpoints** after each year completes
- **File-based progress tracking** with portalocker for cross-process safety
- **Atomic writes** (write to .tmp, then rename) to prevent corruption
- **Exponential backoff with jitter** for database operations (up to 10 retries)

#### Multi-Day Quota Management

```
Day 1: 25 keys × 20 requests/key = 500 requests processed
        → All keys exhausted at 11:47 PM
        → System detects exhaustion, sends Discord alert
        → Waits for midnight PST (Google's quota reset time)

Day 2: Verifies reset, resumes automatically
        → Skips completed companies
        → Continues from last checkpoint for in-progress companies
        → Processes next 500 requests
```

This requires timezone-aware quota tracking (America/Los_Angeles for Google's reset boundary), persistent state that survives restarts, and a thread coordination mechanism that can pause and resume 25 workers simultaneously.

#### System Health Monitoring

| Monitor | Trigger | Action |
|---|---|---|
| **DiskMonitor** | <5GB free | Pause batch, send Discord alert |
| **ProcessMonitor** | >80% memory | Kill orphaned Chrome processes |
| **HealthChecker** | Any degradation | Log warnings, send notifications |
| **Database Backup** | Daily during batch | Automatic backup with 7-day retention |
| **Log Rotation** | >10MB log file | Rotate to backup, prevent disk exhaustion |

### 4. LLM Application Engineering

EON goes beyond "send prompt, get text back" to implement production-grade LLM integration:

#### Type-Safe Structured Output

Every AI response is validated against a Pydantic v2 schema:

```python
class BuffettAnalysis(BaseModel):
    moat_type: str = Field(description="Brand/Network/Switching/Cost/Regulatory")
    moat_rating: str = Field(description="Wide (10+ years) / Narrow (3-5) / None")
    roic_5yr: List[float] = Field(description="5-year ROIC trend")
    management_grade: str = Field(description="A through F")
    intrinsic_value_estimate: float = Field(description="Estimated intrinsic value")
    margin_of_safety: float = Field(description="Upside percentage")
    verdict: str = Field(description="BUY / HOLD / PASS")
```

This eliminates the "LLM returned garbage" failure mode. The schema is sent to Gemini's `response_schema` parameter, which constrains generation to valid JSON matching the Pydantic model. The response is then parsed with `model_validate_json()` for double validation.

#### Intelligent Retry Strategy

The retry logic differentiates between three failure categories:

| Category | Strategy | Max Retries |
|---|---|---|
| **Rate Limit (429)** | Parse `retryDelay` from response, add buffer, wait | Unlimited |
| **Transient (500/502/503)** | Exponential backoff with ±20% jitter | 3 |
| **Other errors** | Linear delay | 3 |

Total possible attempts per request: up to 18 (3 + unlimited rate limit waits + 5 transient retries). The jitter prevents thundering herd when multiple workers hit transient errors simultaneously.

#### Multi-Perspective Prompt Engineering

The multi-perspective analysis prompt is a 178-line structured template that:

1. Defines three complete analytical frameworks (Buffett, Taleb, Contrarian)
2. Specifies quantitative requirements (e.g., "Calculate ROIC: NOPAT / (Debt + Equity - Cash)")
3. Provides scoring rubrics with explicit thresholds (e.g., "ROIC >15% consistently = excellent")
4. Requires synthesis across all three lenses
5. Enforces six rules: be specific, honest, quantitative, contrarian, probabilistic, jargon-free

This is domain-specific prompt engineering that produces consistently structured, analytically rigorous output.

### 5. Data Engineering Pipeline

#### SEC Edgar Integration

The SEC data pipeline handles the full lifecycle:

```
Ticker "AAPL"
    │
    ├─ Resolve: Ticker → CIK (SEC Central Index Key)
    │   └─ Also supports direct CIK input (for delisted companies like Enron)
    │
    ├─ Query: SEC EDGAR API for available filings
    │   ├─ Fiscal year calculation (handles non-calendar fiscal years)
    │   ├─ Filing type classification (10-K, 10-Q, 8-K, DEF 14A, etc.)
    │   └─ Rate limiting: 8 req/sec (conservative, below SEC's 10 req/sec limit)
    │
    ├─ Download: HTML filings with metadata
    │   ├─ Accession number, filing date, report date, fiscal year/quarter
    │   └─ Cross-process rate limiting via file locks
    │
    ├─ Convert: HTML → PDF
    │   ├─ Headless Chrome via Selenium + Chrome DevTools Protocol
    │   ├─ Dynamic wait times based on file size (3-15 seconds)
    │   ├─ Timeout handling with automatic driver restart
    │   └─ Orphaned Chrome process cleanup
    │
    ├─ Extract: PDF → Text
    │   ├─ PyPDF2 with per-page error handling
    │   ├─ Chunking for large files (100-page chunks)
    │   └─ Minimum text threshold validation
    │
    └─ Cache: Intelligent freshness tracking
        ├─ 7-day refresh threshold
        ├─ Filesystem integrity verification
        └─ Smart download (only fetch missing years)
```

#### Multiple Storage Backends

| Backend | Use Case | Compression | Query Speed |
|---|---|---|---|
| **JSON** | Development, debugging | None (human-readable) | File scan |
| **Parquet** | Production, batch export | 10-100x vs JSON | Column-pruning |
| **SQLite** | Metadata, progress, UI state | WAL mode | Full SQL |

The Parquet backend uses year-based partitioning and automatically flattens nested Pydantic models into columnar format. Batch exports group records by year for optimal write performance.

### 6. Software Architecture Patterns

| Pattern | Where Used | Why |
|---|---|---|
| **Protocol-based DI** | `IKeyManager`, `IRateLimiter`, `IRepository` + 3 more | Testability without tight coupling. Services accept protocols, not concrete classes |
| **Result[T] monad** | All fallible operations | Explicit success/failure/partial states. No silent `None` returns |
| **Thread-safe singleton** | Config, usage tracker, request queue, cancellation registry | Double-checked locking for safe multi-threaded access |
| **Plugin architecture** | Custom workflows | Auto-discovery via filesystem scan. Validation at load time |
| **Repository pattern** | `DatabaseRepository` | Centralized data access with retry logic and backup |
| **Strategy pattern** | Storage backends (`JSONStore`, `ParquetStore`) | Swap storage implementations via config |
| **Observer pattern** | Discord notifications, progress callbacks | Decouple batch processing from monitoring |
| **Cooperative cancellation** | `CancellationToken` + `CancellationRegistry` | Thread-safe cancellation without `thread.kill()` |
| **Command pattern** | Click CLI (`analyze`, `batch`, `scan`, `export`) | Each command is an independent entry point |
| **Builder pattern** | `BatchJobConfig` dataclass | Structured batch job construction |
| **Migration pattern** | `v001`-`v012` SQL files | Idempotent, ordered schema evolution |

### 7. Domain Expertise: Quantitative Finance

EON isn't a generic LLM wrapper. It encodes deep financial domain knowledge:

- **Five moat sources** from Buffett's framework (Brand, Network Effects, Switching Costs, Cost Advantage, Regulatory)
- **Fragility metrics** from Taleb: Debt/EBITDA ratio, fixed vs. variable cost structure, customer concentration, cash runway
- **ROIC calculation**: `NOPAT / (Debt + Equity - Cash)` with 5-year trend analysis
- **Contrarian 6-dimension scoring** (Strategic Anomaly, Asymmetric Resources, Contrarian Positioning, Cross-Industry DNA, Early Infrastructure, Intellectual Capital)
- **SEC filing types**: Correct classification of 24+ filing types into annual (10-K, 20-F, N-CSR), quarterly (10-Q, 6-K), and event (8-K, DEF 14A, SC 13D/G)
- **Fiscal year handling**: Proper calculation for non-calendar fiscal years (e.g., Apple's September FY end)
- **CIK-based lookup**: Enables analysis of delisted companies (Enron, Lehman, etc.)

---

## Technical Complexity Metrics

### Codebase Scale

| Metric | Value |
|---|---|
| Total Python files | 158 |
| Total lines of code | 38,000+ |
| Core infrastructure (`eon/core/`) | 2,400 lines across 11 modules |
| AI integration (`eon/ai/`) | 2,300 lines across 13 modules |
| Data pipeline (`eon/data/`) | 3,400 lines across 14 modules |
| Largest single file | `eon/data/sources/sec/downloader.py` (839 lines) |
| Most complex module | `eon/ai/usage_tracker.py` (673 lines -- cross-process atomic operations) |
| SQL migrations | 12 versions, 509 lines |
| Test files | 17 |
| Pydantic models | 30+ |
| Custom exception types | 11 |
| Protocol interfaces | 6 |
| Dependencies | 20 production + 7 dev |

### Concurrency Primitives Used

| Primitive | Count | Purpose |
|---|---|---|
| `threading.Lock` | 8+ | In-memory mutual exclusion |
| `threading.Condition` | 2 | Wait/notify for key reservation |
| `threading.Event` | 3 | Cancellation signaling, stop/pause control |
| `threading.Semaphore` | 2 | Global concurrency limits (Gemini + SEC) |
| `portalocker.LOCK_EX` | 6+ | Cross-process file locks |
| `ProcessPoolExecutor` | 1 | Multi-process batch execution |
| `ThreadPoolExecutor` | 2 | Thread-based batch execution |
| Atomic file writes | 4+ | Temp file + rename pattern |

### Error Handling Depth

```
EonException (base)
├── ConfigurationError
├── DataSourceError
│   ├── DownloadError
│   ├── ConversionError
│   └── ExtractionError
├── AnalysisError
├── AIProviderError
│   ├── RateLimitError
│   ├── KeyQuotaExhaustedError
│   └── ContextLengthExceededError
├── StorageError
└── ValidationError
```

Each exception type triggers different recovery behavior in the batch processor (retry, skip, pause, or fail).

---

## Engineering Problems Solved

### Problem 1: API Key Exhaustion During Multi-Day Runs

**Context:** Processing 1,000 companies × 10 years = 10,000 API requests. With 25 keys at 20 requests/key/day, that's 500 requests/day -- a 20-day run.

**Challenge:** Keys exhaust at unpredictable times. Some keys hit limits earlier due to uneven distribution. The system needs to detect exhaustion, pause all workers, wait for the exact quota reset moment, verify the reset actually happened, and resume.

**Solution:**
- `APIUsageTracker` tracks per-key daily usage in persistent JSON files
- `reserve_and_get_key()` uses `threading.Condition()` to block when all keys are in use or exhausted
- The batch queue detects `KeyQuotaExhaustedError`, sends a Discord notification, calculates seconds until midnight PST (Google's reset boundary), sleeps, then verifies reset by checking usage counts
- Workers resume automatically without human intervention

### Problem 2: Same API Key Used Twice Simultaneously

**Context:** 25 threads each need an API key. Without coordination, two threads could grab the same key, causing rate limit violations.

**Solution:**
- `APIUsageTracker.reserve_and_get_key()` uses `threading.Condition()` as a mutex
- Tracks `_reserved_keys` set and `_key_usage_counts` dict
- A thread requesting a key either gets an unreserved key or blocks until one is released
- File-based locks (`portalocker.LOCK_EX`) extend this safety across processes

### Problem 3: Chrome Browser Process Leaks

**Context:** HTML → PDF conversion spawns headless Chrome instances. During long batch runs, timeout errors leave orphaned Chrome processes consuming memory.

**Solution:**
- `ProcessMonitor.should_cleanup_chrome()` triggers at >80% memory usage
- `cleanup_chrome_processes()` identifies Chrome processes older than the current batch and terminates them
- `SECConverter._restart_driver()` recovers from timeout errors by killing the driver and creating a new one
- Dynamic wait times (3-15 seconds based on HTML file size) reduce timeout frequency

### Problem 4: Database Corruption During Concurrent Access

**Context:** Multiple threads writing analysis results to SQLite simultaneously, plus the UI reading for progress display.

**Solution:**
- SQLite WAL (Write-Ahead Logging) mode enables concurrent readers + one writer
- `DatabaseRepository` implements exponential backoff (up to 10 retries) for lock contention
- Daily automatic backups during batch processing with 7-day retention
- All writes use transactions for atomicity

### Problem 5: Resuming After Arbitrary Failures

**Context:** A 20-day batch run can be interrupted by power outages, OOM kills, network failures, or user cancellation. The system must resume without re-processing completed work or losing partial results.

**Solution:**
- Results are persisted to SQLite **after each individual year** (not after each company)
- `ProgressTracker` maintains a cross-process-safe set of completed items using file locking
- `batch_item_year_checkpoints` table tracks exactly which years are done for each ticker
- On resume: query checkpoints, skip completed years, start from the exact interruption point
- `CancellationToken` enables graceful shutdown that completes the current year before stopping

---

## Skills Demonstrated

### Programming & Architecture
- Python 3.10+ with type hints and Protocol-based interfaces
- Object-oriented design with SOLID principles
- Design patterns: Strategy, Observer, Repository, Command, Plugin, Builder, Cooperative Cancellation
- Pydantic v2 for data validation, serialization, and configuration
- Abstract base classes and protocol-based dependency injection

### Concurrency & Distributed Systems
- Thread-safe programming with locks, conditions, events, and semaphores
- Cross-process coordination via file-based locking (portalocker)
- ProcessPoolExecutor and ThreadPoolExecutor orchestration
- Atomic file operations (temp + rename) for crash safety
- Thundering herd prevention with staggered worker starts
- Adaptive rate limiting with feedback-loop control

### Data Engineering
- End-to-end ETL pipeline (SEC EDGAR → HTML → PDF → Text → AI → Structured Data)
- Multiple storage backends with strategy pattern (JSON, Parquet, SQLite)
- Database schema migration system (12 versions)
- Parquet partitioning and columnar storage optimization
- Multi-format export (CSV, Excel, Parquet)

### LLM/AI Application Development
- Google Gemini API integration with structured output (Pydantic schemas as response constraints)
- Multi-strategy retry logic (rate limits, transient errors, general failures)
- Prompt engineering for quantitative financial analysis
- Token estimation and context length management
- API key rotation and quota management at scale

### Web Scraping & Automation
- SEC EDGAR API integration with rate limit compliance
- Selenium + Chrome DevTools Protocol for HTML → PDF conversion
- Headless browser lifecycle management (startup, timeout recovery, cleanup)
- Cross-process web scraping rate limiting

### Full-Stack Development
- Streamlit web application (5 pages, dashboard, batch management)
- Click-based CLI with multiple commands
- SQLite database with WAL mode and migration system
- Discord webhook integration for real-time notifications

### DevOps & Reliability
- System health monitoring (disk, memory, process management)
- Log rotation for long-running processes
- Automated database backups with retention
- Graceful degradation (optional psutil, disabled webhooks don't crash)
- Resume capability for multi-day batch operations

### Financial Domain
- SEC filing analysis (10-K, 10-Q, 8-K, DEF 14A, and 20+ more types)
- Investment philosophy implementation (Buffett value investing, Taleb antifragility, contrarian analysis)
- Financial metrics (ROIC, FCF, Debt/EBITDA, payout ratios)
- Fiscal year handling for non-calendar companies
- CIK-based lookup for delisted company research

---

## Architecture Decisions and Trade-offs

| Decision | Alternative Considered | Why This Choice |
|---|---|---|
| **SQLite over PostgreSQL** | PostgreSQL would handle concurrency better | Single-machine deployment, zero config, WAL mode is sufficient, portable |
| **File-based locks over Redis** | Redis would be more robust | No external dependency, works offline, cross-platform, sufficient for single-machine |
| **ThreadPool over async/await** | asyncio would use less memory | Simpler debugging, Chrome/Selenium are synchronous, CPU-bound PDF processing |
| **Pydantic over dataclasses** | Dataclasses are simpler | Need validation, serialization, settings management, and LLM schema enforcement |
| **Parquet over CSV for storage** | CSV is universal | 10-100x compression, column pruning for queries, self-describing schema |
| **Plugin auto-discovery over registry** | Explicit registration is safer | Better developer experience, zero-config for new workflows, validation catches errors |
| **Streamlit over Flask/FastAPI** | Flask gives more control | Rapid development for data-focused UI, built-in state management, suitable for analysis dashboard |
| **portalocker over fcntl** | fcntl is simpler on Linux | Cross-platform (Windows + macOS + Linux), well-tested library |

---

## What Makes This Project Stand Out

1. **It solves a real problem at real scale.** This isn't a tutorial project. It processes thousands of companies over weeks, handles arbitrary failures, and produces structured, validated output.

2. **The concurrency engineering is non-trivial.** Three-layer locking, adaptive rate limiting, cross-process coordination via file locks, atomic key reservation, thundering herd prevention -- these are production distributed systems patterns applied to a single-machine Python application.

3. **It demonstrates domain depth.** The financial analysis prompts encode genuine investment frameworks (Buffett's 5 moat sources, Taleb's fragility metrics, contrarian 6-dimension scoring). This isn't "ask ChatGPT about stocks."

4. **The code is well-structured.** 158 modules with clear separation of concerns, Protocol-based dependency injection, Result types for explicit error handling, a custom exception hierarchy, and 17 test files.

5. **It handles the boring-but-critical stuff.** Database migrations, log rotation, disk monitoring, Chrome process cleanup, Discord alerts, resume capability, graceful cancellation. These are the details that separate production systems from prototypes.

---

*Built with Python 3.10+ | 38,000+ lines of code | 158 modules | 12 database migrations | 6 example workflows | 8 analysis types | 3 investment philosophies*
