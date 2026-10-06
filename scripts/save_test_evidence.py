"""
Save raw pytest and coverage output as A3 evidence.

Runs the full test suite with coverage and writes everything pytest
prints to a timestamped text file, together with a short header
describing the environment the run happened in.

Usage (from the project root, with the virtual environment active):

    python scripts/save_test_evidence.py

Output:

    evidence/test-output/pytest_<YYYYMMDD_HHMMSS>.txt

Nothing secret is written. The script does not read .env, and the only
thing it records about the database is the backend name (for example
"sqlite" or "postgresql") -- never the connection string, user name or
password.
"""

import datetime
import os
import platform
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "evidence", "test-output")

PYTEST_COMMAND = [
    sys.executable, "-m", "pytest", "-v",
    "-p", "no:cacheprovider",
    "--cov=app", "--cov-report=term-missing",
]


def git(*args):
    """Return the output of a git command, or 'unknown' if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def test_database_backend():
    """Backend name only (text before the first ':' or '+'), never the URL."""
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        return "sqlite (in-memory default)"
    return url.split(":", 1)[0].split("+", 1)[0]


def main():
    started = datetime.datetime.now().astimezone()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"pytest_{started:%Y%m%d_%H%M%S}.txt")

    uncommitted = git("status", "--porcelain")
    uncommitted_label = {"": "no", "unknown": "unknown"}.get(uncommitted, "yes")
    header = "\n".join([
        "CyberShield automated test evidence",
        "=" * 60,
        f"Run started:      {started:%Y-%m-%d %H:%M:%S %Z}",
        f"Git branch:       {git('rev-parse', '--abbrev-ref', 'HEAD')}",
        f"Git commit:       {git('rev-parse', 'HEAD')}",
        f"Uncommitted work: {uncommitted_label}",
        f"Python:           {platform.python_version()} ({platform.python_implementation()})",
        f"Platform:         {platform.platform()}",
        f"Test database:    {test_database_backend()}",
        f"Command:          python {' '.join(PYTEST_COMMAND[1:])}",
        "=" * 60,
        "",
    ])

    # Plain output: no colour codes, and wide enough that test names are
    # not truncated in the saved file.
    env = dict(os.environ, NO_COLOR="1", PY_COLORS="0", COLUMNS="120")
    result = subprocess.run(
        PYTEST_COMMAND, cwd=PROJECT_ROOT, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    finished = datetime.datetime.now().astimezone()
    footer = "\n".join([
        "",
        "=" * 60,
        f"Run finished:     {finished:%Y-%m-%d %H:%M:%S %Z}",
        f"pytest exit code: {result.returncode} ({'all tests passed' if result.returncode == 0 else 'FAILURES OR ERRORS - see above'})",
        "",
    ])

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(header + result.stdout + footer)

    print(header + result.stdout + footer)
    print(f"Saved to: {os.path.relpath(output_path, PROJECT_ROOT)}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
