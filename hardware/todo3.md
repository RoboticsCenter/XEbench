# Todo 3 — YAM arm and Wuji Hand 2 pick-and-place

## Reference geometry

Use the center of the YAM base as the origin; x points forward, y points left, and distances are in centimeters.

| Item | Reference definition |
| --- | --- |
| Zone A | Center `(35, +15)`; taped 10 × 10 cm square with an arrow for object orientation |
| Zone B tray | Center `(35, -15)`; inside about 25 × 18 cm; 3 cm walls; fixed with double-sided tape; strong color contrast to objects |
| Wood strip | 20 × 2 × 1 cm, fixed at the back edge of zone A for thin objects to lean against |
| Home pose | Open hand, palm down, 25 cm above `(35, 0)`; save measured joint angles |
| D435 | 60 cm horizontally in front of workspace center `(35, 0)`, 60 cm above table, pitched down 45 degrees, viewing zone A, tray, and hand |
| D405 | Mounted on robot wrist, looking at the grasp region |

If the hand cannot reach, shift the full layout 5 cm toward the base and record the resulting coordinates.

## Object set

Record the brand/model and measured dimensions for each physical object. Keep object orientation fixed at the zone A marker.

| Grasp type | Object 1 | Object 2 |
| --- | --- | --- |
| Power grasp | Tennis ball | Unopened 355 ml (12 oz) can, upright |
| Precision pinch | 2.5 cm wooden cube | Whiteboard marker, lying flat and aligned with the arrow |
| Lateral pinch | Credit-card-sized plastic card, leaning on strip | Key, leaning on strip |

## Calibration and event channels

At each session, record the tracker world → YAM base transform and tracker → wrist transform in `calib_id`. Name the Vive map `map_YYYYMMDD_vN`; a rebuilt map gets a new ID. Never span a map rebuild within one benchmark round.

Record `/arm/command`, `/arm/state`, `/hand/command`, `/hand/state`, `/hand/tactile`, glove channels, camera streams, and `/scorer/tray_state`. Store end-effector poses in both world and base frames if the adapter provides them. Before official runs, calibrate tray thresholds against the empty tray and each object, and spot-check automatic scores against human judgments.
