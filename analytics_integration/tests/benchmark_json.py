"""
[Stage 2] Performance Benchmark Script for Analytics Integration JSON Parsing.
Measures standard json vs orjson decoding times and total endpoint overhead.
"""

import json
import sys
import time
import numpy as np

try:
    import orjson
except ImportError:
    print("Error: orjson package is not installed. Run 'pip install orjson'")
    sys.exit(1)


def generate_mock_iot_payload(num_readings: int) -> bytes:
    """Generates a realistic IoT payload string mimicking Flask request byte data."""
    payload = {
        "entity_id": "nab_realtraffic",
        "timestamp_col": "timestamp",
        "data": [
            {
                "timestamp": f"2026-09-12T10:{i % 60:02d}:00Z",
                "occupancy_t4013": round(float(val1), 4),
                "occupancy_6005": round(float(val2), 4),
            }
            for i, (val1, val2) in enumerate(
                zip(
                    np.random.normal(25.0, 2.0, num_readings),
                    np.random.normal(30.0, 3.0, num_readings),
                )
            )
        ],
        "model": {
            "detector": "isolationforest",
            "metric": "occupancy_t4013",
            "parameters": {},
        },
        "correlation": {
            "streams": ["occupancy_t4013", "occupancy_6005"],
            "window_size": 20,
            "step_size": 10,
            "method": "pearson",
        },
    }
    return json.dumps(payload).encode("utf-8")


def benchmark_parsing(byte_data: bytes, iterations: int = 200):
    # Benchmark standard json parsing
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = json.loads(byte_data.decode("utf-8"))
    std_time = (time.perf_counter() - t0) / iterations

    # Benchmark orjson parsing
    t0 = time.perf_counter()
    for _ in range(iterations):
        _ = orjson.loads(byte_data)
    orjson_time = (time.perf_counter() - t0) / iterations

    speedup = std_time / orjson_time if orjson_time > 0 else 0.0
    return std_time * 1000, orjson_time * 1000, speedup


def run_suite():
    payload_sizes = [100, 1000, 5000, 10000]
    print("\n" + "=" * 70)
    print("      AIntg JSON PARSING PERFORMANCE BENCHMARK (Stage 2)")
    print("=" * 70)
    print(
        f"{'Payload Size':<15} | {'Std json (ms)':<15} | {'orjson (ms)':<15} | {'Speedup Factor':<15}"
    )
    print("-" * 70)

    for size in payload_sizes:
        raw_bytes = generate_mock_iot_payload(size)
        std_ms, orjson_ms, factor = benchmark_parsing(raw_bytes)
        print(
            f"{size:<15} | {std_ms:<15.4f} | {orjson_ms:<15.4f} | {factor:<15.2f}x"
        )

    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_suite()