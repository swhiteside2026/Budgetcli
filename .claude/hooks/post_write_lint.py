import json
import sys
import subprocess

data = json.load(sys.stdin)
fp = data.get("tool_input", {}).get("file_path", "")

if fp.endswith(".py"):
    r = subprocess.run(["python", "-m", "ruff", "check", "."], capture_output=True, text=True)
    if r.stdout:
        print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
