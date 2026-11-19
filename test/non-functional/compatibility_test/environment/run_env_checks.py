#!/usr/bin/env python3
"""Run the environment checks and print one PASS/FAIL line per check.

Each ``env_check_*.py`` is a standalone script (it executes on import, which
is why the files are not named ``test_*`` - pytest must not collect them).
This runner starts each one as a separate process with a timeout and
reports exit status and duration; full output goes to
``<tmp>/ai_platform_env_checks/<check>.log``.

    python run_env_checks.py                 # all checks
    python run_env_checks.py 01 03 26        # selected numbers
    python run_env_checks.py --timeout 900

Several checks download models on first run (Hugging Face, Ollama); the
LLM checks (25-28) need the corresponding local server.
"""

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = Path(tempfile.gettempdir()) / "ai_platform_env_checks"


def main() -> int:
    """Run the selected checks; exit 1 if any failed."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("numbers", nargs="*", help="two-digit check numbers (default: all)")
    parser.add_argument("--timeout", type=float, default=600.0)
    args = parser.parse_args()

    checks = sorted(HERE.glob("env_check_*.py"))
    if args.numbers:
        checks = [c for c in checks if c.name.split("_")[2] in args.numbers]
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    failed = 0
    for check in checks:
        log = LOG_DIR / (check.stem + ".log")
        start = time.perf_counter()
        try:
            completed = subprocess.run([sys.executable, str(check)], capture_output=True,
                                       text=True, timeout=args.timeout, check=False)
            status = "PASS" if completed.returncode == 0 else f"FAIL({completed.returncode})"
            log.write_text(completed.stdout + "\n--- stderr ---\n" + completed.stderr,
                           encoding="utf-8")
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
        failed += status != "PASS"
        print(f"{status:9} {time.perf_counter() - start:7.1f} s  {check.name}")
    print(f"\n{len(checks) - failed}/{len(checks)} passed; logs in {LOG_DIR}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
