"""Operating system utility functions."""
       

import os
import re
import shutil

import vesper.util.yaml_utils as yaml_utils

      
def assert_directory(path):
    
    if not os.path.exists(path):
        message = 'Directory "{:s}" does not exist.'.format(path)
        raise AssertionError(message)
    
    elif not os.path.isdir(path):
        message = 'Path "{:s}" exists but is not a directory.'.format(path)
        raise AssertionError(message)
    

def copy_directory(from_path, to_path):
    
    assert_directory(from_path)
    
    try:
        shutil.copytree(from_path, to_path)
        
    except Exception as e:
        message = (
            f'Could not copy directory "{from_path}" to "{to_path}". '
            f'Error message was: {str(e)}')
        raise OSError(message)
        
        
def create_directory(path):
    
    if os.path.exists(path):
        assert_directory(path)
        
    else:
        
        try:
            os.makedirs(path, exist_ok=True)
            
        except OSError as e:
            message = (
                'Could not create directory "{:s}". Error message was: '
                '{:s}').format(path, str(e))
            raise OSError(message)


def create_parent_directory(path):
    dir_path = os.path.dirname(path)
    create_directory(dir_path)
    
    
def clear_directory(path):
    
    """
    Deletes all files and subdirectories from the specified directory.
    
    The directory itself is not deleted.
    """
    
    
    assert_directory(path)
    
    for dirPath, subdirNames, fileNames in os.walk(path):
        
        for fileName in fileNames:
            filePath = os.path.join(dirPath, fileName)
            delete_file(filePath)
            
        for subdirName in subdirNames:
            subdirPath = os.path.join(dirPath, subdirName)
            delete_directory(subdirPath)
            
         
def delete_directory(path):
    
    try:
        shutil.rmtree(path)
    except OSError as e:
        message = (
            'Could not delete directory "{:s}". Error message was: '
            '{:s}').format(path, str(e))
        raise OSError(message)


def assert_file(path):
    
    if not os.path.exists(path):
        message = 'File "{:s}" does not exist.'.format(path)
        raise AssertionError(message)
    
    elif not os.path.isfile(path):
        message = 'Path "{:s}" exists but is not a file.'.format(path)
        raise AssertionError(message)
    
    
def create_file(path):
    
    try:
        file_ = open(path, 'w')
        
    except IOError as e:
        raise OSError((
            'Could not create file "{:s}". Error message was: '
            '{:s}').format(str(e)))
        
    else:
        file_.close()
        
        
def rename_file(from_path, to_path):
    
    try:
        os.rename(from_path, to_path)
        
    except OSError as e:
        message = (
            'Could not rename file "{:s}". Error message was: '
            '{:s}').format(from_path, str(e))
        raise OSError(message)


def delete_file(path, check_existence=True):
    
    if check_existence and not os.path.exists(path):
        return
    
    try:
        os.remove(path)
        
    except OSError as e:
        message = (
            'Could not delete file "{:s}". Error message was: '
            '{:s}').format(path, str(e))
        raise OSError(message)
            


def delete_files(dir_path, pattern=None, recursive=False):
    
    def visitor(path):
        delete_file(path, check_existence=False)
        
    visit_files(dir_path, visitor, pattern, recursive)
            
    
def visit_files(dir_path, visitor, pattern=None, recursive=False):
    
    if pattern is not None:
        regexp = re.compile(pattern)
    
    for _, subdir_names, file_names in os.walk(dir_path):
        
        for file_name in file_names:
            if pattern is None or regexp.match(file_name):
                file_path = os.path.join(dir_path, file_name)
                visitor(file_path)
                
        if not recursive:
            
            # stop walk from visiting subdirectories
            del subdir_names[:]

    
def list_files(dir_path, pattern=None, recursive=False):
    visitor = _FilePathAccumulator()
    visit_files(dir_path, visitor, pattern, recursive)
    return visitor.file_paths


class _FilePathAccumulator:
    
    def __init__(self):
        self.file_paths = []
        
    def __call__(self, file_path):
        self.file_paths.append(file_path)


def copy_file(from_path, to_path):
    
    try:
        shutil.copy(from_path, to_path)
        
    except (OSError, IOError) as e:
        message = (
            'Could not copy file "{:s}" to "{:s}". Error message was: '
            '{:s}').format(from_path, to_path, str(e))
        raise OSError(message)
    
    
def read_file(path):
    
    path = str(path)
    
    try:
        with open(path, 'r') as file_:
            return file_.read()
        
    except Exception as e:
        raise OSError(
            'Could not read file "{:s}". Error message was: {:s}'.format(
                path, str(e)))


def write_file(path, contents, mode='w'):
    
    try:
        with open(path, mode) as file_:
            return file_.write(contents)
        
    except Exception as e:
        raise OSError(
            'Could not write file "{:s}". Error message was: {:s}'.format(
                path, str(e)))


def read_yaml_file(path):

    contents = read_file(path)
    
    try:
        return yaml_utils.load(contents)
    
    except Exception as e:
        raise OSError(
            'Could not load YAML file "{:s}". Error message was: {:s}'.format(
                path, str(e)))
