import os.path
import timeit

import numpy as np


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\File Write Test'
_RESULTS_FILE_NAME = 'Results.csv'
_TOTAL_SIZE = int(6e9)
_FILE_SIZE = 20000
_TIMING_BLOCK_SIZE = 100
_DATA = np.zeros(_FILE_SIZE, dtype='byte')


def _time_file_writes(start_index):
    for i in range(_TIMING_BLOCK_SIZE):
        file_name = '{:06d}'.format(start_index + i)
        file_path = os.path.join(_DIR_PATH, file_name)
        _DATA.tofile(file_path)
    
    
def _main():
    
    num_files = _TOTAL_SIZE // _FILE_SIZE
    num_timings = num_files // _TIMING_BLOCK_SIZE
    
    start_index = 0
    results = []
    for i in range(num_timings):
        stmt = '_time_file_writes({})'.format(start_index)
        setup = 'from __main__ import _time_file_writes'
        time = timeit.timeit(stmt=stmt, setup=setup, number=1)
        results.append((i, time))
        print('{} of {}: {}'.format(i, num_timings, time))
        start_index += _TIMING_BLOCK_SIZE
        
    _write_results_file(results)
    
    
def _write_results_file(results):
    text = ''.join('{},{}\n'.format(i, time) for i, time in results)
    file_path = os.path.join(_DIR_PATH, _RESULTS_FILE_NAME)
    with open(file_path, 'w') as file_:
        file_.write(text)
        
        
if __name__ == '__main__':
    _main()
    