"""Utility functions pertaining to Raven selection table files."""


import csv


def get_selection_table_file_paths(dir_path, file_name_suffixes):
    return [
        p for p in dir_path.glob('*')
        if is_selection_table_file_name(p.name, file_name_suffixes)]


def is_selection_table_file_name(file_name, file_name_suffixes):
    
    if file_name.startswith('.'):
        return False
    
    for suffix in file_name_suffixes:
        if file_name.endswith(suffix):
            return True
        
    return False

    
def read_selection_table_file(file_path):
    
    with open(file_path, newline='') as file_:
        reader = csv.reader(file_, delimiter='\t')
        header = reader.__next__()
        rows = [row for row in reader]
        
    return header, rows
