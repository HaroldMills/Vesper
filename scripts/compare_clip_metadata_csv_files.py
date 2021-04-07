"""
Script that compares two clip metadata CSV files.

This script was written to check that the clip metadata CSV files output
after the switch from PyEphem to Skyfield were almost equal to those output
before. Solar event time columns are allowed to differ by up to one second,
and the lunar altitude and illumination columns are allowed to differ by
up to .1 degrees or percent.
"""


from pathlib import Path
import csv
import datetime
import sys


DIR_PATH = Path('/Users/harold/Desktop')
FILE_NAME_A = 'old.csv'
FILE_NAME_B = 'new.csv'

FILE_PATH_A = DIR_PATH / FILE_NAME_A
FILE_PATH_B = DIR_PATH / FILE_NAME_B


def main():
    
    rows_a = read_csv_file(FILE_PATH_A)
    rows_b = read_csv_file(FILE_PATH_B)
    
    compare_row_counts(rows_a, rows_b)
    compare_headers(rows_a[0], rows_b[0])
    
    diff_count = compare_rows(rows_a[1:], rows_b[1:])
    
    if diff_count == 0:
        print('Files are the same within the allowed differences.')
    else:
        print(f'Found {diff_count} differences outside of those allowed.')


def read_csv_file(file_path):
    with open(file_path) as csv_file:
        reader = csv.reader(csv_file)
        return [row for row in reader]


def compare_row_counts(rows_a, rows_b):
    if len(rows_a) != len(rows_b):
        print('CSV file row counts differ.')
        print(f'    File "{str(FILE_PATH_A)}" has {len(rows_a)} rows.')
        print(f'    File "{str(FILE_PATH_B)}" has {len(rows_b)} rows.')
        sys.exit(1)


def compare_headers(header_a, header_b):
    if header_a != header_b:
        print('CSV file headers differ.')
        print(f'    File "{str(FILE_PATH_A)}" header is {header_a}.')
        print(f'    File "{str(FILE_PATH_B)}" header is {header_b}.')
        sys.exit(1)
        
        
def compare_rows(rows_a, rows_b):
    
    diff_count = 0
    
    for i, (row_a, row_b) in enumerate(zip(rows_a, rows_b)):
        
        row_num = i + 2
        
        compare_row_cell_counts(row_num, row_a, row_b)
        
        for j, (value_a, value_b) in enumerate(zip(row_a, row_b)):
            col_num = j + 1
            if row_cell_values_differ(row_num, col_num, value_a, value_b):
                diff_count += 1
    
    return diff_count


def compare_row_cell_counts(row_num, row_a, row_b):
    if len(row_a) != len(row_b):
        print(f'Cell counts differ at row {row_num}.')
        print(f'    File "{str(FILE_PATH_A)}" row has {len(row_a)} columns.')
        print(f'    File "{str(FILE_PATH_B)}" row has {len(row_b)} columns.')
        sys.exit(1)


def row_cell_values_differ(row_num, col_num, value_a, value_b):
    
    if col_num <= 13:
        
        if value_a != value_b:
            print(f'Cell values differ at row {row_num}, column {col_num}.')
            print(f'    File "{str(FILE_PATH_A)}" value is {value_a}.')
            print(f'    File "{str(FILE_PATH_B)}" value is {value_b}.')
            return True
            
    elif col_num <= 21:
        
        time_a = parse_datetime(value_a)
        time_b = parse_datetime(value_b)
        diff = abs((time_a - time_b).total_seconds())
        
        # We allow solar event times to differ by up to two seconds for
        # the switch from PyEphem to Skyfield.
        if diff > 2:
            print(
                f'Solar event times differ at row {row_num}, '
                f'column {col_num}.')
            print(f'    File "{str(FILE_PATH_A)}" value is {value_a}.')
            print(f'    File "{str(FILE_PATH_B)}" value is {value_b}.')
            return True
    
    else:
        
        diff = abs(float(value_a) - float(value_b))
        
        if diff >= .2:
            print(f'Cell values differ at row {row_num}, column {col_num}.')
            print(f'    File "{str(FILE_PATH_A)}" value is {value_a}.')
            print(f'    File "{str(FILE_PATH_B)}" value is {value_b}.')
            return True
    
    return False


def parse_datetime(s):
    return datetime.datetime.strptime(s, '%m/%d/%y %H:%M:%S')


if __name__ == '__main__':
    main()
