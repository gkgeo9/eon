# Fintel Session State Schema

This document describes all session state variables used across the Fintel Streamlit application.

## Global Session State

These variables are shared across all pages:

### `db` (DatabaseRepository)
- **Type**: `DatabaseRepository`
- **Initialized**: `fintel/ui/session.py::init_session_state()`
- **Purpose**: Shared database connection for all pages
- **Lifecycle**: Persists for entire session

### `page_initialized` (dict)
- **Type**: `dict[str, bool]`
- **Initialized**: `fintel/ui/session.py::init_session_state()`
- **Purpose**: Tracks which pages have been initialized
- **Lifecycle**: Persists for entire session

---

## Page-Specific Session State

### Settings Page (`pages/5_⚙️_Settings.py`)

- **`show_prompt_editor`** (bool): Whether prompt editor modal is visible
- **`edit_prompt_id`** (int|None): ID of prompt being edited, None if creating new
- **`confirm_clear_cache`** (bool): Confirmation flag for cache clearing

### Workflow Builder (`pages/8_🔗_Workflow_Builder.py`)

- **`workflow_steps`** (list): List of workflow step definitions
- **`workflow_name`** (str): Name of current workflow
- **`workflow_description`** (str): Description of current workflow
- **`monitoring_run_id`** (str|None): Run ID being monitored during execution
- **`current_workflow_id`** (str|None): ID of currently loaded workflow
- **`last_refresh`** (float): Timestamp of last auto-refresh for workflow monitoring

### Single Analysis Page (`pages/1_📊_Single_Analysis.py`)

- **`analysis_running`** (bool): Whether analysis is in progress
- **`current_run_id`** (str|None): ID of current analysis run

### Batch Analysis Page (`pages/2_📦_Batch_Analysis.py`)

- **`batch_run_ids`** (list): List of run IDs for batch operations
- **`batch_running`** (bool): Whether batch analysis is in progress

### Results Pages

- **`view_run_id`** (str|None): Run ID to view in Results Viewer
- **`selected_year`** (int|None): Selected year for multi-year analysis results

---

## Adding New State Variables

When adding new session state variables:

1. **Document them in this file** under the appropriate section
2. **Initialize them in `init_page_state()`** if page-specific
3. **Use descriptive names** with page prefix if needed (e.g., `workflow_steps` not just `steps`)
4. **Clean up state when no longer needed** to avoid memory leaks
5. **Consider using `get_or_create()`** from session.py for lazy initialization

## State Lifecycle

- **Session start**: All state is empty
- **Page navigation**: State persists across pages
- **Browser refresh**: All state is lost (Streamlit limitation)
- **Session timeout**: State is cleared after inactivity
- **Explicit clear**: Use `clear_page_state(page_name)` to clear page-specific state

## Best Practices

1. **Avoid large objects** in session state (use database instead)
2. **Use lazy initialization** with `get_or_create()` when possible
3. **Namespace page-specific variables** with page prefix
4. **Document default values** for all state variables
5. **Clean up** temporary state after operations complete

## Example Usage

```python
from fintel.ui.session import init_session_state, init_page_state, get_or_create

# At top of page
db = init_session_state()

# Initialize page-specific state
init_page_state("my_page", {
    "selected_option": "default",
    "is_expanded": False
})

# Lazy initialization
counter = get_or_create("page_visits", 0)
st.session_state.page_visits += 1
```

---

Last updated: 2025-12-12
