"""Module containing `Archive` class."""


from collections import defaultdict

from vesper.django.app.models import Processor


class Archive:
    
    """
    Vesper archive.
    
    The methods of this class provide access to cached Vesper archive
    objects of several types. They also support object UI names and
    object hiding, which are specified via preferences and not
    supported by the archive database.
    """
    
    
    def __init__(self):
        
        # This is here instead of at the top of this module to avoid
        # a circular import.
        from vesper.singletons import preference_manager
        
        preferences = preference_manager.instance.preferences
        self._ui_names = preferences.get('ui_names', {})
        self._hidden_objects = preferences.get('hidden_objects', {})
        
        self._processors_by_type = None
        """
        Mapping from processor types to lists of processors ordered by name.
        """
        
        self._visible_processors_by_type = None
        """
        Mapping from processor types to lists of visible processors ordered
        by name.
        """
        
        self._processors_by_name = None
        """
        Mapping from processor names to processors.
        
        The mapping keys include both processor archive names and
        processor UI names.
        """
        
        self._processor_ui_names = None
        """Mapping from processor archive names to processor UI names."""
    
        self._processor_cache_dirty = True
        
    
    def get_processors(self, processor_type):
        self._refresh_processor_cache_if_needed()
        return self._processors_by_type.get(processor_type, [])
    
    
    def _refresh_processor_cache_if_needed(self):
        if self._processor_cache_dirty:
            self.refresh_processor_cache()
            
            
    def refresh_processor_cache(self):
            
        ui_names_pref = self._ui_names.get('processors', {})
        
        by_type = defaultdict(list)
        by_name = {}
        ui_names = {}
        
        # We iterate over processors in order of name so that processor
        # lists in the `by_type` mappings will be ordered by name.
        for p in Processor.objects.all().order_by('name'):
        
            by_type[p.type].append(p)
            
            archive_name = p.name
            ui_name = ui_names_pref.get(archive_name, archive_name)
            
            by_name[archive_name] = p
            if ui_name != archive_name:
                by_name[ui_name] = p
            
            ui_names[archive_name] = ui_name
            
        self._processors_by_type = by_type
        self._processors_by_name = by_name
        self._processor_ui_names = ui_names
        
        # Get visible processors by type.
        hidden_names = frozenset(self._hidden_objects.get('processors', []))
        self._visible_processors_by_type = \
            dict(
                (k, self._get_visible_processors(v, hidden_names))
                for k, v in self._processors_by_type.items())
            
        self._processor_cache_dirty = False
        
            
    def _get_visible_processors(self, processors, hidden_names):
        return [
            p for p in processors
            if p.name not in hidden_names and
            self._processor_ui_names[p.name] not in hidden_names]
        
        
    def get_visible_processors(self, processor_type):
        self._refresh_processor_cache_if_needed()
        return self._visible_processors_by_type.get(processor_type, [])
        
        
    def get_processor(self, processor_name):
        self._refresh_processor_cache_if_needed()
        try:
            return self._processors_by_name[processor_name]
        except KeyError:
            _handle_unrecognized_processor_name(processor_name)


    def get_processor_ui_name(self, processor):
        self._refresh_processor_cache_if_needed()
        try:
            return self._processor_ui_names[processor.name]
        except KeyError:
            _handle_unrecognized_processor_name(processor.name)
        
        
def _handle_unrecognized_processor_name(name):
    raise ValueError(
        'Archive cache does not recognize processor name "{}".'.format(name))
