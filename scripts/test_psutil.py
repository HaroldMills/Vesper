import psutil


"""
auto_termination:

    sleep_period: 3600

    command_line_component_index: 1

    command_line_component_substring: vesper_recorder
"""


def main():

    for pid in psutil.pids():

        try:
            process = psutil.Process(pid)
            command = process.cmdline()
            time = process.create_time()
        except Exception:
            continue

        if len(command) > 0 and command[0].find('python') != -1:
            print(pid, time, command)


if __name__ == '__main__':
    main()
