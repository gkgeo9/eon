-- Workflow Execution Engine Schema
-- Adds tables for workflow definitions, runs, and step outputs

-- Workflow definitions (already stored as JSON files, but also in DB for querying)
CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    workflow_json TEXT NOT NULL,  -- Full workflow definition (steps, configs, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);
CREATE INDEX IF NOT EXISTS idx_workflows_created ON workflows(created_at DESC);

-- Workflow execution runs
CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,  -- UUID
    workflow_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, paused
    current_step_index INTEGER DEFAULT 0,
    total_steps INTEGER NOT NULL,

    -- Progress tracking
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_successful_step TEXT,

    -- Error tracking
    errors_json TEXT,  -- JSON array of errors

    -- Metadata
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_created ON workflow_runs(created_at DESC);

-- Step outputs (for resume capability and intermediate results)
CREATE TABLE IF NOT EXISTS workflow_step_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    output_json TEXT NOT NULL,  -- Serialized DataContainer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE,
    UNIQUE(workflow_run_id, step_id)
);

CREATE INDEX IF NOT EXISTS idx_step_outputs_run ON workflow_step_outputs(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_step_outputs_step ON workflow_step_outputs(step_id);

-- Step execution logs
CREATE TABLE IF NOT EXISTS workflow_step_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    log_level TEXT NOT NULL,  -- INFO, WARNING, ERROR
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_step_logs_run ON workflow_step_logs(workflow_run_id);
CREATE INDEX IF NOT EXISTS idx_step_logs_level ON workflow_step_logs(log_level);

-- View for workflow run status with details
CREATE VIEW IF NOT EXISTS workflow_run_details AS
SELECT
    wr.id as run_id,
    wr.workflow_id,
    w.name as workflow_name,
    w.description as workflow_description,
    wr.status,
    wr.current_step_index,
    wr.total_steps,
    wr.started_at,
    wr.completed_at,
    wr.last_successful_step,
    wr.errors_json,
    (wr.current_step_index * 100.0 / wr.total_steps) as progress_percent,
    COUNT(DISTINCT wsl.id) as log_count,
    COUNT(DISTINCT wso.id) as step_output_count
FROM workflow_runs wr
JOIN workflows w ON wr.workflow_id = w.id
LEFT JOIN workflow_step_logs wsl ON wr.id = wsl.workflow_run_id
LEFT JOIN workflow_step_outputs wso ON wr.id = wso.workflow_run_id
GROUP BY wr.id;
