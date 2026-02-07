-- Add resume tracking for interrupted analyses
-- Track which years have been completed within a multi-year run

-- Add completed_years to track progress within a run
ALTER TABLE analysis_runs ADD COLUMN completed_years TEXT;  -- JSON array of completed years

-- Add last_activity timestamp for detecting stale runs
ALTER TABLE analysis_runs ADD COLUMN last_activity_at TIMESTAMP;

-- Index for finding interrupted runs
CREATE INDEX IF NOT EXISTS idx_runs_interrupted ON analysis_runs(status, last_activity_at)
WHERE status = 'running';
