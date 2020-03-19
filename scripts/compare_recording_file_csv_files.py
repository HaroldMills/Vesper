from collections import namedtuple
from pathlib import Path
import csv


DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/'
    '2016 MPG Ranch Recording Files Comparison')

DEBBIE_FILE_PATH = DATA_DIR_PATH / 'Recording Files Debbie.csv'
HAROLD_FILE_PATH = DATA_DIR_PATH / 'Recording Files Harold.csv'
OUTPUT_FILE_PATH = DATA_DIR_PATH / 'Differences.txt'


def main():
    
    d_files = read_file(DEBBIE_FILE_PATH)
    h_files = read_file(HAROLD_FILE_PATH)
    
    d_names = frozenset(d_files.keys())
    h_names = frozenset(h_files.keys())
    
    d_extra_names = d_names - h_names
    h_extra_names = h_names - d_names
    
    differing_names = get_differing_file_names(d_files, h_files)
    
    write_output_file(
        d_extra_names, h_extra_names, differing_names, d_files, h_files)
    

def read_file(path):
    with open(path) as file_:
        reader = csv.reader(file_)
        files = [File(*row) for row in reader]
    return dict((f.name, f) for f in files)
            
    
def get_differing_file_names(d_files, h_files):
    d_names = frozenset(d_files.keys())
    h_names = frozenset(h_files.keys())
    names = d_names & h_names
    differing_names = [n for n in names if d_files[n] != h_files[n]]
    return frozenset(differing_names)


def write_output_file(
        d_extra_names, h_extra_names, differing_names, d_files, h_files):
    
    with open(OUTPUT_FILE_PATH, 'w') as f:
        w = OutputWriter(f)
        list_extra_file_names(w, 'Debbie', 'Harold', d_extra_names)
        list_extra_file_names(w, 'Harold', 'Debbie', h_extra_names)
        list_differing_files(w, differing_names, d_files, h_files)
        list_files_to_send_to_harold(w, d_extra_names, differing_names)
        list_total_sizes(w, d_files, d_extra_names, differing_names)
    
    
def list_extra_file_names(w, name_a, name_b, file_names):
    
    w.write(
        f'{len(file_names)} files that {name_a} has that {name_b} does not:')
    
    for name in sort_names(file_names):
        w.write(f'    {name}')
    
    
def sort_names(names):
    return sorted(names, key=lambda n: n.lower())


def list_differing_files(w, names, d_files, h_files):
    
    w.write(
        f'{len(names)} files that Debbie and Harold have different '
        f'versions of:')
    
    for name in sort_names(names):
        
        d_file = d_files[name]
        h_file = h_files[name]
        
        w.write(f'    {name}')
        w.write(f'        Debbie: {d_file[1:]}')
        w.write(f'        Harold: {h_file[1:]}')
        
        
def list_files_to_send_to_harold(w, d_extra_names, differing_names):
    
    names = d_extra_names | differing_names
    
    w.write(f'{len(names)} files for Debbie to send to Harold:')
    
    for name in sort_names(names):
        w.write(f'    {name}')
        
        
def list_total_sizes(w, d_files, d_extra_names, differing_names):
    
    total_size = get_size(d_files)
    extra_size = get_size(d_files, d_extra_names)
    differing_size = get_size(d_files, differing_names)
    
    gig = 2 ** 30
    total_gb = total_size / gig
    min_gb = (extra_size + differing_size) / gig
    
    w.write(f"Total size of Debbie's {len(d_files)} files: {total_gb} GB")
    
    h_file_count = len(d_extra_names) + len(differing_names)
    w.write(f'Total size of {h_file_count} files Harold needs: {min_gb} GB')
 

def get_size(files, names=None):
    
    if names is None:
        names = files.keys()
        
    return sum(get_size_aux(files[n]) for n in names)


def get_size_aux(f):
    return int(f.length) * int(f.channel_count) * int(f.sample_size) // 8


File = namedtuple(
    'File', [
        'name', 'sample_rate', 'length', 'channel_count', 'sample_size',
        'comp_type', 'comp_name'])


class OutputWriter:
    
    def __init__(self, file_):
        self._file = file_
        
    def write(self, *args):
        print(*args, file=self._file)


if __name__ == '__main__':
    main()
