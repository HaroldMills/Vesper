"""
Script that renames AudioMoth recording files for import into a Vesper archive.

Usage:

    python rename_audiomoth_recording_files.py <recording dir path> <file name prefix>
    
The script renames all AudioMoth recording files in the specified directory,
including ones in subdirectories.

For example, the command:

    python rename_audiomoth_recording_files.py "/Users/Nora/Recordings" "Nora"
    
will rename the AudioMoth recording file:

    20201030_123456.WAV
    
to:

    Nora_2020-10-30_12.34.56_Z.wav
    
Files that are not AudioMoth recording files (i.e. files that do not have
names of the form YYYYMMDD_HHMMSS.WAV) are silently ignored.
"""


from pathlib import Path
import datetime
import sys


def main():
    
    args = sys.argv
    
    if len(args) != 3:
        script_name = Path(__file__).name
        print(
            f'Usage: python {script_name} <recording dir path> '
            f'<file name prefix>')
        
    recording_dir_path = Path(args[1])
    file_name_prefix = args[2]
    
    wav_file_paths = \
        list(recording_dir_path.glob('**/*.wav')) + \
        list(recording_dir_path.glob('**/*.WAV'))
    
    for path in wav_file_paths:
        
        new_path = get_new_audiomoth_file_path(path, file_name_prefix)
        
        if new_path is not None:
            print(f'Renaming "{path}" to "{new_path}"...')
            path.rename(new_path)
        
        
def get_new_audiomoth_file_path(file_path, file_name_prefix):
    
    try:
        dt = datetime.datetime.strptime(file_path.stem, '%Y%m%d_%H%M%S')
        
    except Exception:
        return None
        
    start_time = dt.strftime('%Y-%m-%d_%H.%M.%S')
    new_file_name = f'{file_name_prefix}_{start_time}_Z.wav'

    return file_path.parent / new_file_name
    
    
if __name__ == '__main__':
    main()
