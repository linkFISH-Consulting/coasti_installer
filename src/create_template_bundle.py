from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "src" / "coasti" / "_bundles" / "template-repo.bundle"

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print(REPO_ROOT)

    subprocess.check_call(
        ["git", "bundle", "create", str(OUT), "--all"],
        cwd=str(REPO_ROOT),
    )

    # Status
    print("List of git heads:")
    subprocess.check_call(["git", "bundle", "list-heads", str(OUT)])
    print(f"Wrote bundle to: {OUT}")

if __name__ == "__main__":
    main()
