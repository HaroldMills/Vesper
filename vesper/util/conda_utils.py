"""Utility functions relating to Conda environments."""


from pathlib import Path
import os
import subprocess
import sys


class CondaUtilsError(Exception):
    pass


def run_python_script(module_name, args=None, environment_name=None):
    
    """Runs a Python script in a Conda environment."""
    
    if args is None:
        args = []
    
    interpreter_path, env_vars = _get_run_info(environment_name)
    
    # Get command to run.
    command = [str(interpreter_path), '-m', module_name] + list(args)
    
    try:
        
        # Run the child process and wait to it to exit.
        results = subprocess.run(
            
            command,
            
            # Use these for Python <3.7.
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            
            # Use these for Python >=3.7.
            # text=True,
            # capture_output=True,
            
            env=env_vars)
    
    except Exception as e:
        raise CondaUtilsError(
            f'Attempt to run child process raised an exception. '
            f'Error message was: {str(e)}')
    
    return results


def _get_run_info(env_name):
    
    current_interpreter_path = Path(sys.executable)
    
    envs_dir_path, current_env_name, relative_interpreter_path = \
        _split_interpreter_path(current_interpreter_path)
    
    if env_name is None or env_name == current_env_name:
        # will run in current Conda environment
        
        return current_interpreter_path, None
    
    else:
        # will run in Conda environment other than current one
        
        _check_env_dir(envs_dir_path, env_name)
        
        # Get path of Python interpreter to run.
        interpreter_path = envs_dir_path / env_name / relative_interpreter_path
        
        # Get environment variables for run.
        env_vars = _get_env_vars(env_name, current_env_name, envs_dir_path)
        
        return interpreter_path, env_vars


def _split_interpreter_path(path):
    
    parts = path.parts
    
    # Get index in path parts of environment directory name, assuming
    # directory is child of Miniconda or Anaconda "envs" directory.
    i = len(parts)
    while i > 0 and parts[i - 1] != 'envs':
        i -= 1
    
    if i == 0:
        raise ValueError(
            f'Python interpreter path "{path}" does not include expected '
            f'Miniconda or Anaconda "envs" directory.')
    
    # Make sure Python interpreter executable name contains no version number.
    executable_name = _generify_interpreter_executable_name(parts[-1])
    parts = parts[:-1] + (executable_name,)
    
    envs_dir_path = Path(*parts[:i])
    env_name = parts[i]
    relative_interpreter_path = Path(*parts[i + 1:])
    
    return envs_dir_path, env_name, relative_interpreter_path


def _generify_interpreter_executable_name(file_name):
    
    """
    Generifies the file name of a Python interpreter executable.
    
    The name of the Python interpreter executable that we get from
    `sys.executable` sometimes includes version information, e.g.
    "python3.9". This function returns a corresponding generic
    interpreter executable name that includes no version information,
    so that it can be used to invoke the Python interpreter of any
    Conda environment, regardless of version.
    """
    
    if file_name.endswith('.exe'):
        return 'python.exe'
    else:
        return 'python'


def _check_env_dir(envs_dir_path, env_name):
    env_dir_path = envs_dir_path / env_name
    if not env_dir_path.exists():
        raise CondaUtilsError(f'Conda environment "{env_name}" not found.')


def _get_env_vars(env_name, current_env_name, envs_dir_path):
    
    env_vars = dict(os.environ)
    
    pythonpath = env_vars.get('PYTHONPATH')
    
    if pythonpath is None:
        # no PYTHONPATH environment variable
        
        # Use existing environment variables.
        return None
    
    else:
        # have PYTHONPATH environment variable
        
        # Change PYTHONPATH for new Conda environment.
        current_env_dir_path = envs_dir_path / current_env_name
        new_env_dir_path = envs_dir_path / env_name
        env_vars['PYTHONPATH'] = _alter_pythonpath(
            pythonpath, current_env_dir_path, new_env_dir_path)
        
        return env_vars


'''
Example PYTHONPATH:

/Users/harold/Documents/Code/Python/Vesper Auxiliary Server Test
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8/lib-dynload
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8/site-packages
'''


def _alter_pythonpath(pythonpath, old_env_dir_path, new_env_dir_path):
    
    """Alters the PYTHONPATH of one Conda environment for another."""
    
    paths = pythonpath.split(':')
    
    paths = [
        _alter_pythonpath_aux(p, old_env_dir_path, new_env_dir_path)
        for p in paths]
    
    return ':'.join(paths)


def _alter_pythonpath_aux(path, old_env_dir_path, new_env_dir_path):
    
    path = Path(path) 
    
    try:
        path = reparent(path, old_env_dir_path, new_env_dir_path)
        
    except ValueError:
        # `path` is not a subpath of `old_env_dir_path`
        
        # This is fine. Some PYTHONPATH elements may be subpaths
        # of the Conda environment directory, while others may not.
        # If not, we just leave the element as is.
        pass
    
    return str(path)


def reparent(path, old_parent, new_parent):
    relative_path = path.relative_to(old_parent)
    return new_parent / relative_path
