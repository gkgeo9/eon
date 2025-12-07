# 🔗 Fintel Workflow System Design

## Vision

A flexible, composable analysis pipeline where you can:
1. Define inputs (companies, years, prompts)
2. Chain analysis steps together
3. Branch/merge analysis paths
4. Apply custom transformations
5. Save/reuse workflows

## Core Concept: Analysis Pipeline Builder

Instead of clicking "analyze" on one company with one config, you build a **multi-step workflow** like:

```
Step 1: [Input] → AAPL, MSFT, GOOGL + Years: 2020-2024
   ↓
Step 2: [Analyze] → Fundamental Analysis (per company, per year)
   ↓
Step 3: [Transform] → Combine multi-year results → Success Factors
   ↓
Step 4: [Analyze] → Apply custom prompt: "Compare these 3 companies' success factors and rank them"
   ↓
Step 5: [Export] → Generate comparison report
```

## Node Types

### 1. Input Nodes
- **Company List**: Define tickers (manual or CSV)
- **Year Range**: Define time period
- **Custom Prompt**: Define analysis prompt
- **Existing Analysis**: Load previous results as input

### 2. Analysis Nodes
- **Fundamental**: Analyze 10-K filings
- **Success Factors**: Multi-year pattern extraction
- **Perspective**: Apply Buffett/Taleb/Contrarian lens
- **Custom Prompt**: Apply user-defined prompt to any data
- **Comparative**: Compare multiple companies

### 3. Transform Nodes
- **Aggregate**: Combine results (e.g., all years for one company)
- **Filter**: Filter by criteria (e.g., only profitable years)
- **Map**: Apply function to each result
- **Reduce**: Summarize multiple results into one

### 4. Output Nodes
- **Export**: Save to file (JSON/CSV/Excel)
- **Visualize**: Generate charts
- **Report**: Create formatted report
- **Database**: Save to analysis_results table

## UI Design (Streamlit-Compatible)

Since we can't do drag-and-drop in Streamlit, we'll use a **step-by-step builder**:

### Workflow Builder Page Layout

```
┌─────────────────────────────────────────────────────────┐
│  🔗 Workflow Builder                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Workflow Name: [Compare Tech Giants____________]        │
│  Description: [Analyze and compare AAPL, MSFT, GOOGL]   │
│                                                          │
│  ┌──────────────────────────────────────┐              │
│  │ 📊 Workflow Visualization             │              │
│  │                                        │              │
│  │  Companies → Fundamental → Success    │              │
│  │  (3)         Analysis     Factors     │              │
│  │              (3x5=15)     (3)         │              │
│  │                 ↓                      │              │
│  │            Custom Prompt               │              │
│  │            "Compare & Rank"            │              │
│  │                 ↓                      │              │
│  │             Export                     │              │
│  └──────────────────────────────────────┘              │
│                                                          │
│  ┌─ Step 1: Input Companies ──────────────────────┐    │
│  │  Mode: ● Manual  ○ CSV  ○ Load from DB         │    │
│  │  Tickers: AAPL, MSFT, GOOGL                    │    │
│  │  Years: 2020-2024 (5 years)                    │    │
│  │  ✓ 3 companies × 5 years = 15 filings          │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ Step 2: Fundamental Analysis ────────────────┐     │
│  │  Analysis Type: Fundamental                    │     │
│  │  Run for: ● Each company-year ○ Aggregated    │     │
│  │  Output: 15 TenKAnalysis objects              │     │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ Step 3: Success Factors Extraction ─────────┐      │
│  │  Aggregate by: Company                         │      │
│  │  Analyzer: ● Objective ○ Excellent            │      │
│  │  Output: 3 SuccessFactors objects             │      │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ Step 4: Custom Comparative Analysis ────────┐      │
│  │  Input: Step 3 results (3 companies)          │      │
│  │  Prompt:                                       │      │
│  │  ┌──────────────────────────────────────────┐ │      │
│  │  │ Analyze these 3 companies' success       │ │      │
│  │  │ factors and:                             │ │      │
│  │  │ 1. Identify unique strengths of each    │ │      │
│  │  │ 2. Rank them by compounder potential    │ │      │
│  │  │ 3. Recommend which to invest in         │ │      │
│  │  └──────────────────────────────────────────┘ │      │
│  │  Output Schema: ComparisonReport              │      │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ Step 5: Export ────────────────────────────────┐   │
│  │  Format: ☑ JSON  ☑ CSV  ☑ Excel               │   │
│  │  Include: ☑ Raw data  ☑ Summary  ☑ Charts     │   │
│  │  Filename: tech_giants_comparison_2024         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [+ Add Step]  [💾 Save Workflow]  [▶️ Run Workflow]   │
│                                                          │
│  ═══════════════════════════════════════════════════    │
│  Saved Workflows                                        │
│  • Tech Giants Comparison (5 steps)                     │
│  • Portfolio Risk Analysis (7 steps)                    │
│  • Contrarian Scanner Pipeline (4 steps)                │
└─────────────────────────────────────────────────────────┘
```

