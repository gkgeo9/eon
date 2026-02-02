-- Migration v009: CIK Support for Delisted Companies
-- Adds ability to analyze companies by CIK (Central Index Key) instead of ticker
-- Essential for delisted companies like Enron that don't appear in active company lists

-- Add CIK column to analysis_runs for audit trail
ALTER TABLE analysis_runs ADD COLUMN cik TEXT;

-- Add input_mode to track whether user entered ticker or CIK
ALTER TABLE analysis_runs ADD COLUMN input_mode TEXT DEFAULT 'ticker';

-- Create CIK-to-company cache table for resolved company names
-- This caches SEC lookups to avoid repeated API calls
CREATE TABLE IF NOT EXISTS cik_company_cache (
    cik TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    former_names TEXT,  -- JSON array of former names for delisted companies
    sic_code TEXT,
    sic_description TEXT,
    state_of_incorporation TEXT,
    fiscal_year_end TEXT,  -- MMDD format
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cik_cache_name ON cik_company_cache(company_name);
