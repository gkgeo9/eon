-- Add progress tracking to analysis_runs table
ALTER TABLE analysis_runs ADD COLUMN progress_message TEXT;
ALTER TABLE analysis_runs ADD COLUMN progress_percent INTEGER DEFAULT 0;
ALTER TABLE analysis_runs ADD COLUMN current_step TEXT;
ALTER TABLE analysis_runs ADD COLUMN total_steps INTEGER DEFAULT 0;