## Step Configuration Details

### Step Type: Input
```python
{
    "type": "input",
    "config": {
        "companies": ["AAPL", "MSFT", "GOOGL"],
        "years": [2024, 2023, 2022, 2021, 2020],
        "filing_type": "10-K"
    },
    "output": {
        "type": "ticker_year_pairs",
        "count": 15  # 3 companies × 5 years
    }
}
```

### Step Type: Analysis
```python
{
    "type": "analysis",
    "analysis_type": "fundamental",
    "config": {
        "input_from": "step_1",
        "run_mode": "per_item",  # or "aggregated"
        "custom_prompt": None
    },
    "output": {
        "type": "TenKAnalysis",
        "count": 15
    }
}
```

### Step Type: Aggregate
```python
{
    "type": "aggregate",
    "config": {
        "input_from": "step_2",
        "group_by": "company",  # or "year", "none"
        "operation": "success_factors",
        "analyzer_type": "objective"
    },
    "output": {
        "type": "SuccessFactors",
        "count": 3  # One per company
    }
}
```

### Step Type: Custom Analysis
```python
{
    "type": "custom_analysis",
    "config": {
        "input_from": "step_3",
        "prompt": "Analyze these companies and rank them...",
        "output_schema": "ComparisonReport",
        "thinking_budget": 4096
    },
    "output": {
        "type": "ComparisonReport",
        "count": 1
    }
}
```

## Advanced Features

### 1. Branching
Split workflow into parallel paths:

```
Step 1: Input → AAPL
    ↓
Step 2: Fundamental Analysis
    ↓
[Branch]
    ↓                    ↓
Step 3a: Buffett    Step 3b: Taleb
    ↓                    ↓
    [Merge at Step 4]
         ↓
Step 4: Compare perspectives
```

### 2. Conditional Steps
Only run if condition met:

```
Step 3: Success Factors
    ↓
IF (success_score > 80):
    → Step 4: Deep Dive Analysis
ELSE:
    → Skip to Step 5
```

### 3. Loops
Run analysis for each company separately:

```
FOR EACH company IN [AAPL, MSFT, GOOGL]:
    Step A: Fundamental
    Step B: Success Factors
    Step C: Buffett Lens
    → Collect results
```

### 4. Templates
Pre-built workflow templates:

- **"Deep Dive Single Company"**: Full analysis of one company
- **"Compare Competitors"**: Side-by-side comparison
- **"Portfolio Risk Assessment"**: Aggregate risk across holdings
- **"Contrarian Scanner"**: Batch screen for hidden gems
- **"Time Series Analysis"**: Track metrics over time

## Implementation Plan

### Phase 1: Basic Linear Workflows
- Step-by-step builder UI
- 5 step types: Input, Analysis, Aggregate, Custom, Export
- Save/load workflows
- Run workflow sequentially

### Phase 2: Visualization
- Flowchart display using Graphviz/Mermaid
- Step status indicators (pending/running/completed)
- Progress tracking for entire workflow

### Phase 3: Advanced Features
- Branching/merging
- Conditional steps
- Loop support
- Parallel execution

### Phase 4: Library
- Template library
- Share workflows (export/import JSON)
- Community templates

## Data Model

### Workflow Schema
```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class WorkflowStep(BaseModel):
    step_id: str  # "step_1", "step_2", etc.
    step_type: str  # "input", "analysis", "aggregate", etc.
    name: str
    config: Dict[str, Any]
    depends_on: Optional[List[str]] = None  # ["step_1", "step_2"]
    output_type: str

class Workflow(BaseModel):
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: str
    updated_at: str

class WorkflowRun(BaseModel):
    run_id: str
    workflow_id: str
    status: str  # pending, running, completed, failed
    current_step: Optional[str]
    step_results: Dict[str, Any]  # {step_id: result}
    started_at: str
    completed_at: Optional[str]
```

