# Workflow Execution Engine - Design Document

## Overview

The Workflow Engine executes multi-step analysis pipelines defined by the Workflow Builder. It manages data flow between steps, handles aggregations, integrates with existing caching, and provides robust error handling.

## Core Concepts

### 1. Data Shape Tracking

Every step in the workflow operates on data with a defined **shape**: `(companies × years)`

**Example Flow:**
```
Input: 3 companies × 4 years = (3, 4) shape
  ↓
Analysis: Each document analyzed = (3, 4) analyses
  ↓
Aggregate by Company: Combine years = (3, 1) company summaries
  ↓
Aggregate by Year: Combine companies = (1, 4) year summaries
  ↓
Merge All: Single report = (1, 1)
```

### 2. Data Container

All data flowing between steps is wrapped in a `DataContainer`:

```python
@dataclass
class DataContainer:
    """Wrapper for data with metadata tracking."""

    # Data structure: Dict[ticker, Dict[year, analysis_result]]
    data: Dict[str, Dict[int, Any]]

    # Shape tracking
    num_companies: int
    num_years_per_company: Dict[str, int]  # May vary per company

    # Metadata
    step_id: str
    step_type: str
    created_at: datetime

    # Lineage tracking
    source_run_ids: List[str]  # Original analysis run IDs

    @property
    def shape(self) -> Tuple[int, int]:
        """Returns (num_companies, max_years)."""
        max_years = max(self.num_years_per_company.values()) if self.num_years_per_company else 0
        return (self.num_companies, max_years)

    @property
    def total_items(self) -> int:
        """Total number of data items."""
        return sum(len(years) for years in self.data.values())
```

## Architecture Components

### 1. WorkflowEngine

**Purpose:** Main orchestrator that executes workflow steps sequentially.

```python
class WorkflowEngine:
    """
    Executes a workflow definition step-by-step.

    Responsibilities:
    - Load workflow JSON
    - Initialize workflow state
    - Execute steps in sequence
    - Pass data between steps
    - Handle errors and recovery
    - Save workflow run results
    """

    def __init__(self, db: DatabaseRepository, analysis_service: AnalysisService):
        self.db = db
        self.analysis_service = analysis_service
        self.step_executors = self._register_executors()

    def execute_workflow(self, workflow_id: str, workflow_run_id: str) -> WorkflowResult:
        """Execute entire workflow."""
        # 1. Load workflow definition
        # 2. Initialize state
        # 3. Execute each step
        # 4. Save results
        # 5. Return summary

    def execute_step(self, step_config: Dict, input_data: DataContainer) -> DataContainer:
        """Execute a single step."""
        # 1. Validate input shape
        # 2. Get appropriate executor
        # 3. Execute step
        # 4. Validate output
        # 5. Return result
```

### 2. StepExecutor (Abstract Base)

**Purpose:** Base class for all step executors.

```python
class StepExecutor(ABC):
    """Base class for step executors."""

    @abstractmethod
    def execute(self, config: Dict, input_data: Optional[DataContainer]) -> DataContainer:
        """Execute the step logic."""
        pass

    @abstractmethod
    def validate_input(self, input_data: Optional[DataContainer]) -> bool:
        """Validate input data shape/type."""
        pass

    @abstractmethod
    def expected_output_shape(self, input_shape: Tuple[int, int]) -> Tuple[int, int]:
        """Calculate expected output shape."""
        pass
```

### 3. Specific Step Executors

#### a. InputStepExecutor

```python
class InputStepExecutor(StepExecutor):
    """
    Handles company & year input definition.

    Input: None (first step)
    Output: DataContainer with empty analysis placeholders
    Shape: (num_tickers, num_years)

    Config:
    - tickers: List[str]
    - years: List[int] OR num_years: int
    - filing_type: str
    """

    def execute(self, config: Dict, input_data: None) -> DataContainer:
        # 1. Parse tickers and years
        # 2. Create placeholder structure
        # 3. Return DataContainer with shape info
```

#### b. FundamentalAnalysisExecutor

