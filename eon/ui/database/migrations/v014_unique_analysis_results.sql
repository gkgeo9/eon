-- Fix duplicate analysis results caused by double-save pattern
-- store_result() uses INSERT OR IGNORE but no UNIQUE constraint existed,
-- so both incremental and final saves succeeded, creating duplicates.

-- Step 1: Remove existing duplicate rows, keeping the earliest entry
DELETE FROM analysis_results
WHERE id NOT IN (
    SELECT MIN(id)
    FROM analysis_results
    GROUP BY run_id, ticker, fiscal_year, filing_type, result_type
);

-- Step 2: Add UNIQUE constraint so INSERT OR IGNORE works correctly
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_results_unique
ON analysis_results(run_id, ticker, fiscal_year, filing_type, result_type);
