-- v007: Add batch queue and synthesis checkpoint tables
-- Migration date: 2024-12

CREATE TABLE IF NOT EXISTS batch_jobs (
    batch_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    total_tickers INTEGER NOT NULL,
    completed_tickers INTEGER NOT NULL DEFAULT 0,
    failed_tickers INTEGER NOT NULL DEFAULT 0,
    skipped_tickers INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    analysis_type TEXT NOT NULL,
    filing_type TEXT NOT NULL DEFAULT '10-K',
    num_years INTEGER NOT NULL DEFAULT 1,
    config_json TEXT,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    estimated_completion TIMESTAMP,
    error_message TEXT,
    last_synthesis_job_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(status);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_created ON batch_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_priority ON batch_jobs(priority DESC);

CREATE TABLE IF NOT EXISTS batch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    run_id TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    lease_owner TEXT,
    lease_expires_at TIMESTAMP,
    last_heartbeat_at TIMESTAMP,
    priority INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (batch_id) REFERENCES batch_jobs(batch_id) ON DELETE CASCADE,
    UNIQUE(batch_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_batch_items_status ON batch_items(batch_id, status);
CREATE INDEX IF NOT EXISTS idx_batch_items_lease ON batch_items(batch_id, lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_batch_items_priority ON batch_items(batch_id, priority DESC, id);

CREATE TABLE IF NOT EXISTS queue_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_running INTEGER NOT NULL DEFAULT 0,
    current_batch_id TEXT,
    next_run_at TIMESTAMP,
    daily_requests_made INTEGER DEFAULT 0,
    last_reset_date DATE,
    worker_pid INTEGER,
    worker_id TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO queue_state (id, is_running)
SELECT 1, 0
WHERE NOT EXISTS (SELECT 1 FROM queue_state WHERE id = 1);

CREATE TABLE IF NOT EXISTS synthesis_jobs (
    synthesis_job_id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    synthesis_type TEXT NOT NULL DEFAULT 'per_company',
    total_companies INTEGER NOT NULL,
    completed_companies INTEGER NOT NULL DEFAULT 0,
    failed_companies INTEGER NOT NULL DEFAULT 0,
    skipped_companies INTEGER NOT NULL DEFAULT 0,
    synthesis_prompt TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_checkpoint_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (batch_id) REFERENCES batch_jobs(batch_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_synthesis_jobs_status ON synthesis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_synthesis_jobs_batch ON synthesis_jobs(batch_id);

CREATE TABLE IF NOT EXISTS synthesis_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_job_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    source_run_id TEXT,
    num_years INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    synthesis_run_id TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (synthesis_job_id) REFERENCES synthesis_jobs(synthesis_job_id) ON DELETE CASCADE,
    UNIQUE(synthesis_job_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_synthesis_items_status ON synthesis_items(synthesis_job_id, status);