```python
class FundamentalAnalysisExecutor(StepExecutor):
    """
    Run fundamental analysis on each document.

    Input: DataContainer (any shape)
    Output: DataContainer (same shape, with fundamental analyses)

    Config:
    - run_mode: "per_filing" | "aggregated"
    - custom_prompt: Optional[str]

    Behavior:
    - Per filing: Analyze each (ticker, year) independently
    - Aggregated: Combine all years per ticker first, then analyze

    Integration:
    - Uses AnalysisService.run_analysis()
    - Checks cache via DatabaseRepository
    - Creates new run_id for each analysis
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. Determine run mode
        # 2. For each ticker:
        #    a. Check cache for existing analyses
        #    b. Run new analyses if needed
        #    c. Store run_ids
        # 3. Collect all results
        # 4. Return DataContainer with analyses
```

#### c. SuccessFactorsExecutor

```python
class SuccessFactorsExecutor(StepExecutor):
    """
    Extract success factors using ExcellentCompanyAnalyzer or ObjectiveCompanyAnalyzer.

    Input: DataContainer with fundamental analyses
    Output: DataContainer (potentially aggregated)

    Config:
    - analyzer_type: "objective" | "excellent"
    - aggregate_by: "company" | "year" | "none"

    Behavior:
    - Aggregate_by="company": Combines all years per company → (num_companies, 1)
    - Aggregate_by="year": Combines all companies per year → (1, num_years)
    - Aggregate_by="none": Runs on each (ticker, year) → same shape
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. Group data based on aggregate_by
        # 2. For each group:
        #    a. Combine fundamental analyses
        #    b. Run ExcellentCompanyAnalyzer or ObjectiveCompanyAnalyzer
        # 3. Return new DataContainer with updated shape
```

#### d. PerspectiveAnalysisExecutor

```python
class PerspectiveAnalysisExecutor(StepExecutor):
    """
    Apply investment perspective lenses (Buffett/Taleb/Contrarian).

    Input: DataContainer with fundamental analyses
    Output: DataContainer (same shape, with perspective analyses)

    Config:
    - perspectives: List["buffett" | "taleb" | "contrarian"]
    - run_parallel: bool
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. For each (ticker, year) in input
        # 2. Run each perspective analysis
        # 3. Combine perspective results
        # 4. Return DataContainer
```

#### e. CustomPromptExecutor

```python
class CustomPromptExecutor(StepExecutor):
    """
    Run custom prompt on aggregated data.

    Input: DataContainer (any shape)
    Output: DataContainer (potentially different shape)

    Config:
    - prompt: str (can reference {company_data})
    - output_format: "structured_json" | "free_text" | "comparison_table"
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. Format input data for prompt
        # 2. Replace placeholders
        # 3. Call LLM
        # 4. Parse response
        # 5. Return DataContainer
```

#### f. FilterExecutor

```python
class FilterExecutor(StepExecutor):
    """
    Filter results based on criteria.

    Input: DataContainer
    Output: DataContainer (subset of input)

    Config:
    - field: str (JSON path to field)
    - operator: ">" | ">=" | "<" | "<=" | "==" | "!=" | "contains"
    - value: Any
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. Extract field from each result
        # 2. Apply operator
        # 3. Keep matching items
        # 4. Return filtered DataContainer
```

#### g. AggregateExecutor

```python
class AggregateExecutor(StepExecutor):
    """
    Aggregate/combine results.

    Input: DataContainer
    Output: DataContainer (different shape)

    Config:
    - operation: "merge_all" | "group_by_company" | "group_by_year" | "top_n" | "average_metrics"
    - n: int (for top_n)
    - score_field: str (for top_n)
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # Based on operation:
        # - merge_all: (N, M) → (1, 1)
        # - group_by_company: (N, M) → (N, 1)
        # - group_by_year: (N, M) → (1, M)
        # - top_n: (N, M) → (n, M) or (N, m)
```

#### h. ExportExecutor

```python
class ExportExecutor(StepExecutor):
    """
    Export results to files.

    Input: DataContainer
    Output: Same DataContainer (pass-through) + exported files

    Config:
    - formats: List["json" | "csv" | "excel" | "pdf"]
    - include_metadata: bool
    - include_raw_data: bool
    """

    def execute(self, config: Dict, input_data: DataContainer) -> DataContainer:
        # 1. Export to each format
        # 2. Save to workflows/exports/
        # 3. Return original data (pass-through)
```

### 4. WorkflowState

**Purpose:** Track execution progress and enable resume.

