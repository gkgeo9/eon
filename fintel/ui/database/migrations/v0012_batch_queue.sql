-- Migration v008: Batch queue system for large-scale multi-day analysis
-- Supports running 1000+ tickers over multiple days with automatic rate limit handling

-- Batch jobs table - tracks overall batch job status
CREATE TABLE IF NOT EXISTS batch_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    total_tickers INTEGER NOT NULL,
    completed_tickers INTEGER DEFAULT 0,
    failed_tickers INTEGER DEFAULT 0,
    skipped_tickers INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, paused, waiting_reset, completed, failed, stopped
    analysis_type TEXT NOT NULL,
    filing_type TEXT NOT NULL DEFAULT '10-K',
    num_years INTEGER DEFAULT 5,
    config_json TEXT,                         -- Additional config (custom_prompt, max_retries, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    estimated_completion TEXT,                -- ISO datetime estimate
    error_message TEXT,
    priority INTEGER DEFAULT 0                -- Higher = higher priority
);

CREATE INDEX IF NOT EXISTS idx_batch_status ON batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_created ON batch_jobs(created_at DESC);

-- Individual tickers within a batch
CREATE TABLE IF NOT EXISTS batch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending, running, completed, failed, skipped
    run_id TEXT,                              -- Links to analysis_runs when started
    attempts INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (batch_id) REFERENCES batch_jobs(batch_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_batch_items_batch ON batch_items(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_items_status ON batch_items(batch_id, status);
CREATE INDEX IF NOT EXISTS idx_batch_items_ticker ON batch_items(ticker);

-- Queue state (singleton) - tracks global queue status
CREATE TABLE IF NOT EXISTS queue_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),    -- Singleton row
    is_running BOOLEAN DEFAULT 0,
    current_batch_id TEXT,
    current_item_id INTEGER,
    next_run_at TIMESTAMP,                    -- When to resume (after midnight PST)
    daily_requests_made INTEGER DEFAULT 0,    -- Today's request count
    last_reset_date TEXT,                     -- Track when limits reset (YYYY-MM-DD)
    worker_pid INTEGER,                       -- Process ID of worker
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial singleton row if not exists
INSERT OR IGNORE INTO queue_state (id, is_running, daily_requests_made) VALUES (1, 0, 0);

-- Queue history for tracking daily progress
CREATE TABLE IF NOT EXISTS queue_daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                       -- YYYY-MM-DD
    batch_id TEXT,
    tickers_completed INTEGER DEFAULT 0,
    tickers_failed INTEGER DEFAULT 0,
    api_requests INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    notes TEXT,
    UNIQUE(date, batch_id)
);

CREATE INDEX IF NOT EXISTS idx_queue_daily_date ON queue_daily_stats(date DESC);
