"""File type utility functions."""


_WAVE_FILE_NAME_EXTENSIONS = ['.wav', '.WAV']
_YAML_FILE_NAME_EXTENSIONS = ['.yaml', '.YAML']


def is_wave_file(path, include_dot_files=False):
    return is_file_of_type(path, _WAVE_FILE_NAME_EXTENSIONS, include_dot_files)


def is_yaml_file(path, include_dot_files=False):
    return is_file_of_type(path, _YAML_FILE_NAME_EXTENSIONS, include_dot_files)


def is_file_of_type(path, file_name_extensions, include_dot_files=False):
    
    if not path.exists():
        raise ValueError(f'File "{path}" does not exist.')
    
    if not path.is_file():
        return False
    
    file_name = path.name
    
    if not include_dot_files and file_name.startswith('.'):
        return False
    
    for extension in file_name_extensions:
        if file_name.endswith(extension):
            return True
        
    # If we get here, the file name does not end in any recognized extension.
    return False
