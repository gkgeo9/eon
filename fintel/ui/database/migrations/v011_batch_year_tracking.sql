-- v011: Add year tracking columns to batch_items for per-company year progress
-- Migration date: 2026-02

-- Add columns to track year-level progress per batch item
-- total_years: Total number of years to analyze for this company
-- completed_years: Number of years successfully analyzed
-- completed_years_list: JSON array of completed year numbers (e.g., ["2024", "2023", "2022"])
-- current_year: The year currently being processed (for progress display)

ALTER TABLE batch_items ADD COLUMN total_years INTEGER NOT NULL DEFAULT 1;
ALTER TABLE batch_items ADD COLUMN completed_years INTEGER NOT NULL DEFAULT 0;
ALTER TABLE batch_items ADD COLUMN completed_years_list TEXT DEFAULT '[]';
ALTER TABLE batch_items ADD COLUMN current_year TEXT;
