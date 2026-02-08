"""
Performance comparison tests: C++ vs Rust backend.

These tests run each backend for a fixed duration (default 60 seconds per backend)
so you get stable, measurable throughput. Run with -s to see printed results.

Why Rust is typically slower (top 2): (1) C++ does full parse + event assembly in
native code and returns one event per call; Rust exposes a fragment-level lexer
and event assembly is done in Python. (2) Rust has more FFI round-trips per event
(one per fragment and per capture) vs one call per event for C++. See README and
docs/architecture.md for details.

    pytest tests/test_backend_performance.py -v -s

For a shorter run (e.g. quick sanity check), set LOG_SURGEON_BENCH_DURATION:

    LOG_SURGEON_BENCH_DURATION=10 pytest tests/test_backend_performance.py -v -s

They assert that both backends produce correct results; the timing is
informational (no pass/fail based on which backend is faster).

When running from the project root, LOG_MECHANIC_LIB_PATH is set to the
development build dir (build/deps/log-mechanic-install) if present, so
the Rust backend can load without being installed from a wheel.

Memory usage:
  The Rust backend now streams one fragment at a time (O(current event) memory).
  The stream benchmark can run many iterations without unbounded RAM growth.
  Optional: set LOG_SURGEON_BENCH_MAX_RSS_GROWTH_MB to stop early if RSS grows
  (e.g. 0 to disable, or a positive value as a safety cap).
"""

import gc
import os
import time
from pathlib import Path

import pytest


def _get_rss_mb() -> float:
    """Current process RSS in MB (Linux: from /proc/self/status). Returns 0 if unavailable."""
    try:
        with open("/proc/self/status", "rb") as f:
            for line in f:
                if line.startswith(b"VmRSS:"):
                    # "VmRSS:    12345 kB"
                    parts = line.split()
                    if len(parts) >= 3:
                        return int(parts[1]) / 1024.0  # kB -> MB
                    break
    except OSError:
        pass
    return 0.0

# Allow Rust backend to find liblog_mechanic when running from source
_project_root = Path(__file__).resolve().parent.parent
_rust_lib = _project_root / "build" / "deps" / "log-mechanic-install" / "liblog_mechanic.so"
if _rust_lib.exists() and "LOG_MECHANIC_LIB_PATH" not in os.environ:
    os.environ["LOG_MECHANIC_LIB_PATH"] = str(_rust_lib)

from log_surgeon import PATTERN, Parser


def _rust_backend_available() -> bool:
    """Return True if the Rust backend can be loaded (liblog_mechanic found)."""
    try:
        p = Parser(backend="rust")
        p.add_var("x", r"(?<y>\d+)")
        p.compile()
        return True
    except FileNotFoundError:
        return False


def _make_parser(backend: str) -> Parser:
    """Build a parser with the same schema for either backend."""
    parser = Parser(backend=backend)
    parser.add_var("resource", rf"(?<memory_gb>{PATTERN.FLOAT}) GiB ram")
    parser.add_var("metric", rf"metric=(?<metric_name>[a-zA-Z0-9_]+) value=(?<value>\d+)")
    parser.compile()
    return parser


def _metric_log_lines(n: int) -> str:
    """Generate n lines of metric-style logs."""
    templates = [
        "2024-01-01 INFO: metric=cpu value=42\n",
        "2024-01-01 INFO: metric=memory value=100\n",
        "2024-01-01 INFO: metric=disk value=7\n",
        "2024-01-01 INFO: metric=load value=2\n",
    ]
    return "".join(templates[i % len(templates)] for i in range(n))


def _single_line() -> str:
    """Single log line for parse_event micro-benchmark."""
    return "16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram\n"


def _normalize_log_type(s: str) -> str:
    """Normalize log type for comparison (C++ uses <newLine> at end, Rust may omit)."""
    s = s.strip().replace("<newLine>", "\n").replace("\r\n", "\n")
    return s.rstrip("\n")  # ignore trailing newline difference


_requires_rust = pytest.mark.skipif(
    not _rust_backend_available(),
    reason="Rust backend (liblog_mechanic) not available",
)


