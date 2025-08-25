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


KILL_NAME = 'kill_vesper_recorder'
RECORDER_NAME = 'vesper_recorder'
GRACE_SECONDS = 5.0


def main():

    root_processes = get_root_processes()

    print(f'Found {len(root_processes)} Vesper Recorder root process(es).')

    for p in root_processes:

        try:
            print(
                f'Terminating recorder process tree rooted at PID {p.pid} '
                f'({p.name()})')
        except psutil.NoSuchProcess:
            continue

        terminate_process_tree(p)

    return 0


def get_root_processes():

    # Get candidate root processes, i.e. those with "vesper_recorder" but
    # not "kill_vesper_recorder" in their command lines.
    candidate_processes = [
        p for p in psutil.process_iter(['pid', 'cmdline'])
        if matches(p)]
    
    candidate_pids = {p.pid for p in candidate_processes}

    root_processes = []

    for p in candidate_processes:

        try:
            ancestor_pids = {a.pid for a in p.parents()}
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        if len(ancestor_pids & candidate_pids) == 0:
            # no ancestor of process is a candidate process

            root_processes.append(p)

    return root_processes


def matches(p):

    try:
        command = ' '.join(p.cmdline())
        return RECORDER_NAME in command and KILL_NAME not in command
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def terminate_process_tree(root):

    try:
        descendants = root.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return
    
    processes = [root] + descendants

    for p in processes:

        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    gone, alive = psutil.wait_procs(processes, timeout=GRACE_SECONDS)

    if alive:

        for p in alive:

            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        psutil.wait_procs(alive, timeout=2)


if __name__ == '__main__':

    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nInterrupted.')
        