from pathlib import Path


RECORDING_DIR_PATH = Path(
    '/Volumes/Recordings1/PSW/NOGO Archive 2 Recordings')

RENAMABLE_FILE_NAME_SUFFIXES = ('_sel.NOGO.txt', '.wav')


def main():
    for path in RECORDING_DIR_PATH.glob('*'):
        if is_renamable_file(path):
            new_path = get_new_file_path(path)
            print(f'Renaming "{path.name}" to "{new_path.name}"...')
            path.rename(new_path)
    
    
def is_renamable_file(path):
    
    if not path.is_file():
        return False

    name = path.name
    
    if name.startswith('.'):
        return False
    
    for suffix in RENAMABLE_FILE_NAME_SUFFIXES:
        if name.endswith(suffix):
            return True
        
    return False
    
    
def get_new_file_path(path):
    parts = path.name.split('_')
    new_name = parts[0] + ' ' + '_'.join(parts[1:])
    return path.parent / new_name


if __name__ == '__main__':
    main()
