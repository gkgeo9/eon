# Fintel Batch Processing Improvements - Implementation Plan

## Overview
This plan implements 27 improvements for reliable overnight batch processing of 1000+ companies × 10 years.

---

## PHASE 1: Quick Wins & Cleanup (L1-L5)
**Goal:** Remove legacy code and organize files

### L1. Remove `results_display_legacy.py`
- [ ] Delete `fintel/ui/components/results_display_legacy.py`
- [ ] Verify no imports reference this file

### L2. Move export script to scripts/
- [ ] Create `scripts/` directory
- [ ] Move `tests/export_multi_analysis_to_csv.py` to `scripts/`
- [ ] Delete `tests/export_moonshot_to_csv.py` (unused)

### L3. Fix missing `_is_transient_service_error` method
- [ ] Add method to `fintel/ai/providers/gemini.py`

### L5. Verify v009 migration gap
- [ ] Confirm v009 is intentionally missing or add placeholder

---

## PHASE 2: Critical Database Improvements (#2, #6, #8, #11, #18, #19)
**Goal:** Improve database reliability under heavy concurrent load

### #2. Database Connection Pooling & Retry
**Files:** `fintel/ui/database/repository.py`
- [ ] Increase retry count from 5 to 10
- [ ] Implement true exponential backoff (0.1 * 2^attempt + jitter)
- [ ] Add `SQLITE_BUSY` specific handling
- [ ] Add connection timeout parameter to config
- [ ] Test: Run 25 concurrent writers

### #6. Thread-Safe Progress Tracker
**Files:** `fintel/processing/progress.py`
- [ ] Add file locking using `portalocker`
- [ ] Implement atomic read-modify-write for `mark_completed()`
- [ ] Add retry logic for lock acquisition
- [ ] Test: 10 threads marking items concurrently

### #8. Transaction Batching for Results
**Files:** `fintel/ui/database/mixins/results.py`
- [ ] Create `BatchResultWriter` class
- [ ] Buffer results in memory (max 10 or 30 seconds)
- [ ] Flush on buffer full, timeout, or explicit call
- [ ] Test: Write 100 results rapidly

### #11. Database Backup Strategy
**Files:** `fintel/ui/database/repository.py`
- [ ] Add `backup()` method using SQLite `.backup()` API
- [ ] Create backup naming with timestamp
- [ ] Integrate into batch queue daily maintenance
- [ ] Test: Backup during active writes

### #18. Proper Connection Cleanup
**Files:** `fintel/ui/database/repository.py`
- [ ] Add `close()` method
- [ ] Implement `__enter__`/`__exit__` for context manager
- [ ] Update all callers to use context manager or explicit close

### #19. Add Missing Index on `batch_items.ticker`
**Files:** `fintel/ui/database/migrations/v012_batch_improvements.sql`
- [ ] Add `CREATE INDEX IF NOT EXISTS idx_batch_items_ticker`
- [ ] Add index on `batch_items(batch_id, ticker)` for faster lookups

---

## PHASE 3: Per-Year Checkpointing System (#1, #5)
**Goal:** Prevent data loss on crash/restart

### #1. Per-Year Resume Capability
**Files:**
- `fintel/ui/database/migrations/v012_batch_improvements.sql`
- `fintel/ui/services/batch_queue.py`
- `fintel/ui/services/analysis_service.py`

Schema changes:
- [ ] Add `year_checkpoints` table (item_id, year, run_id, result_id, completed_at)
- [ ] Add `last_completed_year` to `batch_items`

Service changes:
- [ ] Modify `_process_item_with_key()` to checkpoint after each year
- [ ] Add `_get_completed_years_for_item()` method
- [ ] Modify resume logic to start from last completed year + 1
- [ ] Test: Simulate crash at year 5 of 10, verify resume

### #5. API Key Exhaustion Graceful Handling
**Files:** `fintel/ui/services/batch_queue.py`
- [ ] Detect 80% key usage threshold
- [ ] Force checkpoint current progress before waiting for reset
- [ ] Add `_checkpoint_all_running_items()` method
- [ ] Test: Exhaust keys mid-company, verify checkpoint

---

## PHASE 4: Process Management (#3, #4, #7, #10, #12)
**Goal:** Improve process reliability and monitoring

### #3. Automatic Chrome Cleanup
**Files:** `fintel/ui/services/batch_queue.py`, `fintel/data/sources/sec/converter.py`
- [ ] Add counter for conversions in batch service
- [ ] Call `cleanup_orphaned_chrome_processes()` every 50 companies
- [ ] Add cleanup to daily maintenance routine
- [ ] Test: Process 100 companies, verify no Chrome accumulation

