def handle_top_level_exception(process_name):
    import sys, traceback
    print(f'{process_name} raised exception:', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