class TestBackendCorrectness:
    """Ensure both backends produce equivalent results before comparing performance."""

    @_requires_rust
    def test_both_backends_extract_same_values(self):
        """C++ and Rust backends should yield identical extracted fields for the same input."""
        line = _single_line()
        cpp_parser = _make_parser("cpp")
        rust_parser = _make_parser("rust")

        cpp_event = cpp_parser.parse_event(line)
        rust_event = rust_parser.parse_event(line)

        assert cpp_event is not None
        assert rust_event is not None
        assert cpp_event["memory_gb"] == rust_event["memory_gb"]
        # Log type may differ in newline representation (<newLine> vs \n)
        assert _normalize_log_type(cpp_event.get_log_type()) == _normalize_log_type(
            rust_event.get_log_type()
        )

    @_requires_rust
    def test_both_backends_same_event_count_streaming(self):
        """Both backends produce events for each log line (count may differ by backend)."""
        log_data = _metric_log_lines(100)
        cpp_parser = _make_parser("cpp")
        rust_parser = _make_parser("rust")

        cpp_events = list(cpp_parser.parse(log_data))
        rust_events = list(rust_parser.parse(log_data))

        assert len(cpp_events) >= 100
        assert len(rust_events) >= 100

        def _val(event: dict, key: str):
            v = event[key]
            return v[0] if isinstance(v, list) else v

        for c, r in zip(cpp_events[:100], rust_events[:100]):
            assert _val(c, "metric_name") == _val(r, "metric_name")
            assert _val(c, "value") == _val(r, "value")


# Target duration per backend in seconds. Each performance test runs each backend
# for this long to get stable measurements. Total time per test ≈ 2 * TARGET_DURATION_SEC.
# Override with env var LOG_SURGEON_BENCH_DURATION (e.g. 10 for a quick run).
TARGET_DURATION_SEC = int(
    os.environ.get("LOG_SURGEON_BENCH_DURATION", "60")
)

# If stream benchmark RSS grows by more than this many MB from start, stop early.
# Set to 0 to disable. Override with LOG_SURGEON_BENCH_MAX_RSS_GROWTH_MB.
MAX_RSS_GROWTH_MB = float(os.environ.get("LOG_SURGEON_BENCH_MAX_RSS_GROWTH_MB", "0"))


