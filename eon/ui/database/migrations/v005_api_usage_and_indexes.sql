-- v005: Add API usage tracking table and additional performance indexes
-- Migration date: 2024-12

-- API usage tracking table: stores API call statistics per key
CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_suffix TEXT NOT NULL,             -- Last 4 chars of API key (for privacy)
    usage_date DATE NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api_key_suffix, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage(usage_date DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_key ON api_usage(api_key_suffix);

-- Additional performance indexes for common queries

-- Composite index for filtering by multiple columns
CREATE INDEX IF NOT EXISTS idx_runs_ticker_type_status ON analysis_runs(ticker, analysis_type, status);

-- Index for date range queries
CREATE INDEX IF NOT EXISTS idx_runs_created_date ON analysis_runs(DATE(created_at));

-- Index for results by type and ticker
CREATE INDEX IF NOT EXISTS idx_results_ticker_type ON analysis_results(ticker, result_type);

-- Index for results created_at (for recent results queries)
CREATE INDEX IF NOT EXISTS idx_results_created ON analysis_results(created_at DESC);