### #4. Disk Space Monitoring
**Files:**
- New: `fintel/core/monitoring.py`
- `fintel/ui/services/batch_queue.py`

- [ ] Create `DiskMonitor` class
- [ ] Add `check_disk_space()` returning (free_gb, total_gb, percent_free)
- [ ] Add `get_estimated_space_needed(num_tickers, num_years)`
- [ ] Add pre-flight check in `start_batch_job()`
- [ ] Add periodic check every 100 companies
- [ ] Pause batch if < 5GB free, resume when space available
- [ ] Test: Simulate low disk, verify pause

### #7. Heartbeat/Watchdog System
**Files:** `fintel/ui/services/batch_queue.py`
- [ ] Add `_watchdog_thread` to monitor all running items
- [ ] Check for items with `last_heartbeat_at` > 15 minutes old
- [ ] Auto-recover stale items (reset to pending)
- [ ] Add `_start_watchdog()` and `_stop_watchdog()` methods
- [ ] Test: Simulate hung worker, verify recovery

### #10. Graceful Shutdown Propagation
**Files:** `fintel/ui/services/batch_queue.py`, `fintel/ui/services/cancellation.py`
- [ ] Create `ShutdownCoordinator` class
- [ ] Pass shutdown event to all ThreadPoolExecutor workers
- [ ] Wait for workers to complete current operation (max 60s)
- [ ] Checkpoint all in-progress items before exit
- [ ] Test: SIGINT during processing, verify clean state

### #12. Log Rotation Configuration
**Files:** `fintel/core/logging.py`
- [ ] Replace StreamHandler with RotatingFileHandler
- [ ] Configure maxBytes=10MB, backupCount=5
- [ ] Keep console output for interactive use
- [ ] Add `FINTEL_LOG_FILE` and `FINTEL_LOG_MAX_SIZE` env vars
- [ ] Test: Generate > 10MB logs, verify rotation

---

## PHASE 5: Rate Limiting & Network (#9, #15)
**Goal:** Improve network reliability

### #9. Global SEC Rate Limiter
**Files:**
- New: `fintel/data/sources/sec/rate_limiter.py`
- `fintel/data/sources/sec/downloader.py`

- [ ] Create `SECRequestQueue` similar to `GeminiRequestQueue`
- [ ] Use file-based locking for cross-process coordination
- [ ] Configure max 10 req/sec globally
- [ ] Integrate into `SECDownloader`
- [ ] Test: 25 parallel downloads, verify no SEC rate limit errors

### #15. Improved Retry with Exponential Backoff
**Files:** `fintel/ai/providers/gemini.py`
- [ ] Add jitter to all retry delays (±20%)
- [ ] Implement capped exponential backoff (max 120s)
- [ ] Add separate tracking for different error types
- [ ] Test: Simulate 503 errors, verify backoff behavior

---

## PHASE 6: Batch Queue Enhancements (#17, #20-24)
**Goal:** Improve batch processing robustness

### #17. Per-Perspective Saving for Multi-Analysis
**Files:** `fintel/ui/services/analysis_service.py`
- [ ] Save each perspective (Buffett/Taleb/Contrarian) immediately
- [ ] Add `_save_partial_multi_result()` method
- [ ] Continue to next perspective on single failure
- [ ] Test: Fail Taleb analysis, verify Buffett saved

### #20. Deduplication Check
**Files:** `fintel/ui/services/batch_queue.py`
- [ ] Add `_check_duplicate_ticker()` in `create_batch_job()`
- [ ] Warn if ticker exists in active batch
- [ ] Option to skip duplicates or include anyway
- [ ] Test: Add same ticker to two batches, verify warning

### #21. Make DAILY_LIMIT_PER_KEY Configurable
**Files:** `fintel/ai/api_config.py`
- [ ] Add `FINTEL_DAILY_LIMIT_PER_KEY` env var
- [ ] Update `get_api_limits()` to read from env
- [ ] Document in README

### #22. Basic Metrics Collection
**Files:**
- New: `fintel/core/metrics.py`
- `fintel/ui/services/batch_queue.py`

- [ ] Create simple `Metrics` class (in-memory counters)
- [ ] Track: requests_total, errors_total, companies_completed, years_completed
- [ ] Add `get_metrics()` method to BatchQueueService
- [ ] Log metrics every 100 companies
- [ ] Test: Process 10 companies, verify metrics

### #23. Truncate Error Messages in Database
**Files:** `fintel/ui/services/batch_queue.py`
- [ ] Create `_truncate_error()` helper (max 500 chars)
- [ ] Apply to all `error_message` writes
- [ ] Keep first 200 chars + "..." + last 200 chars
- [ ] Test: Generate 10KB error, verify truncation

