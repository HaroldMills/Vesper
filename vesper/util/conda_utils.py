"""Script that runs BirdVoxDetect in its own environment."""


from pathlib import Path
import os
import subprocess
import sys


'''
Example PYTHONPATH:

/Users/harold/Documents/Code/Python/Vesper Auxiliary Server Test
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8/lib-dynload
/Users/harold/miniconda3/envs/vesper-dev/lib/python3.8/site-packages
'''


class CondaUtilsError(Exception):
    pass


def run_python_script(module_name, args=None, environment_name=None):
    
    """Runs a Python module in a Conda environment."""
    
    if args is None:
        args = []
        
    # Get path of Conda environment in which to run module.
    env_dir_path = _get_env_dir_path(environment_name)
    
    # Get path of Python interpreter in Conda environment.
    interpreter_path = _get_python_interpreter_path(env_dir_path)
    
    # Get command to run.
    command = [interpreter_path, '-m', module_name] + list(args)
    
    # Get environment variables for child process.
    env_vars = _get_env_vars(env_dir_path)
    
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


def _get_env_dir_path(env_name):
    
    current_env_dir_path = _get_current_env_dir_path()
    
    if env_name is None:
        # want current environment dir path
        return current_env_dir_path
    
    else:
        # want other environment dir path
        
        envs_dir_path = current_env_dir_path.parent
        return envs_dir_path / env_name


def _get_current_env_dir_path():
    interpreter_path = Path(sys.executable)
    return interpreter_path.parent.parent


def _get_python_interpreter_path(env_path):
    return env_path / 'bin' / 'python'


def _get_env_vars(new_env_dir_path):
    
    current_env_dir_path = _get_current_env_dir_path()
    
    if new_env_dir_path == current_env_dir_path:
        return None
    
    else:
        # new Conda environment will differ from current one
        
        env_vars = dict(os.environ)
        
        pythonpath = env_vars.get('PYTHONPATH')
        
        if pythonpath is None:
            return None
        
        else:
            # have PYTHONPATH environment variable
            
            # Change PYTHONPATH for new Conda environment.
            env_vars['PYTHONPATH'] = _alter_pythonpath(
                pythonpath, current_env_dir_path, new_env_dir_path)
                
            return env_vars


def _alter_pythonpath(pythonpath, old_env_dir_path, new_env_dir_path):
    
    """Alters the PYTHONPATH of one Conda environment for another."""
    
    paths = pythonpath.split(':')
    
    # for path in paths:
    #     print(path)
    
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
