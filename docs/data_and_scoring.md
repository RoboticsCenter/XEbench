# Data, clocks, and scoring

DexBench separates data capture from benchmark evaluation. A `dataset` export keeps successful demonstrations. A `benchmark` run keeps every trial, including failed and invalid trials. MCAP is one file per trial, with sensor and command channels preserved at their native rates. JSON run summaries collect per-policy outcomes and point to trial recordings.

All recorded channels share a monotonic clock. Arrival time is not necessarily measurement time: camera transport, USB devices, and MIDI adapters can add delay. For each session, perform a visible/contact event on at least two channels, repeat it about ten times, and record the median fixed offset and residual spread. In metadata, define each channel's mapping to the D435 reference timeline using sample `index` and measured `time_diff_ms`. Report alignment error as a metric; do not silently shift/resample raw data while recording.

Keep hardware serials/models, calibration IDs, frame names, camera intrinsics/extrinsics, tracker transforms when used, sync method/residual, task/object setup, and run type with each session. Session examples are in [hardware/session.template.json](../hardware/session.template.json).

Task scorers consume only recorded events and their timestamps. Keyboard and MIDI event scorers use hardware key/note events. The pick-and-place scorer consumes calibrated tray state plus hand-open feedback. Keep enough raw evidence to re-run a scorer if its implementation changes.
