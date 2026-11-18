#!/usr/bin/env python3
"""Run the product repository's test suite and print only a summary.

This repository is public, so its Actions logs are public. The product
repository is private: its test names, file paths, assertion diffs and source
lines must never reach a log here. Every command's output goes to a log file
outside the workspace that is never printed or uploaded. The only lines
printed are this script's fixed step labels, each step's exit status, and the
pass/fail counts parsed out of the test runners' summary lines (numbers and a
fixed set of words, nothing copied verbatim), plus, for a failed pytest run, the
node id of each failing test (path and test name only, checked against a strict
pattern; never its message, diff or source lines). The commands run without the
runner's file-command variables (GITHUB_STEP_SUMMARY and the like), so they
cannot write a job summary, step output or environment change either, and
without the calling make's state (MAKEFLAGS, MAKELEVEL), so they run as the
product's own CI runs them.

Usage: run.py --product DIR --log FILE python|desktop|rust
Exit status: 0 when every step passed, else the failing step's status.
To see why a step failed, run the same suite locally in the product checkout
(`make tests`).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PYTEST_SUMMARY = re.compile(r"^=*\s*(.*?) in \d+(?:\.\d+)?s(?: \(\d+:\d\d:\d\d\))?\s*=*\s*$")
PYTEST_COUNT = re.compile(r"\b(\d+) (passed|failed|skipped|xfailed|xpassed|errors?|deselected|warnings?)\b")
#: pytest's short summary ("-rfE"): "FAILED tests/x.py::Case::test_y - message".
#: Only the node id is kept, and only when it is a plain path::name id.
PYTEST_FAILED = re.compile(r"^(FAILED|ERROR) (tests/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.py(?:::[A-Za-z0-9_]+){1,3})(?:\[[^\]]*\])?(?: - .*)?$")
MAX_FAILED_IDS = 20
VITEST_LINE = re.compile(r"^\s*(Test Files|Tests)\s+(.*)$")
VITEST_COUNT = re.compile(r"\b(\d+) (passed|failed|skipped|todo)\b")
CARGO_RESULT = re.compile(
    r"^test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out"
)
FILE_COMMANDS = frozenset({"GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_PATH", "GITHUB_STATE", "GITHUB_STEP_SUMMARY"})
#: `make product-ci` starts this script, so its environment carries the calling
#: make's state. The product's own CI runs pytest directly, and its tests run
#: `make` and compare the output: an inherited MAKELEVEL adds "Entering
#: directory" lines and MAKEFLAGS passes this make's variables down.
MAKE_STATE = frozenset({"MAKEFLAGS", "MAKELEVEL", "MFLAGS", "MAKEOVERRIDES"})


@dataclass(frozen=True)
class Step:
    label: str
    argv: tuple[str, ...]
    cwd: str = "."
    timeout_s: int = 600
    counts: str = ""  # "pytest" or "vitest": parse that runner's summary


def python_suite_workers() -> int:
    """Cores this dedicated runner should give pytest-xdist: every core, at least 2."""
    return max(2, os.cpu_count() or 2)


def python_steps(python: str) -> list[Step]:
    """The Python job of the product's own ci.yml, step for step."""
    return [
        Step("install dependencies", (python, "-m", "pip", "install", "--disable-pip-version-check",
                                      "-r", "engine/requirements-dev.txt"), timeout_s=600),
        Step("playwright import boundary", (python, "release/scripts/check_playwright_imports.py"), timeout_s=120),
        # The product's own CI runs `make cli-tests`. Its default PYTEST_WORKERS
        # is half the cores, which is 1 (no xdist) on a 2-core runner, and a
        # single pytest process hits the 900 s timeout. This job is a dedicated
        # runner, so use every core, and at least 2 so xdist is on.
        Step("test suite", ("timeout", "-s", "ABRT", "900", "make", "cli-tests",
                            f"PYTHON={python} -u",
                            "PYTEST_ARGS=tests/ -q -rfE -o faulthandler_timeout=300",
                            f"PYTEST_WORKERS={python_suite_workers()}"),
             timeout_s=960, counts="pytest"),
    ]


def rust_steps() -> list[Step]:
    """The Rust engine tests (`make cli-rust-tests` in the product checkout).

    Live Google Chrome tests in that suite skip when Chrome is not installed.
    """
    return [
        Step("test suite", ("make", "cli-rust-tests"), timeout_s=2400, counts="cargo"),
    ]


def desktop_steps(pnpm: str = "pnpm") -> list[Step]:
    """The desktop job of the product's own ci.yml: install, typecheck, lint, test, build."""
    return [
        Step("install", (pnpm, "install", "--frozen-lockfile"), cwd="desktop", timeout_s=600),
        Step("typecheck", (pnpm, "typecheck"), cwd="desktop", timeout_s=600),
        Step("lint", (pnpm, "lint"), cwd="desktop", timeout_s=600),
        Step("test", (pnpm, "test"), cwd="desktop", timeout_s=900, counts="vitest"),
        Step("build", (pnpm, "build"), cwd="desktop", timeout_s=600),
    ]


