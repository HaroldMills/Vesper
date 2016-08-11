"""Module that loads and provides access to presets."""


import logging
import os


_YAML_FILE_NAME_EXTENSION = '.yaml'


# Note that even though the `PresetManager` class is typically used as a
# singleton, we make it a class rather than a module to facilitate testing.


class PresetManager:
    
    """Preset manager that loads and provides access to presets."""
    
    
    def __init__(self, preset_types, preset_dir_path):
        
        """
        Initializes this preset manager for the specified preset types
        and preset directory.
        
        :Parameters:
        
            preset_types : set or sequence of `Preset` subclasses
                the types of presets to expect in the preset directory.
                
            preset_dir_path : str
                the path of the preset directory.
                
        :Raises ValueError:
            if the specified directory does not exist.
        """
        
        self._preset_types = _get_preset_types(preset_types)
        """tuple of known preset types."""
        
        self._preset_data = _load_presets(preset_dir_path, self._preset_types)
        """Mapping from preset type names to collections of presets."""
        
        self._preset_dicts = dict(
            (type_name, dict(_flatten_presets(preset_data)))
            for type_name, preset_data in self._preset_data.items())
        """
        Mapping from preset type names to mappings from preset paths to
        presets.
        """
        

    @property
    def preset_types(self):
        
        """
        the preset types of this preset manager, as a tuple of `Preset`
        subclasses.
        
        These are the preset types specified when the manager was initialized,
        sorted by name.
        """
        
        return self._preset_types
    
    
    def get_presets(self, type_name):
        
        """
        Gets all presets of the specified type.
        
        :Parameters:
            type_name : str
                the name of a preset type.
                
        :Returns:
            all presets of the specified type.
            
            The presets are returned in a recursive data structure
            that reflects the directory hierarchy for the specified
            preset type. The data structure has the form:
            
                <preset data> := ((<preset>), {<subdir_name>: <preset data>})
                
            That is, it is a pair comprising a tuple of presets (each
            an instance of a `Preset` subclass) and a dictionary that
            maps string subdirectory names to data structures that in
            turn describe the presets that are in those subdirectories.
            Each tuple of presets is sorted by preset name.
        """
        
        try:
            data = self._preset_data[type_name]
            
        except KeyError:
            return ((), {})
        
        else:
            return _copy_preset_data(data)


    def get_flattened_presets(self, type_name):
        
        """
        Gets all presets of the specified type in a flattened form.
        
        :Parameters:
            type_name : str
                the name of a preset type.
                
        :Returns:
            all presets of the specified type in a flattened form.
            
            The presets are returned as a tuple of (<preset path>, <preset>)
            pairs. Each preset path is a tuple of the path components of
            the accompanying preset, i.e. the names of the directories
            between the directory of the specified preset type and the
            preset itself, followed by the preset name. The presets of
            a directory precede the presets of subdirectories of that
            directory in the returned tuple, and presets are otherwise
            ordered lexicographically by path.
        """
        
        presets = self.get_presets(type_name)
        return _flatten_presets(presets)
    
    
    def get_preset(self, type_name, preset_path):
        
        """
        Gets the specified preset.
        
        :Parameters:
            type_name : str
                the name of the preset type.
                
            preset_path : str or str tuple
               the path of the specified preset.
               
               If the path has just one component, the component can
               be supplied as a string, rather than as a tuple.
               
        :Returns:
            the specified preset, or `None` if there is no such preset.
        """
        
        presets = self._preset_dicts.get(type_name)
        
        if presets is None:
            return None
        else:
            if isinstance(preset_path, str):
                preset_path = (preset_path,)
            return presets.get(preset_path)
        
        
def _get_preset_types(preset_types):
        
    # Sort preset types by name.
    types = list(preset_types)
    types.sort(key=lambda t: t.extension_name)

    # Keep preset types as a tuple.
    return tuple(types)


