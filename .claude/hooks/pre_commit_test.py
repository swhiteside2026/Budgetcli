import json
import sys
import subprocess

data = json.load(sys.stdin)
cmd = data.get("tool_input", {}).get("command", "")

if "git commit" in cmd:
    r = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(2)
