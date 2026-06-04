#!/usr/bin/env python3
"""
factory call_jules — fetches delegate_to_agent.py from GitHub, executes it.
"""
import os, sys, subprocess, tempfile, urllib.request

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/RokctAI/The-Rokct-Protocol/main"
DELEGATE_PATH   = "core/skills/agent_delegation/scripts/delegate_to_agent.py"


def resolve_delegate():
    # 1. GitHub raw (no auth needed for public repo)
    url = f"{GITHUB_RAW_BASE}/{DELEGATE_PATH}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8"), "github"
    except Exception:
        pass

    # 2. Filesystem fallback — walk up from workspace root
    here = os.path.dirname(os.path.abspath(__file__))
    rock_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))  # .rokct/
    search = os.path.dirname(rock_root)                                # project root
    for _ in range(6):
        candidate = os.path.join(search, "The-Rokct-Protocol", *DELEGATE_PATH.split("/"))
        if os.path.isfile(candidate):
            with open(candidate) as f:
                return f.read(), "local"
        parent = os.path.dirname(search)
        if parent == search:
            break
        search = parent

    return None, None


def main():
    code, source = resolve_delegate()
    if not code:
        print("Error: delegate_to_agent.py not found on GitHub or local filesystem.", file=sys.stderr)
        sys.exit(1)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run([sys.executable, tmp_path] + sys.argv[1:], check=False)
        sys.exit(result.returncode)
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
