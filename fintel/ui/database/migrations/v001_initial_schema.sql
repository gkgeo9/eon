-- Fintel UI Database Schema
-- SQLite database for storing analysis runs, results, and user preferences

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Analysis runs table: tracks each analysis job
CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,              -- UUID for reference
    ticker TEXT NOT NULL,
    company_name TEXT,
    analysis_type TEXT NOT NULL,               -- fundamental, excellent, objective, buffett, taleb, contrarian, multi
    filing_type TEXT NOT NULL DEFAULT '10-K',  -- 10-K, 10-Q, 8-K, etc.
    years_analyzed TEXT,                       -- JSON array: ["2023", "2024"]
    status TEXT NOT NULL DEFAULT 'pending',    -- pending, running, completed, failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    config_json TEXT                           -- JSON with full configuration
);

CREATE INDEX IF NOT EXISTS idx_runs_ticker ON analysis_runs(ticker);
CREATE INDEX IF NOT EXISTS idx_runs_status ON analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON analysis_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_type ON analysis_runs(analysis_type);

-- Analysis results table: stores Pydantic model outputs
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,                      -- Foreign key to analysis_runs
    ticker TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    filing_type TEXT NOT NULL DEFAULT '10-K',
    result_type TEXT NOT NULL,                 -- TenKAnalysis, BuffettAnalysis, etc.
    result_json TEXT NOT NULL,                 -- Full Pydantic model as JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES analysis_runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_results_run ON analysis_results(run_id);
CREATE INDEX IF NOT EXISTS idx_results_ticker_year ON analysis_results(ticker, fiscal_year);

-- Custom prompts library
CREATE TABLE IF NOT EXISTS custom_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    analysis_type TEXT NOT NULL,               -- fundamental, buffett, taleb, contrarian
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_prompts_type ON custom_prompts(analysis_type);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON custom_prompts(is_active);

-- User settings/preferences
CREATE TABLE IF NOT EXISTS user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File cache (track downloaded PDFs)
CREATE TABLE IF NOT EXISTS file_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    filing_type TEXT NOT NULL DEFAULT '10-K',
    file_path TEXT NOT NULL,
    file_hash TEXT,                            -- SHA256 for integrity
    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, fiscal_year, filing_type)
);

CREATE INDEX IF NOT EXISTS idx_cache_ticker ON file_cache(ticker);
CREATE INDEX IF NOT EXISTS idx_cache_ticker_year ON file_cache(ticker, fiscal_year);

-- Views for convenience

-- Latest analysis for each ticker
CREATE VIEW IF NOT EXISTS latest_analyses AS
SELECT
    ar.ticker,
    ar.company_name,
    ar.analysis_type,
    ar.status,
    ar.completed_at,
    ar.run_id,
    COUNT(ares.id) as num_years
FROM analysis_runs ar
LEFT JOIN analysis_results ares ON ar.run_id = ares.run_id
WHERE ar.status = 'completed'
GROUP BY ar.ticker, ar.analysis_type
HAVING ar.completed_at = (
    SELECT MAX(completed_at)
    FROM analysis_runs
    WHERE ticker = ar.ticker AND analysis_type = ar.analysis_type
);

-- Analysis summary stats
CREATE VIEW IF NOT EXISTS analysis_stats AS
SELECT
    analysis_type,
    status,
    COUNT(*) as count,
    DATE(created_at) as date
FROM analysis_runs
GROUP BY analysis_type, status, DATE(created_at);
