"""
Script that kills all Vesper Recorder processes.

The script will kill any number of root Vesper Recorder processes and
all of their descendants.

The script assumes that any process whose command line contains
"vesper_recorder" but not "kill_vesper_recorder" and that has no
ancestors is a root Vesper Recorder process.

This script was written with assistance from ChatGPT 5.
"""


import psutil
import sys
from typing import Iterable

KILL_NAME = 'kill_vesper_recorder'
RECORDER_NAME = 'vesper_recorder'
GRACE_SECONDS = 5.0

def matches(p: psutil.Process) -> bool:
    try:
        command = ' '.join(p.cmdline())
        return RECORDER_NAME in command and KILL_NAME not in command
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def iter_root_targets() -> Iterable[psutil.Process]:
    procs = [
        p for p in psutil.process_iter(['pid', 'name', 'cmdline'])
        if matches(p)]
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
        print('No vesper_recorder process found.')
        return 0
    print(f'Found {len(roots)} vesper_recorder root process(es).')
    for r in roots:
        try:
            print(f'Terminating tree rooted at PID {r.pid} ({r.name()})')
        except psutil.NoSuchProcess:
            continue
        terminate_tree(r)
    print('Done.')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nInterrupted.')
        