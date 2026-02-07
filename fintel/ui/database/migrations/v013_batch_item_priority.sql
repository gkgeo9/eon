-- v013: Add priority column to batch_items for priority-based ordering.
-- Higher priority values are processed first (default 0).
-- This enables high-interest tickers to be processed before others.

ALTER TABLE batch_items ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_batch_items_priority
ON batch_items (batch_id, status, priority DESC, id);
