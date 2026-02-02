-- Add CIK and input mode support to analysis_runs table
-- Migration v008: Add CIK columns to support CIK-based lookups and filing_date to file_cache

-- Add cik column to analysis_runs
ALTER TABLE analysis_runs ADD COLUMN cik TEXT;

-- Add input_mode column to track whether input was ticker or CIK
ALTER TABLE analysis_runs ADD COLUMN input_mode TEXT DEFAULT 'ticker';

-- Create index on cik for faster lookups
CREATE INDEX IF NOT EXISTS idx_runs_cik ON analysis_runs(cik);

-- Add filing_date column to file_cache for event-based filings
ALTER TABLE file_cache ADD COLUMN filing_date TEXT;

-- Create index on filing_date for faster lookups
CREATE INDEX IF NOT EXISTS idx_cache_filing_date ON file_cache(ticker, filing_date, filing_type);

-- Create CIK to company cache table
CREATE TABLE IF NOT EXISTS cik_company_cache (
    cik TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    former_names TEXT,                      -- JSON array of former names
    sic_code TEXT,
    sic_description TEXT,
    state_of_incorporation TEXT,
    fiscal_year_end TEXT,                   -- MMDD format
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cik_cache_name ON cik_company_cache(company_name);
