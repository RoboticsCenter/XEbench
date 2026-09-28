# `keypress-ldr` example recordings

These two MCAP files contain real recorded camera, hand, glove, and keyboard streams:

| Recording | Label in the source run | File |
| --- | --- | --- |
| Episode 4 | Success | [`episode_4_success.mcap`](episode_4_success.mcap) |
| Episode 5 | Failure | [`episode_5_failure.mcap`](episode_5_failure.mcap) |

The source application logged GUI key press and release callbacks. Operating-system key repeat can generate repeated press records while a key is held, so the raw press count is not necessarily the number of physical presses. These recordings are examples for inspecting event streams; their source labels are not DexBench scores.

The example MCAP metadata has been cleaned of machine addresses and device serial numbers. Browse MCAP recordings with [DexData](https://dexdata.roboticscenter.ai). See the [keypress-ldr protocol](../../SPEC.md#keypress-ldr) for the canonical event contract.
