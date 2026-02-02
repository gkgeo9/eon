-- Migration v007: Add filing_date column to file_cache for universal file naming
-- This allows all filing types (annual, quarterly, event) to use filing_date as identifier

-- Add filing_date column to file_cache table
ALTER TABLE file_cache ADD COLUMN filing_date TEXT;

-- Create index for efficient lookups by ticker + filing_date + filing_type
CREATE INDEX IF NOT EXISTS idx_cache_ticker_filing_date ON file_cache(ticker, filing_date, filing_type);

-- Note: Existing cached files will have NULL filing_date
-- The system will fall back to year-based lookup for backwards compatibility
