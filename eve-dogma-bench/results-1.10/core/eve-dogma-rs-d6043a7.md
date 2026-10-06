# Scorecard: eve-dogma-rs-d6043a7

- command: `/workspace/exct-eve/fj-compare/rs/target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz calc`, batch: `/workspace/exct-eve/fj-compare/rs/target/release/eve-dogma --dataset /workspace/exct-eve/data/dataset-3569502.json.gz batch`
- cases fully correct: **325/339**
- values correct: **22499/22513** (99.94 %)
- engine errors: 0

| group | ok | total | % |
|---|---|---|---|
| application | 4030 | 4030 | 100.0 |
| capacitor | 1198 | 1198 | 100.0 |
| defense | 6100 | 6100 | 100.0 |
| fitting | 3051 | 3051 | 100.0 |
| navigation | 2022 | 2032 | 99.5 |
| offense | 2032 | 2034 | 99.9 |
| tank | 2373 | 2373 | 100.0 |
| targeting | 1693 | 1695 | 99.9 |

| perf | value |
|---|---|
| one process per case, median ms (cold start + calc) | 8.1 |
| batch throughput (corpus x5) fits/s | 5338 |
| latency one fit (exct_rifter) ms/calc | 0.128 |
| startup + one calc ms | 9.2 |
| deterministic | True |

Worst metrics:

- warp_scramble_status: 330/339
- drone_dps: 337/339
- scan_resolution: 337/339
- max_velocity: 337/338
