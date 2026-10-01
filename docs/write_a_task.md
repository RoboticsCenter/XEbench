# Add a task

1. Give the task a stable kebab-case ID and a fixed start state.
2. Write success, failure, invalid-trial, timeout, reset, and trial-count rules before collecting results.
3. Prefer a hardware event or calibrated sensor as the scorer. Store scorer inputs on named MCAP topics so a run can be rescored offline.
4. Implement a deterministic scorer from `list[Event]` and `t0_ns` in `src/xebench/tasks.py`.
5. Add the public task definition and hardware/session fields to `SPEC.md` and `hardware/`.
6. Include a scripted or simulator example only when it is clearly labeled as a software-path demonstration. Never publish it as a hardware baseline.

Keep native timestamps and raw scorer evidence. A task definition must not change after baseline results are seen; if a scoring bug is found, version the task protocol and rescore all comparable runs.
