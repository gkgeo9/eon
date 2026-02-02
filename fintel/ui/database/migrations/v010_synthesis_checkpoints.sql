-- Migration v010: Per-Company Synthesis Checkpoints
-- Enables resume capability for batch synthesis operations
-- Saves checkpoint after each company is synthesized

-- Synthesis jobs table - tracks a synthesis operation
CREATE TABLE IF NOT EXISTS synthesis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_job_id TEXT UNIQUE NOT NULL,
    batch_id TEXT NOT NULL,
    synthesis_type TEXT NOT NULL DEFAULT 'per_company',  -- 'per_company' or 'batch_aggregate'
    total_companies INTEGER NOT NULL,
    completed_companies INTEGER DEFAULT 0,
    failed_companies INTEGER DEFAULT 0,
    skipped_companies INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, paused, completed, failed
    synthesis_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_checkpoint_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (batch_id) REFERENCES batch_jobs(batch_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_synthesis_batch ON synthesis_jobs(batch_id);
CREATE INDEX IF NOT EXISTS idx_synthesis_status ON synthesis_jobs(status);

-- Individual company synthesis status within a job
CREATE TABLE IF NOT EXISTS synthesis_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    synthesis_job_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    source_run_id TEXT,           -- Original analysis run
    synthesis_run_id TEXT,        -- Generated synthesis run (if completed)
    num_years INTEGER,            -- Number of years being synthesized
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, skipped
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (synthesis_job_id) REFERENCES synthesis_jobs(synthesis_job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_synthesis_items_job ON synthesis_items(synthesis_job_id);
CREATE INDEX IF NOT EXISTS idx_synthesis_items_status ON synthesis_items(synthesis_job_id, status);
CREATE INDEX IF NOT EXISTS idx_synthesis_items_ticker ON synthesis_items(ticker);

-- Add synthesis_job_id reference to batch_jobs for linking
ALTER TABLE batch_jobs ADD COLUMN last_synthesis_job_id TEXT;