```python
@dataclass
class WorkflowState:
    """Tracks workflow execution state."""

    workflow_run_id: str
    workflow_id: str

    # Progress tracking
    current_step_index: int
    total_steps: int
    status: Literal["pending", "running", "completed", "failed", "paused"]

    # Data passing
    step_outputs: Dict[str, DataContainer]  # step_id → output

    # Error tracking
    errors: List[Dict[str, Any]]

    # Timing
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Resume capability
    last_successful_step: Optional[str]

    def save(self, db: DatabaseRepository):
        """Persist state to database."""
        # Save to workflow_runs table

    @classmethod
    def load(cls, workflow_run_id: str, db: DatabaseRepository) -> "WorkflowState":
        """Load state from database."""
        # Load from workflow_runs table
```

## Data Flow Examples

### Example 1: Basic Multi-Company Analysis

**Workflow:**
```json
{
  "steps": [
    {
      "step_id": "input_1",
      "type": "input",
      "config": {
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "num_years": 4,
        "filing_type": "10-K"
      }
    },
    {
      "step_id": "fundamental_1",
      "type": "fundamental_analysis",
      "config": {
        "run_mode": "per_filing"
      }
    },
    {
      "step_id": "aggregate_1",
      "type": "aggregate",
      "config": {
        "operation": "group_by_company"
      }
    },
    {
      "step_id": "compare_1",
      "type": "custom_analysis",
      "config": {
        "prompt": "Compare these 3 companies and rank by investment potential...",
        "output_format": "comparison_table"
      }
    }
  ]
}
```

**Data Flow:**
```
Step 1 (Input):
  Input: None
  Output: DataContainer(shape=(3, 4), data={
    "AAPL": {2024: None, 2023: None, 2022: None, 2021: None},
    "MSFT": {...},
    "GOOGL": {...}
  })

Step 2 (Fundamental Analysis):
  Input: (3, 4) placeholders
  Processing:
    - AAPL 2024: run_analysis() → run_id_1
    - AAPL 2023: run_analysis() → run_id_2
    - ... (12 total analyses)
  Output: DataContainer(shape=(3, 4), data={
    "AAPL": {2024: TenKAnalysis(...), 2023: TenKAnalysis(...), ...},
    "MSFT": {...},
    "GOOGL": {...}
  })

Step 3 (Aggregate by Company):
  Input: (3, 4) analyses
  Processing:
    - AAPL: Combine 4 years → CompanySummary
    - MSFT: Combine 4 years → CompanySummary
    - GOOGL: Combine 4 years → CompanySummary
  Output: DataContainer(shape=(3, 1), data={
    "AAPL": {None: CompanySummary(...)},
    "MSFT": {None: CompanySummary(...)},
    "GOOGL": {None: CompanySummary(...)}
  })

Step 4 (Compare):
  Input: (3, 1) summaries
  Processing:
    - Combine all 3 summaries into prompt
    - Call LLM
  Output: DataContainer(shape=(1, 1), data={
    "ALL": {None: ComparisonReport(...)}
  })
```

### Example 2: Year-over-Year Analysis

**Workflow:**
```json
{
  "steps": [
    {
      "step_id": "input_1",
      "type": "input",
      "config": {
        "tickers": ["AAPL"],
        "years": [2024, 2023, 2022, 2021, 2020],
        "filing_type": "10-K"
      }
    },
    {
      "step_id": "fundamental_1",
      "type": "fundamental_analysis",
      "config": {
        "run_mode": "per_filing"
      }
    },
    {
      "step_id": "success_1",
      "type": "success_factors",
      "config": {
        "analyzer_type": "excellent",
        "aggregate_by": "company"
      }
    }
  ]
}
```

**Data Flow:**
```
Step 1: (1, 5) → 1 company, 5 years
Step 2: (1, 5) → 5 fundamental analyses
Step 3: (1, 1) → 1 multi-year success factor analysis
```

### Example 3: Filter + Top N

**Workflow:**
```json
{
  "steps": [
    {
      "step_id": "input_1",
      "type": "input",
      "config": {
        "tickers": ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN"],
        "num_years": 3,
        "filing_type": "10-K"
      }
    },
    {
      "step_id": "scanner_1",
      "type": "scanner",
      "config": {}
    },
    {
      "step_id": "filter_1",
      "type": "filter",
      "config": {
        "field": "compounder_score.total_score",
        "operator": ">",
        "value": 400
      }
    },
    {
      "step_id": "top_3",
      "type": "aggregate",
      "config": {
        "operation": "top_n",
        "n": 3,
        "score_field": "compounder_score.total_score"
      }
    }
  ]
}
```