class TestBackendPerformance:
    """
    Compare C++ vs Rust backend performance.

    Each benchmark runs each backend for TARGET_DURATION_SEC (see constant above)
    so results are stable. Run with: pytest tests/test_backend_performance.py -v -s
    """

    # Chunk size for stream benchmark.
    STREAM_CHUNK_LINES = 5_000
    # Fixed iteration count for stream. Override with LOG_SURGEON_BENCH_STREAM_ITERS.
    # Rust backend now streams (O(event) memory), so many iterations are safe.
    STREAM_ITERATIONS = int(os.environ.get("LOG_SURGEON_BENCH_STREAM_ITERS", "500"))

    def _run_for_duration_parse_event(
        self, parser: Parser, line: str, duration_sec: float
    ) -> tuple[int, float]:
        """Run parse_event(line) in a loop until duration_sec elapsed. Return (count, elapsed)."""
        start = time.perf_counter()
        count = 0
        while (time.perf_counter() - start) < duration_sec:
            parser.parse_event(line)
            count += 1
        elapsed = time.perf_counter() - start
        return count, elapsed

    def _run_stream_fixed_iterations(
        self,
        parser: Parser,
        log_data: str,
        iterations: int,
        max_rss_growth_mb: float = 0,
    ) -> tuple[int, float, bool]:
        """Run parse(log_data) up to `iterations` times, consuming events one-by-one.
        No list materialization; gc every 20 iterations.
        If max_rss_growth_mb > 0, sample RSS every 10 iterations and stop when
        growth exceeds that (returns early). Returns (total_events, elapsed, stopped_early)."""
        t0 = time.perf_counter()
        total_events = 0
        stopped_early = False
        rss_start_mb = _get_rss_mb() if max_rss_growth_mb > 0 else 0.0

        for i in range(iterations):
            total_events += sum(1 for _ in parser.parse(log_data))
            if (i + 1) % 20 == 0:
                gc.collect()
            if max_rss_growth_mb > 0 and (i + 1) % 10 == 0:
                rss_mb = _get_rss_mb()
                if rss_mb > 0 and (rss_mb - rss_start_mb) > max_rss_growth_mb:
                    stopped_early = True
                    break
        elapsed = time.perf_counter() - t0
        return total_events, elapsed, stopped_early

    @_requires_rust
    def test_performance_parse_event_cpp_vs_rust(self):
        """
        Benchmark parse_event() for TARGET_DURATION_SEC per backend.
        Measures per-call overhead and single-event parsing speed.
        """
        line = _single_line()
        cpp_parser = _make_parser("cpp")
        rust_parser = _make_parser("rust")
        duration = TARGET_DURATION_SEC

        print(f"\n[parse_event] Running each backend for {duration}s ...")
        n_cpp, t_cpp = self._run_for_duration_parse_event(cpp_parser, line, duration)
        n_rust, t_rust = self._run_for_duration_parse_event(rust_parser, line, duration)

        assert n_cpp > 0 and n_rust > 0
        rate_cpp = n_cpp / t_cpp
        rate_rust = n_rust / t_rust
        faster = "C++" if rate_cpp > rate_rust else "Rust"
        ratio = max(rate_cpp, rate_rust) / min(rate_cpp, rate_rust) if min(rate_cpp, rate_rust) > 0 else 0

        print(f"  C++:  {n_cpp:,} events in {t_cpp:.2f}s  →  {rate_cpp:,.0f} events/s")
        print(f"  Rust: {n_rust:,} events in {t_rust:.2f}s  →  {rate_rust:,.0f} events/s")
        print(f"  Faster: {faster} (≈{ratio:.2f}x)")

    @_requires_rust
    def test_performance_parse_stream_cpp_vs_rust(self):
        """
        Benchmark parse() with a fixed number of chunk iterations (no time-based loop).
        Consumes stream one event at a time; no list. Monitors RSS and stops early
        if growth exceeds MAX_RSS_GROWTH_MB so the test doesn't exhaust RAM.
        """
        log_data = _metric_log_lines(self.STREAM_CHUNK_LINES)
        cpp_parser = _make_parser("cpp")
        rust_parser = _make_parser("rust")
        iters = self.STREAM_ITERATIONS
        max_growth = MAX_RSS_GROWTH_MB

        msg = f"\n[parse stream] Chunk={self.STREAM_CHUNK_LINES:,} lines, up to {iters} iterations"
        if max_growth > 0:
            msg += f" (stop if RSS grows > {max_growth:.0f} MB)"
        msg += " ..."
        print(msg)
        events_cpp, t_cpp, early_cpp = self._run_stream_fixed_iterations(
            cpp_parser, log_data, iters, max_rss_growth_mb=max_growth
        )
        events_rust, t_rust, early_rust = self._run_stream_fixed_iterations(
            rust_parser, log_data, iters, max_rss_growth_mb=max_growth
        )

        if early_cpp:
            print("  [C++] stopped early: RSS growth exceeded limit")
        if early_rust:
            print("  [Rust] stopped early: RSS growth exceeded limit")

        rate_cpp = events_cpp / t_cpp if t_cpp > 0 else 0
        rate_rust = events_rust / t_rust if t_rust > 0 else 0
        faster = "C++" if rate_cpp > rate_rust else "Rust"
        ratio = max(rate_cpp, rate_rust) / min(rate_cpp, rate_rust) if min(rate_cpp, rate_rust) > 0 else 0

        print(f"  C++:  {events_cpp:,} events in {t_cpp:.2f}s  →  {rate_cpp:,.0f} events/s")
        print(f"  Rust: {events_rust:,} events in {t_rust:.2f}s  →  {rate_rust:,.0f} events/s")
        print(f"  Faster: {faster} (≈{ratio:.2f}x)")