def pytest_counts(text: str) -> str:
    """'6905 passed, 526 skipped' from pytest's last summary line ('... in 300.12s'); '' when there is none."""
    for line in reversed(ANSI.sub("", text).splitlines()):
        summary = PYTEST_SUMMARY.match(line)
        if summary:
            return ", ".join(f"{n} {word}" for n, word in PYTEST_COUNT.findall(summary.group(1)))
    return ""


def pytest_failed_ids(text: str) -> list[str]:
    """Node ids of failing pytest tests from the short summary; parametrize ids and messages dropped."""
    ids: list[str] = []
    for line in ANSI.sub("", text).splitlines():
        match = PYTEST_FAILED.match(line.strip())
        if match:
            entry = f"{match.group(1).lower()} {match.group(2)}"
            if entry not in ids:
                ids.append(entry)
    return ids[:MAX_FAILED_IDS]


def vitest_counts(text: str) -> str:
    """'files: 98 passed; tests: 1367 passed' from vitest's summary; '' when there is none."""
    parts = []
    for line in ANSI.sub("", text).splitlines():
        match = VITEST_LINE.match(line)
        if not match:
            continue
        found = VITEST_COUNT.findall(match.group(2))
        if found:
            name = "files" if match.group(1) == "Test Files" else "tests"
            parts.append(f"{name}: " + ", ".join(f"{n} {word}" for n, word in found))
    return "; ".join(parts[-2:])


def cargo_counts(text: str) -> str:
    """'40 passed, 2 ignored' aggregated from cargo's 'test result:' lines; '' when there is none.

    Only the counts and a fixed set of words are printed. Crate names and
    individual test names stay in the private log.
    """
    passed = failed = ignored = 0
    found = False
    for line in ANSI.sub("", text).splitlines():
        match = CARGO_RESULT.match(line.strip())
        if not match:
            continue
        found = True
        passed += int(match.group(1))
        failed += int(match.group(2))
        ignored += int(match.group(3))
    if not found:
        return ""
    parts = [f"{passed} passed"]
    if failed:
        parts.append(f"{failed} failed")
    if ignored:
        parts.append(f"{ignored} ignored")
    return ", ".join(parts)


COUNTERS = {"pytest": pytest_counts, "vitest": vitest_counts, "cargo": cargo_counts}


def run_steps(steps: list[Step], product: Path, log: Path, out=sys.stdout) -> int:
    """Run *steps* in order inside *product*, every byte of output to *log*; stop at the first failure."""
    log.parent.mkdir(parents=True, exist_ok=True)
    env = {name: value for name, value in os.environ.items() if name not in FILE_COMMANDS | MAKE_STATE}
    with log.open("ab") as sink:
        for step in steps:
            started = time.monotonic()
            sink.write(f"\n===== {step.label} =====\n".encode())
            sink.flush()
            before = sink.tell()
            try:
                status = subprocess.run(step.argv, cwd=product / step.cwd, env=env, stdin=subprocess.DEVNULL,
                                        stdout=sink, stderr=subprocess.STDOUT, timeout=step.timeout_s).returncode
                verdict = "ok" if status == 0 else f"failed (exit {status})"
            except subprocess.TimeoutExpired:
                status, verdict = 124, f"failed (timed out after {step.timeout_s} s)"
            except OSError as exc:
                status, verdict = 127, f"failed (could not start: {type(exc).__name__})"
            sink.flush()
            line = f"{step.label}: {verdict} in {time.monotonic() - started:.0f} s"
            if step.counts:
                with log.open("rb") as read:
                    read.seek(before)
                    counts = COUNTERS[step.counts](read.read().decode("utf-8", "replace"))
                if counts:
                    line += f" [{counts}]"
            print(line, file=out, flush=True)
            if status != 0 and step.counts == "pytest":
                with log.open("rb") as read:
                    read.seek(before)
                    for entry in pytest_failed_ids(read.read().decode("utf-8", "replace")):
                        print(f"  {entry}", file=out, flush=True)
            if status != 0:
                print("Output is withheld because the product repository is private; "
                      "run the same suite in a local checkout to see it.", file=out, flush=True)
                return status
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("suite", choices=("python", "desktop", "rust"))
    parser.add_argument("--product", required=True, type=Path, help="the product repository checkout")
    parser.add_argument("--log", required=True, type=Path, help="private log file, never printed")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    if args.suite == "python":
        steps = python_steps(args.python)
    elif args.suite == "desktop":
        steps = desktop_steps()
    else:
        steps = rust_steps()
    return run_steps(steps, args.product, args.log)


if __name__ == "__main__":
    sys.exit(main())
