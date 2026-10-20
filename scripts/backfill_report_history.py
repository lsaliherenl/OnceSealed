"""Recover every report version anchored on Sepolia into reports/history/<project>/v<n>.json.

Each anchored hash is matched against the versions of reports/<project>.json in git history; the matching file
is written byte for byte. From now on scripts/seed_sepolia.py archives a version when it anchors it, so this is
only needed once (or to check the archive):

    python scripts/backfill_report_history.py           # write missing versions
    python scripts/backfill_report_history.py --check   # fail if an anchored version has no archived file
"""

import json
import subprocess
import sys

from core.config import PROJECT_ROOT
from core.hashing import hash_json
from core.reports import HISTORY, anchored_versions, history_path


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, check=True).stdout


def main() -> None:
    check = "--check" in sys.argv
    missing = 0
    for pid, versions in sorted(anchored_versions().items()):
        commits = _git("log", "--format=%H", "--", f"reports/{pid}.json").decode().split()
        by_hash: dict[str, bytes] = {}
        for c in commits:
            try:
                blob = _git("show", f"{c}:reports/{pid}.json")
            except subprocess.CalledProcessError:
                continue  # the file did not exist in this commit
            by_hash.setdefault(hash_json(json.loads(blob)), blob)
        for version, report_hash in versions:
            path = history_path(pid, version)
            if path.exists():
                if hash_json(json.loads(path.read_bytes())) != report_hash:
                    raise SystemExit(f"{path} does not hash to the anchored {report_hash}")
                continue
            if check or report_hash not in by_hash:
                print(f"  {pid} v{version}: no archived file" + ("" if check else " and not found in git history"))
                missing += 1
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(by_hash[report_hash])
            print(f"  {pid} v{version}: recovered")
    total = sum(len(v) for v in anchored_versions().values())
    print(f"{total - missing} of {total} anchored versions archived in {HISTORY.relative_to(PROJECT_ROOT)}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