def _load_presets(preset_dir_path, preset_types):
    
    if not os.path.exists(preset_dir_path):
        message = 'Preset directory "{}" does not exist.'.format(
            preset_dir_path)
        logging.error(message)
        raise ValueError(message)
    
    elif not os.path.isdir(preset_dir_path):
        message = 'Path "{}" exists but is not a preset directory.'.format(
            preset_dir_path)
        logging.error(message)
        raise ValueError(message)
        
    else:
        # have preset directory
        
        preset_types = dict((t.extension_name, t) for t in preset_types)
        preset_data = {}
        
        for _, dir_names, _ in os.walk(preset_dir_path):
            
            for dir_name in dir_names:
                
                dir_path = os.path.join(preset_dir_path, dir_name)
                
                try:
                    preset_type = preset_types[dir_name]
                    
                except KeyError:
                    logging.warning((
                        'Preset manager encountered directory for '
                        'unrecognized preset type "{}" at "{}".').format(
                            dir_name, dir_path))
                
                else:
                    preset_data[dir_name] = \
                        _load_presets_aux(dir_path, preset_type)
                    
            # Stop walk from visiting subdirectories.
            del dir_names[:]
                      
        return preset_data
        

def _load_presets_aux(dir_path, preset_type):
    
    presets = []
    preset_data = {}
    
    for _, subdir_names, file_names in os.walk(dir_path):
        
        for file_name in file_names:
            preset = _load_preset(dir_path, file_name, preset_type)
            if preset is not None:
                presets.append(preset)
                            
        for subdir_name in subdir_names:
            subdir_path = os.path.join(dir_path, subdir_name)
            preset_data[subdir_name] = \
                _load_presets_aux(subdir_path, preset_type)
                
        # Stop walk from visiting subdirectories.
        del subdir_names[:]
        
    presets.sort(key=lambda p: p.name)
    
    return (tuple(presets), preset_data)
        
        
def _load_preset(dir_path, file_name, preset_type):
    file_path = os.path.join(dir_path, file_name)
    preset_name = _get_preset_name(file_name)
    if preset_name is None:
        return None
    else:
        return _parse_preset(file_path, preset_name, preset_type)
            

def _get_preset_name(file_name):
    if file_name.endswith(_YAML_FILE_NAME_EXTENSION):
        return file_name[:-len(_YAML_FILE_NAME_EXTENSION)]
    else:
        return None
    
    
def _parse_preset(file_path, preset_name, preset_type):
    
    try:
        file_ = open(file_path, 'rU')
    except:
        logging.error(
            'Preset manager could not open preset file "{}".'.format(file_path))
        return
    
    try:
        data = file_.read()
    except:
        logging.error(
            'Preset manager could not read preset file "{}".'.format(file_path))
        return
    finally:
        file_.close()
        
    try:
        return preset_type(preset_name, data)
    except ValueError as e:
        logging.error((
            'Preset manager could not parse preset file "{}". '
            'Error message was: {}').format(file_path, str(e)))


def _copy_preset_data(data):
    presets, subdirs_data = data
    return (presets, dict((k, _copy_preset_data(v))
                          for k, v in subdirs_data.items()))


def _flatten_presets(preset_data):
    
    """
    Flattens presets returned by the `PresetManager.get_presets` method.
    
    :Parameters:
        preset_data : tuple of length two
            preset data as returned by the `PresetManager.get_presets` method.
            
    :Returns:
        flattened version of the specified preset data.
        
        The returned value is a tuple of (<preset path>, <preset>)
        pairs, where each preset path is a tuple of string path
        components. For example, the preset path for a preset
        named "P" that is in a subdirectory "D" of the directory
        for the preset's type is `('D', 'P')`.
    """
    
    return _flatten_presets_aux(preset_data, ())
    
    
def _flatten_presets_aux(preset_data, name_tuple):

    presets, subdirs_data = preset_data
    
    # Get top-level (name, preset) pairs.
    top_pairs = tuple((name_tuple + (p.name,), p) for p in presets)
    
    # Get subdirectory (name, preset) pairs
    keys = sorted(subdirs_data.keys())
    subdir_pair_tuples = \
        [_flatten_presets_aux(subdirs_data[k], name_tuple + (k,)) for k in keys]
    subdir_pairs = sum(subdir_pair_tuples, ())
    
    return top_pairs + subdir_pairs
