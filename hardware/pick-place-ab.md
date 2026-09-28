# `pick-place-ab` setup

Use the center of the YAM base as the origin. The x-axis points forward, the y-axis points left, and measurements are in centimeters.

| Item | Setup |
| --- | --- |
| Zone A | Center `(35, +15)`; taped 10 × 10 cm square with an arrow marking object orientation |
| Zone B tray | Center `(35, -15)`; inside about 25 × 18 cm, walls 3 cm high; fix it with double-sided tape and choose a color that contrasts with the objects |
| Home pose | Open hand, palm down, 25 cm above `(35, 0)`; teach this pose once, save the joint angles, and call the saved pose from the run script |
| D435 | 60 cm in front of workspace center `(35, 0)` and 60 cm above the table; aim down at 45 degrees so the view includes zone A, the tray, and the hand |
| D405 | Mount on the robot wrist and aim at the grasp area |

If the hand cannot reach, shift the whole layout 5 cm toward the base and record the new coordinates.

## Objects

Keep each object's orientation fixed at the zone A arrow. Record the brand and measured dimensions of the objects used.

| Object | Grasp | Reference setup |
| --- | --- | --- |
| Standard tennis ball | Whole-hand grasp | About 6.7 cm diameter |
| Standard 3×3 Rubik's cube | Whole-hand grasp | About 5.7 cm and 100 g; grasp flat and place it so it sits stably in the tray |
| Thick capped whiteboard marker | Fingertip pinch | Place flat in zone A along the arrow; use a thick marker so the depth camera can detect it |

## Tracker and scorer setup

- Place the tracker on a fixed mark on the YAM base. Record the tracker-world-to-YAM-base and tracker-to-wrist transforms in the session calibration.
- Name the Vive map `map_YYYYMMDD_vN`. Keep its ID while the map is unchanged; assign a new ID after rebuilding the map. Do not rebuild the map during a benchmark round.
- Calibrate the tray scorer with one empty-tray reading and one reading for each of the three objects in the tray. Set the threshold to half the weakest signal.
- Score the tray with D435 depth. If the marker's depth signal is too weak, add color differencing and use a tray color that contrasts with the marker.

See the [`pick-place-ab` protocol](../SPEC.md#pick-place-ab) for trial and scoring rules.
