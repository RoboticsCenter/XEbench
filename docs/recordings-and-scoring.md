# Benchmark recordings and scoring

Each benchmark trial is recorded in one MCAP file. Each policy/task run writes one `results.json` summary that links to the trial files. Keep success, failure, and invalid trials. Mark hardware faults invalid and include the reason.

## Clock alignment

Use a shared monotonic clock for event timestamps. Before a session, trigger a visible or physical contact event on at least two channels about ten times. Record the measured channel offsets and residual spread in the session metadata. Keep the original sensor timestamps and report alignment error instead of shifting or resampling recorded data.

## Session metadata

Record installed hardware models and serials, calibration IDs, coordinate frames, camera calibration, task and object setup, clock-sync method and residuals. Start from the [session metadata template](../hardware/session.template.json) and use the setup guide linked from the task table in the README.

## Scoring

Scorers use event timestamps from the MCAP files. `keypress-ldr` uses USB key events; `piano-seq` uses MIDI note and velocity events; `pick-place-ab` uses the calibrated tray-state scorer and hand-open feedback. Store the scorer inputs so a run can be rescored from its recordings.
