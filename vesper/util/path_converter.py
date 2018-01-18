"""Module containing class `PathConverter`."""


class PathConverter:

    """
    Converts file system paths between relative and absolute forms.
    
    The conversions are performed relative to a sequence of one or more
    *root directory paths*.
    
    Parameters
    ----------
    root_dir_paths: sequence of pathlib.Path objects
        The root directory paths of the converter.
        Each root directory path must be absolute, and there must be
        at least one root directory path.
        
    Attributes
    ----------
    root_dir_paths: tuple of pathlib.Path objects
        The root directory paths of the converter.
        Each root directory path is absolute, and there is at least one.
        
    Raises
    ------
    ValueError
        if any of the specified root directory paths is not absolute,
        or if no paths are specified.
    
    """
    
    
    def __init__(self, root_dir_paths):
        
        self._check_root_dir_paths(root_dir_paths)
        
        self._root_dir_paths = tuple(root_dir_paths)
        self._cache = {}

        
    def _check_root_dir_paths(self, paths):
        
        if len(paths) == 0:
            raise ValueError('No root directory paths specified.')
        
        for path in paths:
            if not path.is_absolute():
                raise ValueError('Path "{}" is not absolute.'.format(path))
        
        
    @property
    def root_dir_paths(self):
        return self._root_dir_paths
    
    
    def absolutize(self, path):
        
        """
        Finds the absolute version of an relative path.
        
        This method looks for the specified relative path within the
        root directories of this converter, and returns the absolute
        version of the path if found. The root directories are searched
        in order.
        
        Parameters
        ----------
        path: pathlib.Path
            The relative path for which to find the absolute path.
            
        Returns
        -------
        pathlib.Path
            The absolute version of the specified relative path.
            
        Raises
        ------
        ValueError
            If the specified path is already absolute, or if nothing
            is found at it.
        """
        
        if path.is_absolute():
            raise ValueError('Path "{}" is not relative.'.format(path))
        
        else:
            # `path` is relative
            
            try:
                return self._cache[path]
            
            except KeyError:
                
                for dir_path in self.root_dir_paths:
                
                    abs_path = dir_path / path
                    
                    if abs_path.exists():
                        self._cache[path] = abs_path
                        return abs_path
                
            # If we get here, the specified path does not exist inside
            # any of this converter's root directories.
            raise ValueError('Nothing found at path "{}".'.format(path))
        
    
    def relativize(self, path):
        
        """
        Finds the relative version of an absolute path.
        
        This method relativizes the specified absolute path with
        respect to the root directory paths of this converter.
        The path is converted relative to the first root directory
        path that is a prefix of it.
        
        Note that this method does not require that any thing exist
        at the specified path, only that it include one of the root
        directory paths of this converter as a prefix.
        
        Parameters
        ----------
        path: pathlib.Path
            The absolute path for which to find the relative path.
        
        Returns
        -------
        root_dir_path: pathlib.Path
            The path of the first root directory whose path is a prefix
            of `path`.
        rel_path: pathlib.Path
            The path relative to `root_dir_path` of `path`.
            
        Raises
        ------
        ValueError
            If the specified path is already relative, or does not include
            any root directory path as a prefix.
        """
        
        if path.is_absolute():
            
            for dir_path in self.root_dir_paths:
                
                try:
                    rel_path = path.relative_to(dir_path)
                    
                except ValueError:
                    continue
                
                else:
                    return dir_path, rel_path
            
            # If we get here, the specified path is not inside any of this
            # converter's root directories.
            paths = ['    {}'.format(p) for p in self.root_dir_paths]
            raise ValueError(
                ('Path "{}" could not be relativized, since it does not '
                 'begin with any of the following prefixes:\n').format(path) +
                '\n'.join(paths))
            
        else:
            # `path` is relative
            
            raise ValueError('Path "{}" is not absolute.'.format(path))