**Data Flow:**
```
Step 1: (7, 3) → 7 companies, 3 years each
Step 2: (7, 1) → Scanner aggregates per company
Step 3: (5, 1) → Filter keeps only score > 400 (assume 5 pass)
Step 4: (3, 1) → Top 3 by score
```

## Edge Cases & Error Handling

### 1. Missing Filings

**Scenario:** Company doesn't have filing for a specific year.

**Handling:**
```python
class InputStepExecutor:
    def execute(self, config, input_data):
        # Try to fetch filing
        try:
            filing = self.fetch_filing(ticker, year, filing_type)
        except FilingNotFoundError:
            # Log warning
            logger.warning(f"Filing not found: {ticker} {year} {filing_type}")
            # Store None placeholder
            data[ticker][year] = None
            # Add to missing_filings list
            metadata["missing_filings"].append({
                "ticker": ticker,
                "year": year,
                "filing_type": filing_type,
                "reason": "not_found"
            })
```

**Impact on Shape:**
- Shape still reflects requested dimensions: (3, 4)
- But `total_items` may be less: e.g., 11 instead of 12
- Downstream steps must handle None values

### 2. Analysis Failures

**Scenario:** LLM API call fails, rate limit hit, or parsing error.

**Handling:**
```python
class FundamentalAnalysisExecutor:
    def execute(self, config, input_data):
        results = {}
        errors = []

        for ticker, years in input_data.data.items():
            for year, doc in years.items():
                if doc is None:
                    continue

                try:
                    result = self.run_analysis(ticker, year, doc)
                    results[ticker][year] = result
                except RateLimitError as e:
                    # Implement exponential backoff
                    time.sleep(60)
                    result = self.run_analysis(ticker, year, doc)
                    results[ticker][year] = result
                except AnalysisError as e:
                    # Log error but continue
                    logger.error(f"Analysis failed: {ticker} {year}: {e}")
                    results[ticker][year] = None
                    errors.append({
                        "ticker": ticker,
                        "year": year,
                        "error": str(e),
                        "step": "fundamental_analysis"
                    })

        # If too many failures, fail the step
        failure_rate = len(errors) / input_data.total_items
        if failure_rate > 0.5:  # 50% threshold
            raise StepExecutionError(f"Too many failures: {len(errors)}/{input_data.total_items}")

        return DataContainer(data=results, errors=errors, ...)
```

### 3. Type Mismatches

**Scenario:** Step expects different input type than previous step output.

**Handling:**
```python
class WorkflowEngine:
    def execute_step(self, step_config, input_data):
        executor = self.get_executor(step_config["type"])

        # Validate input
        if not executor.validate_input(input_data):
            raise StepValidationError(
                f"Step {step_config['step_id']} ({step_config['type']}) "
                f"cannot accept input from previous step. "
                f"Expected: {executor.expected_input_type()}, "
                f"Got: {type(input_data.data[next(iter(input_data.data))]).__name__}"
            )

        return executor.execute(step_config, input_data)
```

### 4. Empty Results After Filter

**Scenario:** Filter step eliminates all data.

**Handling:**
```python
class FilterExecutor:
    def execute(self, config, input_data):
        filtered = self.apply_filter(input_data, config)

        if filtered.total_items == 0:
            logger.warning(f"Filter eliminated all data: {config}")
            # Option 1: Raise error
            raise EmptyDataError("Filter resulted in empty dataset")

            # Option 2: Return empty container with warning
            filtered.metadata["warnings"].append({
                "type": "empty_result",
                "message": "Filter eliminated all items",
                "filter": config
            })

        return filtered
```

### 5. Partial Execution & Resume

**Scenario:** Workflow fails mid-execution. User wants to resume.