### #24. Batch Priority Support
**Files:** `fintel/ui/services/batch_queue.py`
- [ ] Respect existing `priority` column in queries
- [ ] Add `ORDER BY priority DESC` to pending item queries
- [ ] Add `set_batch_priority()` method
- [ ] Test: Create high/low priority batches, verify order

### #14. Usage Tracker Cleanup
**Files:** `fintel/ai/usage_tracker.py`
- [ ] Add `cleanup_old_records(days=90)` method
- [ ] Call during daily maintenance
- [ ] Test: Create old records, verify cleanup

---

## PHASE 7: Notifications (#13) and PDF Memory (#16)
**Goal:** Add alerting and optimize memory (deferred)

### #13. Discord Webhook Notifications
**Files:**
- New: `fintel/core/notifications.py`
- `fintel/ui/services/batch_queue.py`
- `fintel/core/config.py`

- [ ] Add `FINTEL_DISCORD_WEBHOOK_URL` to config
- [ ] Create `NotificationService` class
- [ ] Implement `send_discord()` with simple HTTP POST
- [ ] Add notifications for: batch_failed, batch_completed, all_keys_exhausted
- [ ] Make notifications optional (only if webhook configured)
- [ ] Test: Trigger batch failure, verify Discord message

### #16. PDF Memory Optimization (LOW PRIORITY)
**Files:** `fintel/data/sources/sec/extractor.py`
- [ ] Add streaming extraction for files > 50MB
- [ ] Process page-by-page instead of loading entire PDF
- [ ] Test: Extract 300-page 10-K, verify memory usage

---

## VERIFICATION CHECKLIST

After each phase:
- [ ] Run `pytest tests/` - all tests pass
- [ ] Run `black fintel/ tests/ pages/` - code formatted
- [ ] Run `ruff check fintel/` - no lint errors
- [ ] Test batch with 5 companies × 3 years manually
- [ ] Verify no regressions in existing functionality

Final verification:
- [ ] Run overnight batch with 50 companies × 5 years
- [ ] Monitor memory, disk, and process count
- [ ] Verify resume after intentional stop
- [ ] Verify per-year checkpointing works

---

## FILE CHANGE SUMMARY

### New Files
- `fintel/core/monitoring.py` - Disk space monitoring
- `fintel/core/metrics.py` - Simple metrics collection
- `fintel/core/notifications.py` - Discord webhook notifications
- `fintel/data/sources/sec/rate_limiter.py` - SEC global rate limiter
- `fintel/ui/database/migrations/v012_batch_improvements.sql` - Schema changes
- `scripts/export_multi_analysis_to_csv.py` - Moved from tests/

### Modified Files
- `fintel/ui/database/repository.py` - Connection pooling, backup, cleanup
- `fintel/ui/services/batch_queue.py` - Most improvements
- `fintel/ui/services/analysis_service.py` - Per-year checkpointing
- `fintel/processing/progress.py` - Thread safety
- `fintel/ai/providers/gemini.py` - Retry improvements, missing method
- `fintel/ai/api_config.py` - Configurable limits
- `fintel/ai/usage_tracker.py` - Cleanup method
- `fintel/core/logging.py` - Log rotation
- `fintel/core/config.py` - New config options
- `fintel/data/sources/sec/downloader.py` - Global rate limiter

### Deleted Files
- `fintel/ui/components/results_display_legacy.py`
- `tests/export_moonshot_to_csv.py`

---

## ESTIMATED EFFORT

| Phase | Items | Complexity | Est. Time |
|-------|-------|------------|-----------|
| 1 | 5 | Low | 30 min |
| 2 | 6 | Medium | 2 hours |
| 3 | 2 | High | 3 hours |
| 4 | 5 | Medium | 3 hours |
| 5 | 2 | Medium | 1.5 hours |
| 6 | 7 | Low-Medium | 2 hours |
| 7 | 2 | Medium | 1.5 hours |
| **Total** | **29** | - | **~13.5 hours** |

---

## DEPENDENCIES

```
Phase 1 (L1-L5) - No dependencies
    ↓
Phase 2 (#2, #6, #8, #11, #18, #19) - Foundation
    ↓
Phase 3 (#1, #5) - Depends on Phase 2 (database changes)
    ↓
Phase 4 (#3, #4, #7, #10, #12) - Depends on Phase 2 (repository)
    ↓
Phase 5 (#9, #15) - Independent
    ↓
Phase 6 (#17, #20-24) - Depends on Phase 3
    ↓
Phase 7 (#13, #16) - Independent (deferred)
```
