"""Module containing `PresetManager` class."""


from __future__ import print_function

import os
import sys

from vesper.util.classification_commands_preset import \
    ClassificationCommandsPreset
import vesper.util.vesper_path_utils as vesper_path_utils


# TODO: Do away with `PresetManager` class, since we appear to need only
# one preset manager. Make preset types and data module attributes and
# convert methods to module-level functions.


_PRESETS_DIR_NAME = 'Presets'
_PRESET_TYPES = {ClassificationCommandsPreset}
_TEXT_FILE_NAME_EXTENSION = '.txt'


class PresetManager(object):
    
    """Preset manager that loads and provides access to presets."""
    
    
    @staticmethod
    def flatten_preset_data(preset_data):
        
        """
        Flattens preset data returned by the `get_preset_data` method.
        
        :Parameters:
            preset_data : tuple of length two
                preset data as returned by the `get_preset_data` method.
                
        :Returns:
            flattened version of the specified preset data.
            
            The returned value is a tuple of (<preset path>, <preset>)
            pairs, where each preset path is a tuple of string path
            components. For example, the preset path for a preset
            named "P" that is within subdirectory "D" of the
            directory for the preset's type is `('D', 'P')`.
        """
        
        return PresetManager._flatten_preset_data(preset_data, ())
        
        
    @staticmethod
    def _flatten_preset_data(preset_data, name_tuple):

        presets, subdirs_data = preset_data
        
        # Get top-level (name, preset) pairs.
        top_pairs = tuple((name_tuple + (p.name,), p) for p in presets)
        
        # Get subdirectory (name, preset) pairs
        keys = subdirs_data.keys()
        keys.sort()
        f = PresetManager._flatten_preset_data
        subdir_pair_tuples = \
            [f(subdirs_data[k], name_tuple + (k,)) for k in keys]
        subdir_pairs = sum(subdir_pair_tuples, ())
        
        return top_pairs + subdir_pairs


    def __init__(self, presets_dir_path, preset_types):
        
        """
        Initializes this preset manager for the specified presets
        directory and preset types.
        
        This method
        
        :Parameters:
        
            presets_dir_path : str
                the path of the presets directory.
                
            preset_types : set or sequence of `Preset` subclasses
                the types of presets to expect in the presets directory.
                
        :Raises ValueError:
            if the specified directory does not exist.
        """
        
        # TODO: Should we raise exceptions or log errors here?
        if not os.path.exists(presets_dir_path):
            f = 'Presets directory "{:s}" does not exist.'
            raise ValueError(f.format(presets_dir_path))
        
        elif not os.path.isdir(presets_dir_path):
            f = 'Path "{:s}" exists but is not a presets directory.'
            raise ValueError(f.format(presets_dir_path))
            
        # Sort preset types by name.
        types = list(preset_types)
        types.sort(key=lambda t: t.type_name)

        self._preset_types = tuple(types)
        self._preset_data = _load_presets(presets_dir_path, types)
    
    
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
            that reflects how the presets are stored in the persistent
            store. The data structure has the form:
            
                <preset data> := ((<preset>), {<subdir_name>: <preset data>})
                
            That is, it is a pair comprising a tuple of presets (each
            an instance of a `Preset` subclass) and a dictionary that
            maps string subdirectory names to data structures that in
            turn describe the presets that are in those subdirectories.
            Each tuple of presets is sorted by preset name.
            
        :Raises ValueError:
            if the specified preset type is not recognized.
        """
        
        try:
            return _copy_preset_data(self._preset_data[type_name])
        
        except KeyError:
            f = ('Presets of unrecognized type "{:s}" requested from '
                 'preset manager.')
            _log_error(f.format(type_name))
            return ((), {})


def _load_presets(presets_dir_path, preset_types):
    
    preset_types = dict((t.type_name, t) for t in preset_types)
    preset_data = {}
    
    for _, dir_names, _ in os.walk(presets_dir_path):
        
        for dir_name in dir_names:
            
            dir_path = os.path.join(presets_dir_path, dir_name)
            
            try:
                preset_type = preset_types[dir_name]
                
            except KeyError:
                f = ('Preset manager encountered directory for unrecognized '
                     'preset type "{:s}" at "{:s}".')
                _log_warning(f.format(dir_name, dir_path))
            
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
            
            file_path = os.path.join(dir_path, file_name)
            preset_name = _get_preset_name(file_name)
            preset = _parse_preset(file_path, preset_name, preset_type)
            
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
        
        
def _get_preset_name(file_name):
    if file_name.endswith(_TEXT_FILE_NAME_EXTENSION):
        return file_name[:-len(_TEXT_FILE_NAME_EXTENSION)]
    else:
        return file_name
    
    
def _parse_preset(file_path, preset_name, preset_type):
    
    try:
        file_ = open(file_path, 'rU')
    except:
        f = 'Preset manager could not open preset file "{:s}".'
        _log_error(f.format(file_path))
    
    try:
        data = file_.read()
    except:
        f = 'Preset manager could not read preset file "{:s}".'
        _log_error(f.format(file_path))
    finally:
        file_.close()
        
    try:
        return preset_type(preset_name, data)
    except ValueError as e:
        f = 'Preset manager could not parse preset file "{:s}": {:s}'
        _log_error(f.format(file_path, str(e)))
        
        
def _log_warning(message):
    print('Warning: ' + message, file=sys.stderr)
    
    
def _log_error(message):
    print('Error: ' + message, file=sys.stderr)
    
    
def _copy_preset_data(data):
    presets, subdirs_data = data
    return (presets, dict((k, _copy_preset_data(v))
                          for k, v in subdirs_data.iteritems()))


def _create_preset_manager():
    app_data_dir_path = vesper_path_utils.get_path('App Data')
    presets_dir_path = os.path.join(app_data_dir_path, _PRESETS_DIR_NAME)
    return PresetManager(presets_dir_path, _PRESET_TYPES)
    
    
preset_manager = _create_preset_manager()
