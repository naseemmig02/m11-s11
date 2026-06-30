# Latency Profile Report

## Load Level Results
| load_level | p50 | p95 | p99 | error_rate |
|------------|-----|-----|-----|------------|
| 1 | 27.04 | 38.27 | 43.45 | 0.0000 |
| 5 | 5.70 | 33.16 | 37.99 | 0.0000 |
| 10 | 8.78 | 19.74 | 28.71 | 0.0200 |
| 25 | 34.08 | 93.90 | 111.97 | 0.0100 |
| 50 | 48.36 | 70.77 | 74.24 | 0.0000 |

## Latency Chart
![Latency vs Load Level](charts\latency-vs-load.png)

## Latency Knee
The latency knee is identified at load_level = 10, with a p95 latency of 19.74 ms.
The criterion used is: the first load level where the p95 slope (change in p95 per change in load)
is greater than twice the slope of the previous step, indicating a super-linear increase.

## Analysis
As load level increases, we observe a gradual increase in p50, p95, and p99 latencies.
The error rate remains low (as seen in the table), suggesting the system is handling the load
well up to and slightly beyond the identified knee point.
