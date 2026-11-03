"""Run offline checks in isolated directories, with outbound sockets disabled.

Use an interpreter with the existing project dependencies installed. No packages
are installed by this runner. Report files are written only with --report.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''import runpy, socket, sys

def deny(*args, **kwargs):
    raise RuntimeError("Offline check attempted a network connection")

socket.socket.connect = deny
socket.create_connection = deny
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
'''


def run_check(script: Path, *, probe: bool = False, timeout: float = 60) -> dict:
    """Run one check; timeout and nonzero exit become failed report entries."""
    with tempfile.TemporaryDirectory(prefix="va-offline-") as directory:
        args = ["--self-test", "--output", str(Path(directory) / "probe")] if probe else []
        env = {**os.environ, "PYTHONPATH": str(REPO), "PYTHONDONTWRITEBYTECODE": "1",
               "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "LANGCHAIN_TRACING_V2": "false", "MPLCONFIGDIR": str(Path(directory) / "mpl")}
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", BOOTSTRAP, str(script), *args],
            cwd=directory, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            code = process.returncode
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
            code = "timeout"
        return {"check": script.name, "code": code, "output": output}


def main() -> int:
    """Return nonzero if any fixture or the planning-only probe fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    results = []
    for script in sorted((REPO / "verification").glob("*_checks.py")) + [REPO / "td_ac_probe.py"]:
        result = run_check(script, probe=script.name == "td_ac_probe.py")
        results.append(result)
        print(f"{result['check']}: {result['code']}", flush=True)
        if result["code"] != 0:
            print(result["output"], flush=True)
    if args.report:
        args.report.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return int(any(result["code"] != 0 for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
