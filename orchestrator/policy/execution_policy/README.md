# Execution Policy

### Task Cancellation from Execution
When a `cancel` intent is received inside Execution, the `route_to_domain()` function is called. Inside that function the current session information that is no longer needed is deleted, e.g. task_selection, taskmap, and state, and the task phase is set to `DOMAIN`.

### Starting a new Search from Execution
Similarly to Task Cancellation, when a `search` intent is received inside Execution, the `route_to_domain()` function is called. The intent is then 'consumed', meaning it is deleted from the user intents list. Then the redundant session information is deleted and the task phase is set to `DOMAIN`.
