"""Synthetic load generator for the M11-instrumented `api`.

Ramps concurrent requests across a sequence of load levels, captures per-level
latency samples, and queries `/metrics` for error counts. Writes a structured
results JSON consumable by `report_writer.py`.

Honors Track — TODO implementations required. See README.md for the contract.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Iterable
import httpx


@dataclass
class LoadLevelResult:
    """Per-load-level summary of one ramp step."""

    load_level: int
    requests_attempted: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_rate: float


def percentile(samples: list[float], q: float) -> float:
    """Return the q-th percentile (q in [0, 100]) of a samples list.

    Uses statistics.quantiles with method='inclusive' as the method.
    """
    if not samples:
        return 0.0
    if len(samples) == 1:
        return samples[0]
    # quantiles gives n=100, so index is q-1 (since 0-based)
    quants = statistics.quantiles(samples, n=100, method='inclusive')
    if q == 0:
        return min(samples)
    if q == 100:
        return max(samples)
    return quants[int(q)-1]


async def run_one_request(client, base_url: str) -> tuple[float, bool]:
    """Issue one request to `{base_url}/predict` and return (latency_ms, was_error).

    - Send a POST with a small JSON body (any payload your fixture/API accepts).
    - Measure wall-clock latency in milliseconds.
    - Return was_error = True for non-2xx responses or transport exceptions.
    """
    start = time.perf_counter()
    was_error = False
    try:
        response = await client.post(f"{base_url}/predict", json={})
        if response.status_code >= 400:
            was_error = True
    except Exception:
        was_error = True
    latency_ms = (time.perf_counter() - start) * 1000
    return latency_ms, was_error


async def run_level(
    base_url: str,
    concurrency: int,
    requests_per_level: int,
) -> LoadLevelResult:
    """Drive `requests_per_level` requests at `concurrency` in-flight.

    - Use an asyncio.Semaphore or similar to bound in-flight to `concurrency`.
    - Collect latency samples; count errors.
    - Aggregate via percentile() and return a LoadLevelResult.
    """
    semaphore = asyncio.Semaphore(concurrency)
    latencies = []
    errors = 0

    async def bounded_request(client):
        async with semaphore:
            latency, was_error = await run_one_request(client, base_url)
            latencies.append(latency)
            if was_error:
                nonlocal errors
                errors += 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [bounded_request(client) for _ in range(requests_per_level)]
        await asyncio.gather(*tasks)

    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    error_rate = errors / requests_per_level

    return LoadLevelResult(
        load_level=concurrency,
        requests_attempted=requests_per_level,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        error_rate=error_rate
    )


async def run_load_profile(
    base_url: str,
    load_levels: Iterable[int],
    requests_per_level: int,
) -> list[LoadLevelResult]:
    """Run each load level in sequence and return the aggregated results.

    - For each level in load_levels, call run_level and append the result.
    - Return the ordered list.
    """
    results = []
    for level in load_levels:
        result = await run_level(base_url, level, requests_per_level)
        results.append(result)
    return results


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="M11 Stretch-Tue load generator")
    p.add_argument("--base-url", required=True, help="Target API base URL")
    p.add_argument(
        "--load-levels",
        default="1,5,10,25,50",
        help="Comma-separated concurrency levels to ramp through",
    )
    p.add_argument("--requests-per-level", type=int, default=100)
    p.add_argument("--output", default="latency_results.json")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    levels = [int(x) for x in args.load_levels.split(",")]
    results = asyncio.run(
        run_load_profile(args.base_url, levels, args.requests_per_level)
    )
    with open(args.output, "w") as f:
        json.dump({"results": [asdict(r) for r in results]}, f, indent=2)
    print(f"Wrote {args.output} ({len(results)} levels)")


if __name__ == "__main__":
    main()
