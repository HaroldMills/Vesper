from __future__ import print_function
import os
import sys


def _main():
    
    (dir_path_a, dir_path_b) = _processArgs()
    
    paths_a = _get_file_paths(dir_path_a)
    paths_b = _get_file_paths(dir_path_b)
    
    _compare_file_paths(paths_a, paths_b, dir_path_a, dir_path_b)
    
    
            
def _processArgs():
    
    program_name = os.path.basename(sys.argv[0])
    
    if len(sys.argv) < 3:
        print('Usage: python {:s} <dir path A> <dir path B>'.format(
            program_name))
        sys.exit(1)
        
    return (sys.argv[1], sys.argv[2])


def _get_file_paths(directory_path):

    print('Getting file paths in "{:s}"...'.format(directory_path))
    
    rel_path_start_index = len(directory_path) + 1
    
    paths = set()
    
    for (dir_path, dir_names, file_names) in os.walk(directory_path):
        
        if len(dir_names) == 0:
            # directory has no subdirectories
            
            for file_name in file_names:
                
                path = os.path.join(dir_path, file_name)
                paths.add(path[rel_path_start_index:])
                
    print('    {:d} files found.'.format(len(paths)))

    return paths
                

def _compare_file_paths(paths_a, paths_b, dir_path_a, dir_path_b):
    _aux(paths_a, paths_b, dir_path_a, dir_path_b)
    _aux(paths_b, paths_a, dir_path_b, dir_path_a)
    
    
def _aux(paths_a, paths_b, dir_path_a, dir_path_b):
    
    diff = list(paths_a - paths_b)
    diff.sort()
    
    if len(diff) != 0:
        print('Files in "{:s}" but not in "{:s}":'.format(
                  dir_path_a, dir_path_b))
        for path in diff:
            print('    ' + path)
        
    
if __name__ == '__main__':
    _main()
