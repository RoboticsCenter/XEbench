# Publish a result

The Dexterity leaderboard accepts complete, non-mock XEbench runs. Upload the `results.json` file written by `xebench run`, provide the hardware and policy metadata below, and link public MCAP trial recordings in DexData. The public site validates the fixed protocol and recalculates the score from the per-trial outcomes.

## Submit on the website

1. Finish the complete task protocol with a real adapter. The standard counts are 20 trials for `keypress-ldr`, 20 for `piano-seq`, and 30 for `pick-place-ab`.
2. Upload each trial MCAP to [DexData](https://dexdata.roboticscenter.ai) and create a public viewer link covering the run's recordings.
3. Open the [Dexterity benchmark page](https://dexterity.roboticscenter.ai/benchmark), select the matching task, and upload that run's `results.json`.
4. Enter the hand manufacturer and model, the arm manufacturer and model when used (required for `pick-place-ab`), and policy type and name. LLM results must include provider and model.
5. Add the MCAP viewer URL and, optionally, a public URL for `results.json`. Choose a public display name or organization if desired.
6. Consent to publish the result. Contact email is optional and is kept private. To be contacted about a possible future purchase discount for a top-ranked contribution, provide an email and opt in.

The leaderboard reports success rate and mean completion time. Keyboard runs also report key sequence accuracy; piano runs report note accuracy and medium-velocity hit rate; pick-and-place runs report success counts for the ball, cube, and marker. These task-specific scores are calculated from the per-trial events and are not directly comparable across tasks. Published rows are community-reported and are not labeled as independently verified.

## Submission format

The website accepts the `dexbench.submission.v1` JSON envelope defined by [submission.schema.json](submission.schema.json). The form builds this envelope from `results.json` and the fields above. Its top-level fields are:

| Field | Required values |
| --- | --- |
| `schema_version` | `dexbench.submission.v1` |
| `benchmark` | `task_id`, `protocol_version`, and `custom_task` (`null` for the three standard tasks) |
| `run` | Scoring fields copied from `results.json`: task, mock status, protocol count/completeness, and each trial's `success`, `invalid`, and task metrics (`key_events`, `notes`/`velocities`, or pick-and-place `object_id`) plus optional completion time |
| `hardware` | `hand.manufacturer`, `hand.model`, and `arm` (`null` if not used) |
| `policy` | `type`, `name`, `provider`, `model`, and `version`; provider and model are required for `llm` |
| `artifacts` | Public DexData `mcap_viewer_url`; optional HTTPS `results_json_url` |
| `contributor` | Optional public display name and organization; contact email and explicit incentive opt-in are private |
| `publish` | Must be `true` to enter the public leaderboard |

For custom tasks, set the benchmark task ID in both `benchmark.task_id` and `run.task`, and supply the task name, protocol version, complete trial count, and HTTPS protocol/specification link in `benchmark.custom_task`. Custom results rank only against the same task ID and protocol version.

The site rejects mock runs, partial protocols, mismatched task IDs or trial counts, malformed trial outcomes, and runs with no valid trials. Success rate is recomputed as successful valid trials divided by valid trials; hardware-invalid trials stay in the uploaded record but are excluded from the denominator. Key and note accuracy compare events with the expected sequence positions; any extra events count as errors. Piano medium-velocity hit rate counts observed notes with MIDI velocity 50–90. Pick-and-place results report valid successes and valid trials for each object. Mean completion time is calculated from valid trials that report a completion time and breaks success-rate ties.

The form reads the complete `results.json` locally, then sends only the scoring fields to the submission service. Calibration IDs, session metadata, endpoint URLs, and local file paths are stripped before upload. The leaderboard stores aggregate scores and public metadata, not the trial records. The public MCAP viewer link and optional public JSON link are displayed to help readers inspect the result; make sure an optional JSON link contains only information you intend to publish.

Top-ranked contributors may receive a discount on a future Robotics Center purchase. The amount and eligibility details are provided directly to eligible contributors; submitting a result does not guarantee a discount.
