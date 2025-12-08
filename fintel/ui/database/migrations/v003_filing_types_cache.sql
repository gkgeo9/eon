-- Migration v003: Add filing types cache table
-- Purpose: Cache available filing types per ticker to avoid repeated SEC API calls

CREATE TABLE IF NOT EXISTS filing_types_cache (
    ticker TEXT PRIMARY KEY,
    filing_types TEXT NOT NULL,  -- JSON array of filing types
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_filing_types_cache_ticker ON filing_types_cache(ticker);
CREATE INDEX IF NOT EXISTS idx_filing_types_cache_cached_at ON filing_types_cache(cached_at);
