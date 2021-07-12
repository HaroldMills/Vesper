"""Module that loads and provides access to presets."""


from pathlib import Path
import logging

import vesper.util.file_type_utils as file_type_utils


# Note that even though the `PresetManager` class is typically used as a
# singleton, we make it a class rather than a module to facilitate testing.


# TODO: Consider supporting dynamic registration of preset types.
# A freshly initialized preset manager probably should not know about
# any preset types. Each preset type might be associated with a particular
# plugin that defines it, and it might be added to the preset manager
# when the plugin is loaded. That way, we don't need to register
# preset types defined by plugins that are never loaded.


class PresetManager:
    
    """
    Preset manager that loads and provides access to a collection of presets.
    
    The presets are organized in a preset tree as described in the
    documentation for the `vesper.util.preset.Preset` class. The tree
    structure is determined by a directory hierarchy rooted by a
    *preset directory*, with one directory per preset group and one
    YAML file per preset. The preset directory can have any name.
    The preset directory must contain a *preset type directory* for
    for each preset type, with the same name as the type. In general,
    the names of preset groups are the names of the corresponding
    directories of the preset directory hierarchy. The name of a
    preset file must end with the ".yaml" file name extension, and
    the name of a preset is its file name less that extension.
    """
    
    
    def __init__(self, preset_dir_path, preset_types):
        
        """
        Initializes this preset manager for the specified preset directory
        and preset types.
        
        The preset manager does not load any presets in this method.
        Presets are loaded subsequently as needed by the `get_presets`
        and `get_preset` methods.
        
        :Parameters:
        
            preset_dir_path : path
                the path of the preset directory.
                
            preset_types : set or sequence of `Preset` subclasses
                the types of presets to expect in the preset directory.
                
        :Raises ValueError:
            if the specified directory does not exist.
        """
        
        self._preset_dir_path = _get_preset_dir_path(preset_dir_path)
        self._initialize_preset_types(preset_types)
        self._initialize_presets()
                
        
    def _initialize_preset_types(self, preset_types):
        
        # Sort preset types by name.
        types = sorted(preset_types, key=lambda t: t.extension_name)
    
        self._preset_type_tuple = tuple(types)
        """Tuple of preset types, sorted by name."""
        
        self._preset_type_dict = dict((t.extension_name, t) for t in types)
        """Mapping from preset type name to preset type."""


    def _initialize_presets(self):
        
        self._preset_tuples = dict(
            (t.extension_name, None)
            for t in self._preset_type_tuple)
        """
        Mapping from preset type name to preset tuple.
    
        Preset tuple is `None` for preset types for which presets have not
        yet been loaded. Initially, no presets are loaded.
        """
        
        self._presets = {}
        """Mapping from preset path to preset for loaded presets."""

    
    def _create_unloaded_preset_mapping(self):
        return 


    @property
    def preset_dir_path(self):
        return self._preset_dir_path
    
    
    @property
    def preset_types(self):
        
        """
        The preset types of this preset manager, as a tuple of `Preset`
        subclasses.
        
        These are the preset types specified when the manager was initialized,
        sorted by name.
        """
        
        return self._preset_type_tuple
    
    
    @property
    def _loaded_preset_types(self):
        
        """
        The preset types for which presets are currently loaded.
        
        This property is protected (i.e. its name starts with an underscore)
        since it is intended for use only by unit test code.
        """
        
        return tuple(
            t for t in self.preset_types
            if self._preset_tuples[t.extension_name] is not None)


    @property
    def _loaded_presets(self):
        
        """
        The presets that are currently loaded.
        
        This property is protected (i.e. its name starts with an underscore)
        since it is intended for use only by unit test code.
        """
        
        return tuple(sorted(self._presets.values(), key=_get_preset_sort_key))
    
    
    def unload_presets(self, preset_type_name=None):

        """
        Unloads presets of the specified type, or all presets if the
        specified type is `None`.
        
        Unloading the presets of a preset type forces them to be reloaded
        the next time they are requested.
        """
        
        if preset_type_name is None:
            # unloading all presets
            
            self._initialize_presets()
            
        else:
            # unloading presets of just one type
            
            try:
                self._preset_tuples[preset_type_name] = None
            except KeyError:
                self._handle_unrecognized_preset_type(preset_type_name)
                
            # In the following, we must get a list of dictionary keys
            # and iterate over that instead of iterating directly over
            # `self._presets.keys()` since the loop modifies the
            # dictionary.
            preset_paths = list(self._presets.keys())
            for preset_path in preset_paths:
                if preset_path[0] == preset_type_name:
                    del self._presets[preset_path]
            
        
    def _handle_unrecognized_preset_type(self, preset_type_name):
        raise ValueError(f'Unrecognized preset type "{preset_type_name}".')


    def get_presets(self, preset_type_name):
        
        """
        Gets all presets of the specified type.
        
        :Parameters:
            preset_type_name : str
                the name of a preset type.
                
        :Returns:
            tuple of `Preset` objects.
            
            The presets are sorted first by parent group path and then
            by name.
        """
        
        self._load_presets_if_needed(preset_type_name)
        return self._preset_tuples[preset_type_name]


    def _load_presets_if_needed(self, preset_type_name):
        
        try:
            presets = self._preset_tuples[preset_type_name]
        except KeyError:
            self._handle_unrecognized_preset_type(preset_type_name)
            
        if presets is None:
            self._load_presets(preset_type_name)
        
        
    def _load_presets(self, preset_type_name):
        
        preset_type_dir_path = self.preset_dir_path / preset_type_name
        
        if not preset_type_dir_path.exists():
            presets = ()

        else:
            # preset type directory exists
            
            preset_type = self._preset_type_dict[preset_type_name]
            
            paths = preset_type_dir_path.glob('**/*')
        
            presets = [
                self._load_preset(p, preset_type)
                for p in paths
                if file_type_utils.is_yaml_file(p)]
 
            # Remove `None` items from failed loads.
            presets = [p for p in presets if p is not None]
            
            # Sort.
            presets.sort(key=_get_preset_sort_key)
            
            # Make immutable.
            presets = tuple(presets)
            
        # Remember preset tuple.
        self._preset_tuples[preset_type_name] = presets
        
        # Remember presets by path.
        for p in presets:
            self._presets[p.path] = p

        
    def _load_preset(self, file_path, preset_type):
        
        preset_path = self._get_preset_path(file_path)
        
        try:
            file_ = open(file_path, 'rU')
        except:
            logging.warning(
                f'Preset manager could not open preset file "{file_path}".')
            return None
        
        try:
            data = file_.read()
        except:
            logging.warning(
                f'Preset manager could not read preset file "{file_path}".')
            return None
        finally:
            file_.close()
            
        try:
            return preset_type(preset_path, data)
        except ValueError as e:
            logging.warning(
                f'Preset manager could not construct preset from contents '
                f'of file "{file_path}". Error message was: {str(e)}')
            return None
    
    
    def _get_preset_path(self, file_path):
        relative_path = file_path.relative_to(self.preset_dir_path)
        group_names = relative_path.parts[:-1]
        preset_name = relative_path.stem
        return group_names + (preset_name,)
    

    def get_preset(self, preset_path):
        
        """
        Gets the specified preset.
        
        :Parameters:
        
            preset_path : str tuple
               the path of the specified preset.
               
        :Returns:
            the specified preset, or `None` if there is no such preset.
        """
        
        preset_type_name = preset_path[0]
        self._load_presets_if_needed(preset_type_name)
        return self._presets.get(preset_path)
        
        
def _get_preset_dir_path(dir_path):
    
    if isinstance(dir_path, str):
        dir_path = Path(dir_path)
        
    _check_preset_dir_path(dir_path)
    
    return dir_path
    

def _check_preset_dir_path(dir_path):
    
    if not dir_path.exists():
        raise ValueError(f'Preset directory "{dir_path}" does not exist.')
    
    elif not dir_path.is_dir():
        raise ValueError(
            f'Purported preset directory path "{dir_path}" exists but '
            f'is not a directory.')
        

def _get_preset_sort_key(preset):
    
    """
    Get key for sorting presets.
    
    Sort paths first by parent group path, and then by preset name.
    
    Note that this is not the same as sorting by path alone. For
    example, if we sort paths ('a', 'b') and ('c',) by path alone
    we get:
    
        (('a', 'b'), ('c',))
        
    whereas if we sort them first by parent group path and then by
    preset name, we get:
    
        (('c',), ('a', 'b')).
        
    We prefer the chosen order since it always puts presets that
    are children of a group before children of subgroups of that
    group.
    """
    
    parent_group_path = preset.path[:-1]
    return parent_group_path, preset.name
