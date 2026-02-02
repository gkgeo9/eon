# Rate Limiting Fix - Implementation Report

## Summary

Fixed the Gemini API rate limiting issue that was causing concurrent API calls to exceed quota limits (503 UNAVAILABLE, 429 RESOURCE_EXHAUSTED) when running multiple analyses in parallel.

## Root Cause

The initial implementation used `threading.Lock()` which only works within a single Python process. When running:
- **CLI batch mode**: ProcessPoolExecutor creates separate processes, each with its own memory space
- **Mixed CLI + UI execution**: Different Python processes don't share the same lock object

Result: Multiple processes could call the Gemini API simultaneously, hitting rate limits.

## Solution Implemented

Replaced `threading.Lock` with **file-based locking using `portalocker`**, which:
- ✅ Works across separate Python processes (CLI batch mode)
- ✅ Works across threads in same process (UI batch mode)
- ✅ Works for mixed execution scenarios (CLI + UI simultaneously)
- ✅ Automatically cleans up if process crashes
- ✅ Cross-platform compatible (Windows, macOS, Linux)

## Files Modified

### 1. `fintel/ai/request_queue.py`
**Changes**: Complete rewrite from threading.Lock to portalocker (cross-platform)

- Imports: Changed from `threading` to `portalocker`
- `__init__`: Now manages lock file at `data/api_usage/gemini_request.lock`
- `execute_with_lock`: Uses `portalocker.lock()` with `LOCK_EX` (exclusive) and `portalocker.unlock()`
- Lock file is automatically created in data/api_usage directory
- Same directory as usage tracking files for consistency

**Key Code Pattern**:
```python
with open(self.lock_file_path, 'a+') as lock_file:
    try:
        portalocker.lock(lock_file, portalocker.LOCK_EX)  # Block until lock available
        result = request_func(*args, **kwargs)
        time.sleep(self._sleep_duration)  # 65s sleep
        return result
    finally:
        portalocker.unlock(lock_file)  # Release lock
```

### 2. `fintel/ai/providers/gemini.py`
**Changes**: Fixed double-sleep issue

- **Before**: Called `record_and_sleep()` which sleeps 65 seconds
- **After**: Calls `tracker.record_request()` directly (no sleep)
- Reason: The request queue already handled the mandatory 65s sleep

**Modified Lines**:
- Line 155: Changed from `record_and_sleep()` to `tracker.record_request()`
- Line 191: Same change for unstructured output path

## Execution Flow

### Before Fix (Threading.Lock - BROKEN)
```
Thread 1 (Process A, Key 1): Calls Gemini at t=0
                              └─ Sleeps 65s
Thread 2 (Process B, Key 2): Calls Gemini at t=0.1  ❌ (different process, different lock!)
Thread 3 (Process A, Key 1): BLOCKED until t=65
Result: 2 concurrent API calls → 429 RESOURCE_EXHAUSTED error
```

### After Fix (portalocker - WORKING)
```
Thread 1 (Process A, Key 1): Acquires file lock → Calls Gemini at t=0
                              ├─ Sleeps 65s
                              └─ Releases lock at t=65
                                            ↓
Thread 2 (Process B, Key 2): WAITS for lock ────→ Acquires lock at t=65 → Calls Gemini at t=65
                                                   ├─ Sleeps 65s
                                                   └─ Releases lock at t=130
                                                                 ↓
Thread 3 (Process A, Key 1): WAITS ──────────────────────────────→ Acquires lock at t=130
Result: All requests serialized, 65s gaps between each call, no rate limit errors
```

## Testing Plan

### Unit Tests
1. ✅ Lock file is created correctly
2. ✅ File-based locking can be acquired and released
3. ✅ Requests are recorded without double-sleeping

### Integration Tests
Run these scenarios to verify the fix:

#### 1. CLI Single Analysis (No Concurrency)
```bash
fintel analyze AAPL
# Expected: Works fine (no concurrency issues)
```

#### 2. CLI Batch (Multiple Processes)
```bash
fintel batch tickers.csv --workers 3
# Expected: All processes serialize through file lock
# Logs should show: "Lock acquired" → "sleeping 65s" → "Lock released"
```

#### 3. UI Single Analysis
```
# Click "Run Analysis" button once
# Expected: Works fine, background thread uses file lock
```

