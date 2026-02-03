# Batch Processing Fix Plan

This document outlines the fixes implemented to enable reliable multi-day batch processing (1000+ companies, 7 years each).

## Context

**Goal**: Start batch analysis, leave running for 1-2 weeks, return with all data.

**Scale**:
- 1000 companies × 7 years = 7000 API requests
- 25 API keys × 20 requests/day/key = 500 requests/day
- **Estimated time: 14 days**

---

## Implementation Status

| Problem | Status | Files Modified |
|---------|--------|----------------|
| Problem 1: CLI Batch Mode | COMPLETED | `fintel/cli/batch.py` |
| Problem 2: Auto-Resume | COMPLETED | `fintel/cli/batch.py` |
| Problem 3: Graceful Skip | COMPLETED | `fintel/core/exceptions.py`, `fintel/ai/providers/gemini.py`, `fintel/ui/services/batch_queue.py` |
| Problem 4: Timezone Buffer | COMPLETED | `fintel/ui/services/batch_queue.py` |
| Problem 5: Chrome Cleanup | COMPLETED | `fintel/data/sources/sec/converter.py`, `fintel/ui/services/batch_queue.py` |
| Problem 6: SQLite Maintenance | COMPLETED | `fintel/ui/database/repository.py`, `fintel/ui/services/batch_queue.py` |

---

## Problem 1: Streamlit Session Timeout (CRITICAL) - COMPLETED

### Description
Batch worker runs as a daemon thread tied to Streamlit session. When browser closes or session times out, the worker dies silently.

### Solution Implemented
Rewrote `fintel/cli/batch.py` to use `BatchQueueService` directly instead of `ParallelProcessor`:
- Runs in foreground (not daemon thread)
- Signal handlers for SIGINT/SIGTERM for graceful shutdown
- Use with tmux/screen for persistence

### Usage
```bash
# Start in tmux for persistence
tmux new -s fintel-batch
fintel batch companies.csv --years 7

# Ctrl+C to stop gracefully (resume later with --resume)
```

---

## Problem 2: No Auto-Resume (HIGH) - COMPLETED

### Description
When a batch is interrupted, no easy way to resume.

### Solution Implemented
Added CLI resume capabilities:
- `fintel batch --resume` - Resume most recent incomplete batch
- `fintel batch --resume-id <batch_id>` - Resume specific batch
- `fintel batch --list-incomplete` - List all incomplete batches

### Usage
```bash
# List incomplete batches
fintel batch --list-incomplete

# Resume most recent
fintel batch --resume

# Resume specific batch
fintel batch --resume-id abc12345-...
```

---

## Problem 3: Large 10-Ks Fail Entire Company (MEDIUM) - COMPLETED

### Description
Banks and large companies have 10-Ks exceeding Gemini's context limit, failing the entire company.

### Solution Implemented
1. Added `ContextLengthExceededError` exception in `fintel/core/exceptions.py`
2. Catch context-length errors in `fintel/ai/providers/gemini.py` with pattern matching
3. Handle in batch_queue.py: mark as "skipped" not "failed", continue processing
4. Added `_mark_item_skipped()` method to batch queue

### Detection Patterns
```python
context_error_indicators = [
    'token count', 'context length', 'maximum context',
    'input too long', 'request payload size exceeds',
    'exceeds the limit', 'too many tokens', 'content too large',
]
```

---

## Problem 4: Timezone/Reset Issues (LOW) - COMPLETED

### Description
Edge cases around DST transitions or clock drift during midnight PST reset.

### Solution Implemented
Added 5-minute buffer after calculated midnight PST:
```python
RESET_BUFFER_SECONDS = 300  # 5 minutes
wait_seconds += RESET_BUFFER_SECONDS
```

The existing verification logic already rechecks key availability after the wait.

---

## Problem 5: Chrome Memory Leak (LOW) - COMPLETED

### Description
Orphaned Chrome processes accumulate over 14 days.

### Solution Implemented
1. Added `cleanup_orphaned_chrome_processes()` in `fintel/data/sources/sec/converter.py`
2. Called during daily reset wait via `_perform_daily_maintenance()`
3. Cross-platform support (Linux, macOS, Windows)

### Cleanup Function
```python
def cleanup_orphaned_chrome_processes(logger=None) -> int:
    # Uses pkill on Linux/macOS, taskkill on Windows
    # Returns number of process groups killed
```

---

## Problem 6: SQLite Under Sustained Load (LOW) - COMPLETED

### Description
14 days of continuous writes may cause database bloat.

### Solution Implemented
1. Added `maintenance()` method to `DatabaseRepository`
2. Performs WAL checkpoint and ANALYZE
3. Called during daily reset wait via `_perform_daily_maintenance()`
4. Logs database size before/after

### Maintenance Method
```python
def maintenance(self) -> dict:
    # WAL checkpoint (flush to main database)
    # ANALYZE (update query planner statistics)
    # Returns stats and any errors
```

---

## CLI Batch Command Usage

```bash
# Start new batch (1000 companies, 7 years each)
fintel batch companies.csv --years 7

# With specific analysis type
fintel batch companies.csv --years 7 --analysis-type multi_analysis

# Resume interrupted batch
fintel batch --resume

# Resume specific batch
fintel batch --resume-id <batch_id>

# List incomplete batches
fintel batch --list-incomplete

# With Chrome cleanup flag (recommended for long runs)
fintel batch companies.csv --years 7 --cleanup-chrome
```

### CSV Format
```csv
ticker
AAPL
MSFT
GOOGL
```

### Recommended Setup for Multi-Day Runs
```bash
# 1. Create tmux session
tmux new -s fintel-batch

# 2. Start batch
fintel batch companies.csv --years 7

# 3. Detach with Ctrl+B, then D

# 4. Reattach later
tmux attach -t fintel-batch

# 5. If interrupted, resume
fintel batch --resume
```

---

## Files Modified

| File | Changes |
|------|---------|
| `fintel/cli/batch.py` | Complete rewrite for CLI batch with BatchQueueService |
| `fintel/core/exceptions.py` | Added `ContextLengthExceededError` |
| `fintel/ai/providers/gemini.py` | Catch context length errors, raise specific exception |
| `fintel/ui/services/batch_queue.py` | Handle skipped items, add maintenance during reset wait, 5-min buffer |
| `fintel/data/sources/sec/converter.py` | Added `cleanup_orphaned_chrome_processes()` |
| `fintel/ui/database/repository.py` | Added `maintenance()` method |

---

## Testing Checklist

- [x] Python syntax valid for all modified files
- [x] CLI batch command has proper options and help text
- [x] Signal handlers installed for graceful shutdown
- [x] Resume flags work (--resume, --resume-id, --list-incomplete)
- [x] ContextLengthExceededError catches relevant error patterns
- [x] Items marked as "skipped" not "failed" for context errors
- [x] 5-minute buffer added after midnight reset
- [x] Chrome cleanup function is cross-platform
- [x] Database maintenance performs WAL checkpoint and ANALYZE
- [x] Daily maintenance called during reset wait
