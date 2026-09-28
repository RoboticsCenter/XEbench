# Todo 1 — Wuji Glove human demonstration data

Todo 1 is a data-collection track, not a scored benchmark task: it has no robot embodiment to evaluate. The operating specification calls for five task types with one or two successful demonstration episodes each.

## Reference sensors

- Wuji Glove with 526 tactile points (24 × 31 array, 0–20 N range, 0.1 N resolution, 4 mm spacing), five EMF modules (6-DoF each), and a 6-axis IMU at 800 Hz.
- VIVE Ultimate Tracker strapped to the operator's wrist as the global 6-DoF pose source.
- D435 overhead at about 45 degrees, covering the work surface; D405 mounted on the wrist.
- Keep the D435 fixed through a session. Use the D405 `image_rect_raw` stream. Record camera serials and calibration.

## Frames and alignment

Keep the tracker world frame, glove wrist frame (`r_wrist`), and EMF transmitter frame (`r_hand_emf_tx`) explicit. Measure tracker-to-glove-wrist and camera-to-world transforms per session, and save them under `calib_id`. Before recording, project the tracked wrist into the D435 image and confirm it lands on the hand.

Record every channel on the same monotonic clock at its native rate without record-time resampling. Store one MCAP per episode, with alignment `index` and `time_diff_ms` records to the D435 reference timeline. Keep only successful episodes in the data export (`run_type=dataset`). Record task text, objects, channel units/rates, calibration, sync method/residual, hardware serials, and frame definitions.

This page intentionally describes the released data interface and measured setup only; workstation-specific tracker map construction is not part of the public data contract.