**Handling:**
```python
class WorkflowEngine:
    def execute_workflow(self, workflow_id, workflow_run_id, resume=False):
        if resume:
            state = WorkflowState.load(workflow_run_id, self.db)
            start_index = state.current_step_index
            current_data = state.step_outputs[state.last_successful_step]
        else:
            state = WorkflowState.create(workflow_id, workflow_run_id)
            start_index = 0
            current_data = None

        workflow = self.load_workflow(workflow_id)

        for i in range(start_index, len(workflow["steps"])):
            step = workflow["steps"][i]
            state.current_step_index = i
            state.status = "running"
            state.save(self.db)

            try:
                output = self.execute_step(step, current_data)
                state.step_outputs[step["step_id"]] = output
                state.last_successful_step = step["step_id"]
                current_data = output
            except Exception as e:
                state.status = "failed"
                state.errors.append({
                    "step_id": step["step_id"],
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                state.save(self.db)
                raise WorkflowExecutionError(f"Failed at step {i}: {step['step_id']}") from e

        state.status = "completed"
        state.completed_at = datetime.now()
        state.save(self.db)
        return state
```

## Caching Integration

### 1. Analysis Result Caching

**Strategy:** Reuse existing analyses when possible.

```python
class FundamentalAnalysisExecutor:
    def run_analysis(self, ticker, year, filing_type, custom_prompt):
        # Check if analysis already exists
        existing = self.db.search_analyses(
            ticker=ticker,
            analysis_type="fundamental",
            filing_type=filing_type,
            status="completed"
        )

        # Filter by year
        for analysis in existing:
            years_analyzed = json.loads(analysis["years_analyzed"])
            if year in years_analyzed:
                # Reuse existing result
                logger.info(f"Cache hit: {ticker} {year} fundamental")
                results = self.db.get_results_by_run(analysis["run_id"])
                for result in results:
                    if result["fiscal_year"] == year:
                        return json.loads(result["result_json"])

        # No cache hit, run new analysis
        logger.info(f"Cache miss: {ticker} {year} fundamental")
        run_id = self.analysis_service.run_analysis(
            ticker=ticker,
            analysis_type="fundamental",
            filing_type=filing_type,
            years=[year],
            custom_prompt=custom_prompt
        )

        # Wait for completion (or poll)
        result = self.wait_for_analysis(run_id, timeout=300)
        return result
```

### 2. Filing Caching

**Strategy:** Use existing file_cache table.

```python
class InputStepExecutor:
    def fetch_filing(self, ticker, year, filing_type):
        # Check file cache
        cached_file = self.db.get_cached_file(ticker, year, filing_type)

        if cached_file and Path(cached_file["file_path"]).exists():
            logger.info(f"File cache hit: {ticker} {year} {filing_type}")
            return cached_file["file_path"]

        # Download and cache
        logger.info(f"File cache miss: {ticker} {year} {filing_type}")
        file_path = self.downloader.download(ticker, year, filing_type)

        # Save to cache
        self.db.save_cached_file(
            ticker=ticker,
            fiscal_year=year,
            filing_type=filing_type,
            file_path=file_path
        )

        return file_path
```

### 3. Workflow Result Caching

**Strategy:** Save intermediate step outputs for resume capability.

```python
class WorkflowState:
    def save_step_output(self, step_id, output: DataContainer):
        """Save step output to database for resume."""
        # Serialize DataContainer to JSON
        output_json = json.dumps({
            "data": output.data,  # May need custom serialization for Pydantic models
            "shape": output.shape,
            "metadata": output.metadata
        }, cls=PydanticEncoder)

        # Save to workflow_step_outputs table
        self.db.execute("""
            INSERT INTO workflow_step_outputs (
                workflow_run_id, step_id, output_json, created_at
            ) VALUES (?, ?, ?, ?)
        """, (self.workflow_run_id, step_id, output_json, datetime.now()))
```

## Database Schema Extensions

### New Tables

```sql
-- Workflow definitions (already in WORKFLOW_DESIGN.md)
CREATE TABLE workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    workflow_json TEXT NOT NULL,  -- Full workflow definition
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workflow execution runs
CREATE TABLE workflow_runs (
    id TEXT PRIMARY KEY,  -- UUID
    workflow_id INTEGER NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed, paused
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

    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Step outputs (for resume capability)
CREATE TABLE workflow_step_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    output_json TEXT NOT NULL,  -- Serialized DataContainer
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id),
    UNIQUE(workflow_run_id, step_id)
);

-- Step execution logs
CREATE TABLE workflow_step_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    log_level TEXT NOT NULL,  -- INFO, WARNING, ERROR
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (workflow_run_id) REFERENCES workflow_runs(id)
);
```

## Performance Considerations

### 1. Parallel Execution

For independent items (e.g., analyzing multiple companies), use parallel execution:

```python
class FundamentalAnalysisExecutor:
    def execute(self, config, input_data):
        # Collect all (ticker, year) pairs
        tasks = []
        for ticker, years in input_data.data.items():
            for year, doc in years.items():
                if doc is not None:
                    tasks.append((ticker, year, doc))

        # Run in parallel with thread pool
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.run_analysis, ticker, year, doc): (ticker, year)
                for ticker, year, doc in tasks
            }

            results = {}
            for future in as_completed(futures):
                ticker, year = futures[future]
                try:
                    result = future.result()
                    if ticker not in results:
                        results[ticker] = {}
                    results[ticker][year] = result
                except Exception as e:
                    logger.error(f"Failed: {ticker} {year}: {e}")

        return DataContainer(data=results, ...)
```

### 2. Rate Limit Management

Use API key rotation (already implemented in AnalysisService):

```python
class FundamentalAnalysisExecutor:
    def __init__(self, analysis_service: AnalysisService):
        self.analysis_service = analysis_service
        # analysis_service already has key rotation logic
```

### 3. Memory Management

For large workflows, don't keep all intermediate results in memory:

```python
class WorkflowEngine:
    def execute_workflow(self, workflow_id, workflow_run_id, keep_intermediates=False):
        # ...

        for step in workflow["steps"]:
            output = self.execute_step(step, current_data)

            # Save to database
            state.save_step_output(step["step_id"], output)

            # Only keep in memory if needed
            if keep_intermediates or step == workflow["steps"][-1]:
                state.step_outputs[step["step_id"]] = output

            current_data = output
```

## API Surface

### 1. Main Entry Point

```python
# In fintel/ui/services/workflow_service.py

class WorkflowService:
    """Service for workflow execution."""

    def __init__(self, db: DatabaseRepository, analysis_service: AnalysisService):
        self.db = db
        self.engine = WorkflowEngine(db, analysis_service)

    def execute_workflow(
        self,
        workflow_id: int,
        resume: bool = False,
        workflow_run_id: Optional[str] = None
    ) -> str:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of workflow to execute
            resume: Resume from previous failed run
            workflow_run_id: Required if resume=True

        Returns:
            workflow_run_id: ID of this execution run
        """
        if resume and not workflow_run_id:
            raise ValueError("workflow_run_id required for resume")

        if not resume:
            workflow_run_id = str(uuid.uuid4())

        self.engine.execute_workflow(workflow_id, workflow_run_id, resume=resume)
        return workflow_run_id

    def get_run_status(self, workflow_run_id: str) -> Dict:
        """Get status of a workflow run."""
        state = WorkflowState.load(workflow_run_id, self.db)
        return {
            "status": state.status,
            "current_step": state.current_step_index,
            "total_steps": state.total_steps,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
            "errors": state.errors
        }

    def get_run_results(self, workflow_run_id: str) -> DataContainer:
        """Get final results of completed workflow run."""
        state = WorkflowState.load(workflow_run_id, self.db)

        if state.status != "completed":
            raise ValueError(f"Workflow not completed: {state.status}")

        # Get last step output
        last_step = state.last_successful_step
        return state.step_outputs[last_step]
```

### 2. Streamlit Integration

```python
# In pages/8_🔗_Workflow_Builder.py

# Add "Run Workflow" button
if st.button("▶️ Run Workflow"):
    # Start execution in background
    workflow_run_id = workflow_service.execute_workflow(
        workflow_id=selected_workflow_id
    )

    st.session_state.monitoring_run_id = workflow_run_id
    st.success(f"Started workflow run: {workflow_run_id}")
    st.rerun()

# Show progress
if 'monitoring_run_id' in st.session_state:
    run_id = st.session_state.monitoring_run_id
    status = workflow_service.get_run_status(run_id)

    st.progress(status["current_step"] / status["total_steps"])
    st.write(f"Step {status['current_step']}/{status['total_steps']}")

    if status["status"] == "completed":
        st.success("Workflow completed!")
        results = workflow_service.get_run_results(run_id)
        # Display results
```

## Testing Strategy

### 1. Unit Tests

Test each executor independently:

```python
def test_input_executor():
    executor = InputStepExecutor(db, analysis_service)

    config = {
        "tickers": ["AAPL", "MSFT"],
        "num_years": 2,
        "filing_type": "10-K"
    }

    output = executor.execute(config, None)

    assert output.shape == (2, 2)
    assert "AAPL" in output.data
    assert "MSFT" in output.data

def test_aggregate_by_company():
    executor = AggregateExecutor(db)

    # Mock input with (3, 4) shape
    input_data = create_mock_container(
        tickers=["A", "B", "C"],
        years=[2024, 2023, 2022, 2021]
    )

    config = {"operation": "group_by_company"}
    output = executor.execute(config, input_data)

    assert output.shape == (3, 1)
```

### 2. Integration Tests

Test full workflow execution:

```python
def test_full_workflow_execution():
    # Create test workflow
    workflow_json = {...}
    workflow_id = db.save_workflow("Test Workflow", workflow_json)

    # Execute
    service = WorkflowService(db, analysis_service)
    run_id = service.execute_workflow(workflow_id)

    # Check status
    status = service.get_run_status(run_id)
    assert status["status"] == "completed"

    # Get results
    results = service.get_run_results(run_id)
    assert results.shape == (1, 1)  # Final aggregated result
```

### 3. Error Handling Tests

```python
def test_missing_filing_handling():
    # Create workflow with non-existent filing
    config = {"tickers": ["FAKE"], "years": [2024], "filing_type": "10-K"}

    executor = InputStepExecutor(db, analysis_service)
    output = executor.execute(config, None)

    # Should have None for missing filing
    assert output.data["FAKE"][2024] is None
    assert len(output.metadata["missing_filings"]) == 1

def test_resume_after_failure():
    # Start workflow that will fail mid-way
    run_id = service.execute_workflow(workflow_id_with_error)

    # Should fail at step 3
    status = service.get_run_status(run_id)
    assert status["status"] == "failed"
    assert status["current_step"] == 3

    # Fix the error, then resume
    run_id = service.execute_workflow(workflow_id, resume=True, workflow_run_id=run_id)

    # Should complete
    status = service.get_run_status(run_id)
    assert status["status"] == "completed"
```

## Implementation Phases

### Phase 1: Core Engine (Week 1)
- [ ] Implement DataContainer
- [ ] Implement WorkflowState
- [ ] Implement WorkflowEngine (basic)
- [ ] Implement InputStepExecutor
- [ ] Database schema migrations
- [ ] Basic tests

### Phase 2: Analysis Executors (Week 2)
- [ ] Implement FundamentalAnalysisExecutor
- [ ] Implement SuccessFactorsExecutor
- [ ] Implement PerspectiveAnalysisExecutor
- [ ] Caching integration
- [ ] Error handling
- [ ] Tests

### Phase 3: Aggregation & Filters (Week 3)
- [ ] Implement AggregateExecutor
- [ ] Implement FilterExecutor
- [ ] Implement CustomPromptExecutor
- [ ] Shape transformations
- [ ] Tests

### Phase 4: Export & Polish (Week 4)
- [ ] Implement ExportExecutor
- [ ] Resume capability
- [ ] Progress tracking
- [ ] UI integration
- [ ] End-to-end tests

### Phase 5: Optimization (Week 5)
- [ ] Parallel execution
- [ ] Memory optimization
- [ ] Performance profiling
- [ ] Documentation

## Open Questions

1. **Pydantic Model Serialization:** How to serialize complex Pydantic models (TenKAnalysis, etc.) to JSON for storage?
   - **Answer:** Use `model.model_dump()` for serialization, `ModelClass.model_validate()` for deserialization

2. **Async vs Sync:** Should we use async/await for I/O operations?
   - **Answer:** Start with sync (threading), migrate to async if needed

3. **Progress Callbacks:** How to report progress to UI in real-time?
   - **Answer:** Streamlit polling with st.rerun(), check status every N seconds

4. **Workflow Versioning:** What if user edits workflow while it's running?
   - **Answer:** Store full workflow JSON in workflow_runs, execution uses snapshot

5. **Resource Limits:** Max workflow size, timeout limits?
   - **Answer:** Configure via settings:
     - Max steps: 20
     - Max total analyses: 100
     - Timeout per step: 1 hour
     - Total workflow timeout: 24 hours

## Next Steps

1. **Review this design document** - Ensure all edge cases covered
2. **Create database migrations** - Add new tables
3. **Implement Phase 1** - Core engine components
4. **Write comprehensive tests** - TDD approach
5. **UI mockups** - Design workflow execution monitoring page
