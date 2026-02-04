-- Migration v012: Batch Processing Improvements
-- Adds indexes and tables for reliable overnight batch processing

-- =============================================================================
-- INDEXES for better batch query performance
-- =============================================================================

-- Index on batch_items.ticker for faster lookups by ticker
CREATE INDEX IF NOT EXISTS idx_batch_items_ticker ON batch_items(ticker);

-- Composite index for finding items by batch and ticker
CREATE INDEX IF NOT EXISTS idx_batch_items_batch_ticker ON batch_items(batch_id, ticker);

-- Index for finding running items with stale heartbeats (watchdog)
CREATE INDEX IF NOT EXISTS idx_batch_items_heartbeat ON batch_items(status, last_heartbeat_at)
    WHERE status = 'running';

-- =============================================================================
-- Year-level checkpointing for resume capability
-- =============================================================================

-- Table to track completed years within a batch item
-- This allows resuming from the last completed year instead of restarting
CREATE TABLE IF NOT EXISTS batch_item_year_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_item_id INTEGER NOT NULL,
    fiscal_year INTEGER NOT NULL,
    result_id INTEGER,
    run_id TEXT,
    completed_at TEXT NOT NULL,

    FOREIGN KEY (batch_item_id) REFERENCES batch_items(id) ON DELETE CASCADE,
    UNIQUE(batch_item_id, fiscal_year)
);

CREATE INDEX IF NOT EXISTS idx_year_checkpoints_item ON batch_item_year_checkpoints(batch_item_id);
CREATE INDEX IF NOT EXISTS idx_year_checkpoints_item_year ON batch_item_year_checkpoints(batch_item_id, fiscal_year);

-- Add column to batch_items to track last completed year (for quick lookup)
-- Using ALTER TABLE with IF NOT EXISTS simulation for SQLite
-- SQLite doesn't support IF NOT EXISTS for columns, so we use a safe pattern
SELECT CASE
    WHEN (SELECT COUNT(*) FROM pragma_table_info('batch_items') WHERE name='last_completed_year') = 0
    THEN 'ALTER TABLE batch_items ADD COLUMN last_completed_year INTEGER'
END;

-- Note: The above SELECT doesn't actually execute the ALTER.
-- We need to do it directly but handle the error if it exists.
-- This is handled by the repository's migration logic that ignores "duplicate column" errors.

ALTER TABLE batch_items ADD COLUMN last_completed_year INTEGER;