### Database Tables
```sql
CREATE TABLE workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    workflow_json TEXT NOT NULL,  -- Full Workflow object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_step TEXT,
    results_json TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

CREATE TABLE workflow_step_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);
```

## Example Workflows

### Example 1: "Tech Giants Comparison"
```json
{
    "name": "Tech Giants Comparison",
    "description": "Compare AAPL, MSFT, GOOGL success factors",
    "steps": [
        {
            "step_id": "step_1",
            "step_type": "input",
            "name": "Define Companies",
            "config": {
                "companies": ["AAPL", "MSFT", "GOOGL"],
                "years": [2024, 2023, 2022, 2021, 2020]
            }
        },
        {
            "step_id": "step_2",
            "step_type": "analysis",
            "name": "Fundamental Analysis",
            "config": {
                "analysis_type": "fundamental",
                "depends_on": ["step_1"]
            }
        },
        {
            "step_id": "step_3",
            "step_type": "aggregate",
            "name": "Extract Success Factors",
            "config": {
                "operation": "success_factors",
                "analyzer_type": "objective",
                "depends_on": ["step_2"]
            }
        },
        {
            "step_id": "step_4",
            "step_type": "custom_analysis",
            "name": "Compare & Rank",
            "config": {
                "prompt": "Compare these companies and rank by investment potential",
                "depends_on": ["step_3"]
            }
        },
        {
            "step_id": "step_5",
            "step_type": "export",
            "name": "Export Results",
            "config": {
                "format": ["json", "csv", "excel"],
                "depends_on": ["step_4"]
            }
        }
    ]
}
```

### Example 2: "Deep Dive with Multiple Perspectives"
```json
{
    "name": "Deep Dive - Multiple Lenses",
    "description": "Analyze one company through all lenses",
    "steps": [
        {
            "step_id": "input",
            "step_type": "input",
            "config": {
                "companies": ["AAPL"],
                "years": [2024, 2023, 2022, 2021, 2020]
            }
        },
        {
            "step_id": "fundamental",
            "step_type": "analysis",
            "config": {
                "analysis_type": "fundamental",
                "depends_on": ["input"]
            }
        },
        {
            "step_id": "buffett",
            "step_type": "analysis",
            "config": {
                "analysis_type": "buffett",
                "depends_on": ["fundamental"]
            }
        },
        {
            "step_id": "taleb",
            "step_type": "analysis",
            "config": {
                "analysis_type": "taleb",
                "depends_on": ["fundamental"]
            }
        },
        {
            "step_id": "contrarian",
            "step_type": "analysis",
            "config": {
                "analysis_type": "contrarian",
                "depends_on": ["fundamental"]
            }
        },
        {
            "step_id": "synthesize",
            "step_type": "custom_analysis",
            "config": {
                "prompt": "Synthesize insights from all three perspectives",
                "depends_on": ["buffett", "taleb", "contrarian"]
            }
        }
    ]
}
```

## UI Workflow

1. **Create New Workflow**
   - Name it
   - Add description
   - Start with Step 1 (always Input)

2. **Add Steps**
   - Click "+ Add Step"
   - Select step type
   - Configure step (depends on type)
   - See preview of what will happen

3. **Visualize**
   - See flowchart of workflow
   - Understand data flow
   - Identify bottlenecks

4. **Save Workflow**
   - Save to database
   - Can load later
   - Can share (export JSON)

5. **Run Workflow**
   - Execute all steps in order
   - Track progress (step X of Y)
   - Handle errors (retry failed steps)
   - View results

6. **Review Results**
   - See output of each step
   - Export final results
   - Rerun if needed

## Why This is Powerful

1. **Flexibility**: Build any analysis pipeline
2. **Reusability**: Save workflows, use templates
3. **Scalability**: Run on 1 company or 100
4. **Customization**: Insert custom prompts anywhere
5. **Transparency**: See exactly what's happening
6. **Efficiency**: Run once, get all insights

## Next Steps

After implementing quick wins, we'll build:
1. Workflow builder page (basic linear workflows)
2. Workflow execution engine
3. Workflow visualization
4. Template library
5. Advanced features (branching, loops, conditions)
