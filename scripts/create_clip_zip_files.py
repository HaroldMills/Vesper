"""
Script that creates zip files from Vesper archive clip directories.

The script puts the zip files in a directory called "Clips (zipped)"
that is a sibling of the archive's "Clips" directory. The "Clips (zipped)"
directory has the same structure as the "Clips" directory, except that
each grandchild directory of the "Clips" directory is replaced by a zip
file containing the contents of the grandchild directory.

The script should be run from the archive directory, e.g.:

    cd /Users/harold/archive
    python create_clip_zip_files.py
    
On macOS, you can unzip the resulting zip files with "unzip \*.zip".
"""


from pathlib import Path
from zipfile import ZipFile
import re


DIR_NAME_RE = re.compile('\d\d\d')


def main():
    
    dir_path = Path.cwd()
    clips_dir_path = dir_path / 'Clips'
    zips_dir_path = dir_path / 'Clips (zipped)'
    
    for clip_dir_path in clips_dir_path.glob('*/*'):
        
        parent_dir_name = clip_dir_path.parent.name
        clip_dir_name = clip_dir_path.name
        
        if DIR_NAME_RE.match(parent_dir_name) and \
                DIR_NAME_RE.match(clip_dir_name):
            
            parent_dir_path = zips_dir_path / parent_dir_name
            parent_dir_path.mkdir(parents=True, exist_ok=True)
            
            zip_file_name = f'{parent_dir_name}.{clip_dir_name}.zip'
            zip_file_path = parent_dir_path / zip_file_name
            
            print(f'Compressing "{parent_dir_name}/{clip_dir_name}"...')
            
            with ZipFile(zip_file_path, 'w') as zip_file:
                
                for clip_file_path in clip_dir_path.glob('*.wav'):
                    
                    # print(f'    Compressing file "{clip_file_path.name}"...')
                    
                    rel_path = clip_file_path.relative_to(clip_dir_path.parent)
                    zip_file.write(str(clip_file_path), str(rel_path))


if __name__ == '__main__':
    main()
