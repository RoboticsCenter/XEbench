# Todo 2 — fixed hand and keyboard/MIDI rig

## Reference hardware

- Wuji Hand 2, 20 active DoF, firmware v1.2.1 or later, mounted upright on a fixed table mount.
- Each of index, middle, and ring fingertips is centered over its assigned key within 2 mm. Rest pose is 1 cm above the key surface with no key pressed.
- For `keypress-ldr`, use a dedicated USB keyboard read by evdev. Clamp or tape it so it cannot move. Index → LEFT, middle → DOWN, ring → RIGHT.
- For `piano-seq-3` and `piano-seq-dyn`, use a standard velocity-sensitive MIDI keyboard (white key about 2.3 cm wide). Index → C4/60, middle → D4/62, ring → E4/64. Strike about 3 cm behind the front edge. Record the keyboard model and velocity-curve setting.
- D435 reference placement: 40 cm horizontally in front of the keyboard, 40 cm above the table, pitched down 45 degrees and aimed at the middle key. A D405 may be added close to the keys.

## Channels

Record `/keyboard/events` or `/midi/events`, `/hand/command`, `/hand/state`, `/hand/tactile`, cameras, and all available glove channels during teleoperation. Keep command and achieved state separate. Capture MIDI note-on, velocity, note-off, and source timestamps.

## Session measurements to fill

Record the hand and keyboard models/serials, firmware, mount and key positions, fingertip alignment errors, camera serials and intrinsics/extrinsics, lighting, background, keyboard velocity curve, calibration ID, clock offsets/residuals, task, operator, and setup photos. The reference dimensions are not a substitute for rig measurements.
