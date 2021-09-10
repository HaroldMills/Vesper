from pathlib import Path
import csv
import itertools

import vesper.psw.util.raven_utils as raven_utils


RECORDING_DIR_PATH = Path('/Volumes/Recordings1/Northern Goshawks/Recordings')
SELECTION_TABLE_FILE_NAME_SUFFIXES = ('_sel.NOGO.txt',)
OUTPUT_FILE_NAME = 'All Selections.csv'


def main():
    
    file_contents = [
        raven_utils.read_selection_table_file(p)
        for p in raven_utils.get_selection_table_file_paths(
            RECORDING_DIR_PATH, SELECTION_TABLE_FILE_NAME_SUFFIXES)]
    
    if len(file_contents) == 0:
        print('No selection table files found.')
        
    else:
        
        header = file_contents[0][0]
        
        row_lists = tuple(zip(*file_contents))[1]
        rows = itertools.chain.from_iterable(row_lists)
        
        write_csv_file(header, rows)
        
        
def write_csv_file(header, rows):
    
    file_path = RECORDING_DIR_PATH / OUTPUT_FILE_NAME
    
    with open(file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)
        
        
if __name__ == '__main__':
    main()
