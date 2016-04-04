"""Summarizes `astro_utils` test results."""


import os

import numpy as np
import pandas as pd


_DATA_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\USNO Tables'
# _DATA_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/USNO Tables'
_CSV_FILE_NAME = 'Rise Set Data.csv'


def _main():
    
    csv_file_path = os.path.join(_DATA_DIR_PATH, _CSV_FILE_NAME)
    df = pd.read_csv(csv_file_path)
    
    r = _get_diff_data(df, 'Risings')
    s = _get_diff_data(df, 'Settings')
    
    keys = (
        'Event Type', 'Number of Events', 'Percent Diffs 0',
        'Percent Diffs 1', 'Percent Diffs 2 or More')

    items = [_item(keys[i], i, r, s) for i in range(5)]
    
    df = pd.DataFrame.from_items(items)
    
    print(df)
    
    
def _get_diff_data(df, name):
    column_names = _get_diff_column_names(name)
    d = df[column_names].sum()
    n = d.sum()
    counts = np.array([d[2], d[1] + d[3], d[0] + d[4]])
    percentages = 100. * counts / float(n)
    return [name[:-1], n] + list(percentages)
    
    
def _get_diff_column_names(name):
    return [name + ' Diff ' + str(d) for d in range(-2, 3)]


def _item(name, index, r, s):
    return (name, (r[index], s[index]))


if __name__ == '__main__':
    _main()
