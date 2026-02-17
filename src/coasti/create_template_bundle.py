from __future__ import annotations

import subprocess
from pathlib import Path


def create_template_bundle(repo_root: Path, out_file: Path) -> None:
    print("Creating template bundle from git repo:")
    print(f"{repo_root=}")
    print(f"{out_file=}")

    assert repo_root.is_dir()

    out_file.parent.mkdir(parents=True, exist_ok=True)

    subprocess.check_call(
        ["git", "bundle", "create", str(out_file), "--all"],
        cwd=str(repo_root),
    )

    # Status
    print("List of git heads:")
    subprocess.check_call(["git", "bundle", "list-heads", str(out_file)])
    print(f"Wrote bundle to: {out_file}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    out_file = repo_root / "src" / "coasti" / "_bundles" / "template-repo.bundle"

    create_template_bundle(
        repo_root=repo_root,
        out_file=out_file,
    )
