import json
import subprocess
import sys
from pathlib import Path


def check_structure(root: Path) -> dict:
    # Count directories within depth 2 equivalent
    dirs = [p for p in root.rglob("*") if p.is_dir() and len(p.relative_to(root).parts) <= 2]
    return {"n_dirs_depth_le_2": len(dirs), "pass": len(dirs) >= 15}


def check_deps() -> dict:
    missing = []
    for pkg in ["pandas", "rapidfuzz"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return {"pass": not missing, "missing": missing}


def main() -> int:
    root = Path(__file__).resolve().parent
    struct = check_structure(root)
    deps = check_deps()
    overall = struct["pass"] and deps["pass"]
    result = {"structure": struct, "dependencies": deps, "pass": overall}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
