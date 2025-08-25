"""
Script that kills the Vesper Recorder process and all of its
descendants.

This script was written with assistance from ChatGPT 5.
"""


import psutil
import sys
from typing import Iterable

TARGET = "vesper_recorder"
EXCLUDE_SCRIPT = "kill_vesper_recorder.py"
GRACE_SECONDS = 5.0

def matches(p: psutil.Process) -> bool:
    try:
        name = p.name() or ""
        cmdline_parts = p.cmdline()
        cmdline = " ".join(cmdline_parts)
        # Exclude this script (or any process running it)
        if any(EXCLUDE_SCRIPT in part for part in cmdline_parts):
            return False
        if TARGET.lower() in name.lower():
            return True
        return TARGET.lower() in cmdline.lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def iter_root_targets() -> Iterable[psutil.Process]:
    procs = [p for p in psutil.process_iter(["pid", "name", "cmdline"]) if matches(p)]
    if not procs:
        return []
    target_pids = {p.pid for p in procs}
    roots = []
    for p in procs:
        try:
            ancestors = {a.pid for a in p.parents()}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if not (ancestors & target_pids):
            roots.append(p)
    return roots

def terminate_tree(root: psutil.Process):
    try:
        descendants = root.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return
    procs = [root] + descendants
    for p in procs:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    gone, alive = psutil.wait_procs(procs, timeout=GRACE_SECONDS)
    if alive:
        for p in alive:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        psutil.wait_procs(alive, timeout=2)

def main():
    roots = list(iter_root_targets())
    if not roots:
        print("No vesper_recorder process found.")
        return 0
    print(f"Found {len(roots)} vesper_recorder root process(es).")
    for r in roots:
        try:
            print(f"Terminating tree rooted at PID {r.pid} ({r.name()})")
        except psutil.NoSuchProcess:
            continue
        terminate_tree(r)
    print("Done.")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        