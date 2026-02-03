-- Migration v010: Per-Company Synthesis Checkpoints (additive indexes only)
-- Note: synthesis_jobs, synthesis_items, and batch_jobs.last_synthesis_job_id
-- are already created by v007_batch_queue_and_synthesis.sql
-- This migration only adds additional indexes for performance

-- Additional index for synthesis items by ticker (for cross-job lookups)
CREATE INDEX IF NOT EXISTS idx_synthesis_items_ticker ON synthesis_items(ticker);