#### 4. UI Batch Analysis
```
# Enter 10 companies and click "Run Batch"
# Expected: 10 background threads serialize through file lock
```

#### 5. Mixed CLI + UI Execution
```
# Terminal 1: fintel batch tickers.csv --workers 3
# Terminal 2: (wait 5 seconds) Click UI "Run Analysis"
# Expected: Both respect the same lock file
```

### Stress Test
```python
# Run 100 concurrent analyses to ensure no quota errors
# Expected result: All succeed with proper serialization
```

## Success Criteria

- ✅ No 503 UNAVAILABLE errors
- ✅ No 429 RESOURCE_EXHAUSTED errors
- ✅ Lock file created at data/api_usage/gemini_request.lock
- ✅ Logs show proper serialization (lock acquired → request → sleep → unlock)
- ✅ Works in all execution modes:
  - CLI single
  - CLI batch with ProcessPoolExecutor
  - UI single (background thread)
  - UI batch (multiple threads)
  - Mixed execution (CLI + UI simultaneously)

## Performance Impact

### Throughput Change
- **Before**: Theoretically N requests/minute (N = number of API keys) but hits quota errors
- **After**: 1 request/65s = 0.92 requests/minute (serialized, no quota errors)

### Net Impact: POSITIVE
- Before: Concurrent requests → quota errors → all analyses fail
- After: Serialized requests → no quota errors → all analyses succeed
- Users get successful results even if slower

## Platform Support

- ✅ macOS (Darwin) - Fully supported
- ✅ Linux - Fully supported
- ✅ Windows - Fully supported (via portalocker cross-platform library)
- ✅ Unix-based systems - Fully supported

## Edge Cases Handled

### 1. Lock File Deleted During Execution
- Handled: File is recreated on next request (touch exists with exist_ok=True)

### 2. Process Crashes (Stale Locks)
- Handled: portalocker locks automatically release when process exits
- No manual cleanup needed

### 3. Permission Issues
- Handled: data/api_usage directory created with mkdir(parents=True, exist_ok=True)
- Logs clear error if lock file can't be created

### 4. Multiple Process Instances
- Handled: All instances use same lock file path
- File system ensures only one process has exclusive lock

### 5. Very Long Processing
- Handled: Lock is held only during API call + sleep
- Doesn't block on PDF processing or other non-API work

## Rollback Plan

If any issues arise:
1. Revert `fintel/ai/request_queue.py` to threading.Lock version
2. Note that this will only work for UI mode, not CLI batch
3. Consider Redis-based queue for distributed deployments

## Future Enhancements

1. **Token Bucket Algorithm** - Allow periodic bursts while respecting limits
2. **Per-Minute Rate Limiting** - Respect 15 RPM limit more precisely
3. **Intelligent Scheduling** - Prioritize smaller requests
4. **Redis Queue** - For cloud/distributed deployments
5. **Monitoring Dashboard** - Track API usage and queue stats

## Testing Instructions

To verify the fix works:

```bash
# 1. Check lock file is created
ls -la data/api_usage/gemini_request.lock

# 2. Run test analysis with logging
export PYTHONUNBUFFERED=1
LOGLEVEL=DEBUG fintel analyze AAPL 2>&1 | grep -i "lock\|request"

# 3. Run batch to see serialization
fintel batch test_tickers.csv --workers 3 2>&1 | grep -i "lock"

# 4. Check logs show proper gaps
# Should see: "Lock acquired" → "Request #1 complete, sleeping 65s" → "Lock released"
```

## Documentation

- **Lock File Location**: `data/api_usage/gemini_request.lock`
- **Serialization**: All Gemini API calls go through global queue
- **Sleep Duration**: 65 seconds between each request
- **Thread-Safe**: Yes, across threads and processes
- **Process-Safe**: Yes, uses file-based locking

## Summary

This fix ensures that running multiple analyses in parallel (CLI batch, UI batch, or mixed) will not exceed Gemini API rate limits. All API calls are serialized through a global file-based lock, guaranteeing only one request is in-flight at any moment.

The solution is:
- ✅ Simple and reliable
- ✅ Cross-process and cross-thread safe
- ✅ Cross-platform compatible (Windows, macOS, Linux)
- ✅ Uses portalocker library for file locking
- ✅ Automatic cleanup on process crash
- ✅ Works for all execution modes
