"""
Utility functions pertaining to object UI names.

Various archive objects like stations, devices, detectors, etc. are
referred to by name in the Vesper client user interface. Names for the
objects are specified in the archive, but those names are sometimes
not the names we would like to display in the user interface, for
example because they are too long. Thus Vesper supports the specification
of object *UI names* via the `ui_names` preference that differ from the
objects' *archive names*. This module contains functions for getting
lists of object UI names, and for translating between UI names and
archive names.
"""


from vesper.singletons import preference_manager
import vesper.django.app.model_utils as model_utils


def get_processor_choices(processor_type):
    
    """
    Gets HTML select choices for the non-hidden processors of the specified
    type.
    
    Parameters
    ----------
    processor_type : str
        the type of the processors for which to get choices.
        
    Returns
    -------
    List of processor choices, each an (archive_name, ui_name) pair.
    """
    
    processors = model_utils.get_processors(processor_type)
    archive_names = [p.name for p in processors]
    return _get_choices(archive_names, 'processors')


def _get_choices(archive_names, ui_names_key):
    
    ui_names_dict = _get_ui_names_dict(ui_names_key)
    hidden_names = _get_hidden_names(ui_names_key)
    
    choices = []
    
    for name in archive_names:
        
        if name not in hidden_names:
            
            ui_name = ui_names_dict.get(name, name)
            
            if ui_name not in hidden_names:
                # object is not hidden
                
                choices.append((name, ui_name))
            
    # Sort choices by UI name.
    choices.sort(key=lambda c: c[1])
    
    return choices

    
def _get_ui_names_dict(ui_names_key):
    preferences = preference_manager.instance.preferences
    return preferences.get('ui_names', {}).get(ui_names_key, {})


def _get_hidden_names(ui_names_key):
    preferences = preference_manager.instance.preferences
    names = preferences.get('hidden_objects', {}).get(ui_names_key, [])
    return frozenset(names)


def get_processor_ui_name(name):
    
    """
    Gets the UI name of the specified processor.
    
    Parameters
    ----------
    name : str
        The name of a processor, either an archive name or a UI name.
        
    Returns
    -------
    The UI name of the specified processor. If the "processors" item of
    the UI names preference does not specify a UI name for the processor,
    its UI name is `name`.
    
    Raises
    ------
    KeyError
        if the specified name is not a processor archive name or UI name.
    """
    
    return _get_object_ui_name(name, 'processors', _check_processor_name)


def _get_object_ui_name(name, ui_names_key, archive_name_checker):
    
    ui_names_dict = _get_ui_names_dict(ui_names_key)
    
    try:
        return ui_names_dict[name]
        
    except KeyError:
        # `name` is not a key in `ui_names_dict`
        
        if name not in ui_names_dict.values():
            # `name` is not a UI name
            
            # Check that `name` is an archive name.
            archive_name_checker(name)
        
        return name
    
    
def _check_processor_name(name):
    processors = model_utils.get_processors()
    processor_names = [p.name for p in processors]
    if name not in processor_names:
        raise ValueError('Unrecognized processor name "{}".'.format(name))
    

def get_processor_archive_name(name):
    
    """
    Gets the archive name of the specified processor.
    
    Parameters
    ----------
    name : str
        The name of a processor, either a UI name or an archive name.
        
    Returns
    -------
    The archive name of the specified processor.
    
    Raises
    ------
    KeyError
        if the specified name is not a processor UI name or archive name.
    """
    
    return _get_object_archive_name(name, 'processors', _check_processor_name)


def _get_object_archive_name(name, ui_names_key, archive_name_checker):
    
    ui_names_dict = _get_ui_names_dict(ui_names_key)
    archive_names_dict = _invert(ui_names_dict)
    
    try:
        return archive_names_dict[name]
    
    except KeyError:
        # `name` is not a UI name
                
        # Check that `name` is an archive name
        archive_name_checker(name)
        
        return name
        
    
def _invert(d):
    return dict((v, k) for k, v in d.items() if v is not None)
