"""Module containing `Archive` class."""


from collections import defaultdict

from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Processor, TagInfo)
from vesper.singleton.preference_manager import preference_manager
        
import vesper.util.yaml_utils as yaml_utils


# TODO: Move code that modifies lists of items for presentation in
# the UI to the client? This includes, for example, wildcard additions
# and UI name substitutions. The basic idea is to move UI concerns to
# the client.


_NOT_APPLICABLE = '-----'
_STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR = '.'
_STRING_ANNOTATION_VALUE_WILDCARD = '*'
_STRING_ANNOTATION_VALUE_NONE = '-None-'


class Archive:
    
    """
    Vesper archive.
    
    The methods of this class provide access to cached Vesper archive
    objects of several types. They also support object UI names and
    object hiding, which are specified via preferences and not
    supported by the archive database.
    """
    
    
    def __init__(self):
        
        preferences = preference_manager.preferences
        self._ui_names = preferences.get('ui_names', {})
        
        self._hidden_objects = _get_hidden_objects(preferences)
        
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
    
        self._string_anno_archive_value_tuples = None
        """
        Mapping from string annotation names to tuples of string annotation
        archive values.
        
        The annotation values of each tuple are ordered lexicographically.
        The mapping includes an item for every known string annotation.
        """
        
        self._string_anno_ui_values = None
        """
        Mapping from string annotation names to mappings from annotation
        archive and UI values to annotation UI values.
        
        The mapping includes an item for every known string annotation.
        """
        
        self._string_anno_archive_values = None
        """
        Mapping from string annotation names to mappings from annotation
        archive and UI values to annotation archive values.
        
        The mapping includes an item for every known string annotation.
        """
        
        self._visible_string_anno_ui_values = None
        """
        Mapping from string annotation names to tuples of visible string
        annotation UI values.
        
        The annotation values of each tuple are ordered lexicographically.
        The mapping includes an item for every known string annotation.
        """
        
        self._visible_string_anno_ui_value_specs = None
        """
        Mapping from string annotation names to tuples of visible string
        annotation UI value specs.
        
        Except for three special specs at the beginning of each tuple
        (unless one or more of the three are hidden), the specs of each
        tuple are ordered lexicographically. The special specs are for
        no value, any or no value, and any value, respectively.
        """

        self._processor_cache_dirty = True
        self._string_anno_values_cache_dirty = True
        
    
    @property
    def NOT_APPLICABLE(self):
        return _NOT_APPLICABLE
    
    
    @property
    def STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR(self):
        return _STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR
    
    
    @property
    def STRING_ANNOTATION_VALUE_WILDCARD(self):
        return _STRING_ANNOTATION_VALUE_WILDCARD
    
    
    @property
    def STRING_ANNOTATION_VALUE_ANY(self):
        return _STRING_ANNOTATION_VALUE_WILDCARD
    
    
    @property
    def STRING_ANNOTATION_VALUE_NONE(self):
        return _STRING_ANNOTATION_VALUE_NONE
    
    
    def get_processors_of_type(self, processor_type):
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
        
        
    def get_visible_processors_of_type(self, processor_type):
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
        
        
    def get_string_annotation_values(self, annotation_name):
        self._refresh_string_annotation_values_cache_if_needed()
        try:
            return self._string_anno_archive_value_tuples[annotation_name]
        except KeyError:
            _handle_unrecognized_annotation_name(annotation_name)
     
    
    def _refresh_string_annotation_values_cache_if_needed(self):
        if self._string_anno_values_cache_dirty:
            self.refresh_string_annotation_values_cache()
             
             
    def refresh_string_annotation_values_cache(self):
        
        infos = AnnotationInfo.objects.all()
        
        self._string_anno_archive_value_tuples = dict(
            (i.name, _get_string_annotation_archive_values(i.name))
            for i in infos)
        
        ui_values_pref = self._ui_names.get('annotation_values', {})
        
        self._string_anno_ui_values = dict(
            (i.name, ui_values_pref.get(i.name, {}))
            for i in infos)
        
        self._string_anno_archive_values = dict(
            (i.name, _invert(ui_values_pref.get(i.name, {})))
            for i in infos)
        
        hidden_values_pref = self._hidden_objects.get('annotation_values', {})
        
        self._visible_string_anno_ui_values = dict(
            (i.name, self._get_visible_string_annotation_ui_values(
                i.name, hidden_values_pref))
            for i in AnnotationInfo.objects.all())
        
        self._visible_string_anno_ui_value_specs = dict(
            (i.name,
             self._get_visible_string_annotation_ui_value_specs(
                 i.name, hidden_values_pref))
            for i in AnnotationInfo.objects.all())
                
        self._string_anno_values_cache_dirty = False
         
             
    def _get_visible_string_annotation_ui_values(
            self, annotation_name, hidden_values_pref):
        
        hidden_values = hidden_values_pref.get(annotation_name, [])
        
        hidden_archive_values = set(
            self._get_string_annotation_archive_value(annotation_name, v)
            for v in hidden_values)
        
        archive_values = \
            self._string_anno_archive_value_tuples[annotation_name]
        
        if archive_values is None:
            return None
        
        else:
            
            visible_ui_values = sorted(
                self._get_string_annotation_ui_value(annotation_name, v)
                for v in archive_values
                if v not in hidden_archive_values)
                
            return tuple(visible_ui_values)
        
        
    def _get_visible_string_annotation_ui_value_specs(
            self, annotation_name, hidden_values_pref):
        
        hidden_value_specs = hidden_values_pref.get(annotation_name, [])
        
        hidden_archive_value_specs = set(
            self._get_string_annotation_archive_value(annotation_name, s)
            for s in hidden_value_specs)
        
        archive_values = \
            self._string_anno_archive_value_tuples[annotation_name]
            
        if archive_values is None:
            return None
        
        else:
            
            archive_value_specs = _get_string_annotation_archive_value_specs(
                archive_values)
            
            visible_ui_value_specs = [
                self._get_string_annotation_ui_value(annotation_name, s)
                for s in archive_value_specs
                if s not in hidden_archive_value_specs]
            
            return tuple(visible_ui_value_specs)
        
        
    def get_string_annotation_archive_value(
            self, annotation_name, annotation_value):
        
        self._refresh_string_annotation_values_cache_if_needed()
        
        return self._get_string_annotation_archive_value(
            annotation_name, annotation_value)
        
        
    # We define this method so we can call it instead of the public
    # `get_string_annotation_archive_value` method from within the
    # `_refresh_string_annotation_values_cache` method. Calling the
    # public method would initiate an endless recursion.
    def _get_string_annotation_archive_value(
            self, annotation_name, annotation_value):
        
        return self._get_string_annotation_value(
            annotation_name, annotation_value,
            self._string_anno_archive_values)
        
        
    def _get_string_annotation_value(
            self, annotation_name, annotation_value, values):
        
        # Get mapping from archive and UI annotation values to archive
        # or UI annotation values for the specified annotation name.
        try:
            values = values[annotation_name]
        except KeyError:
            _handle_unrecognized_annotation_name(annotation_name)
            
        # Get archive annotation value.
        return values.get(annotation_value, annotation_value)
     
     
    def get_string_annotation_ui_value(
            self, annotation_name, annotation_value):
        
        self._refresh_string_annotation_values_cache_if_needed()
        
        return self._get_string_annotation_ui_value(
            annotation_name, annotation_value)
        
        
    # We define this method so we can call it instead of the public
    # `get_string_annotation_ui_value` method from within the
    # `_refresh_string_annotation_values_cache` method. Calling the
    # public method would initiate an endless recursion.
    def _get_string_annotation_ui_value(
            self, annotation_name, annotation_value):
        
        return self._get_string_annotation_value(
            annotation_name, annotation_value, self._string_anno_ui_values)
    
    
    def get_visible_string_annotation_ui_values(self, annotation_name):
        
        self._refresh_string_annotation_values_cache_if_needed()
        
        try:
            return self._visible_string_anno_ui_values[annotation_name]
        except KeyError:
            _handle_unrecognized_annotation_name(annotation_name)
    
    
    def get_visible_string_annotation_ui_value_specs(
            self, annotation_name):
        
        self._refresh_string_annotation_values_cache_if_needed()
        
        try:
            return self._visible_string_anno_ui_value_specs[
                annotation_name]
        except KeyError:
            _handle_unrecognized_annotation_name(annotation_name)
            
            
    def get_tag_specs(self, include_not_applicable=True):
        infos = TagInfo.objects.all().order_by('name')
        specs = [i.name for i in infos]
        if include_not_applicable:
            specs = [_NOT_APPLICABLE] + specs
        return specs
    
    
def _get_hidden_objects(preferences):
    
    objects = preferences.get('hidden_objects', {})
    
    # Add processor names specified via older `hidden_processors` preference
    # to processor names specified via newer  `hidden_objects` preference.
    # The newer preference does not distinguish processors by type, so we
    # ignore the processor types specified in the older preference.
    processor_names = objects.get('processors', [])
    old_processors = preferences.get('hidden_processors', [])
    old_processor_names = [p['name'] for p in old_processors]
    processor_names = sorted(frozenset(processor_names + old_processor_names))
    objects['processors'] = processor_names
    
    return objects


def _handle_unrecognized_processor_name(name):
    raise ValueError(
        'Archive cache does not recognize processor name "{}".'.format(name))


def _handle_unrecognized_annotation_name(name):
    raise ValueError(
        'Archive cache does not recognize annotation name "{}".'.format(name))


def _get_string_annotation_archive_values(annotation_name):
    
    try:
        info = AnnotationInfo.objects.get(name=annotation_name)
    except AnnotationInfo.DoesNotExist:
        return None
    
    constraint = info.constraint
    
    if constraint is None:
        return None
    
    else:
        
        # We get the annotation values specified by the named constraint
        # in a two-stage process. In the first stage, we retrieve the
        # constraint's YAML, and the YAML of all of its ancestors, from
        # the database, parse it into constraint dictionaries, and
        # substitute parent constraint dictionaries for parent names.
        # We also look for inheritance graph cycles in this stage and
        # raise an exception if one is found.
        #
        # In the second stage, we create a flat tuple of annotation
        # values from the graph of constraint dictionaries produced
        # by the first stage.
        #
        # In retrospect I'm not sure it was really a good idea to
        # separate the processing into two stages rather than doing
        # it all in one. I don't think the single-stage processing
        # would really be any more difficult to write or understand.

        constraint = _get_string_annotation_constraint_dict(constraint.name)
        values = _get_string_annotation_constraint_values(constraint)
        return tuple(sorted(values))


def _get_string_annotation_constraint_dict(constraint_name):
    return _get_string_annotation_constraint_dict_aux(constraint_name, [])


def _get_string_annotation_constraint_dict_aux(
        constraint_name, visited_constraint_names):
    
    """
    Gets the specified string annotation value constraint from the
    database, parses its YAML to produce a constraint dictionary, and
    recursively substitutes similarly parsed constraint dictionaries for
    constraint names in the `extends` value (if there is one) of the result.
    
    This method detects cycles in constraint inheritance graphs, raising
    a `ValueError` when one is found.
    """
    
    if constraint_name in visited_constraint_names:
        # constraint inheritance graph is cyclic
        
        i = visited_constraint_names.index(constraint_name)
        cycle = ' -> '.join(visited_constraint_names[i:] + [constraint_name])
        raise ValueError(
            ('Cycle detected in constraint inheritance graph. '
             'Cycle is: {}.').format(cycle))
        
    constraint = AnnotationConstraint.objects.get(name=constraint_name)
    constraint = yaml_utils.load(constraint.text)
    
    constraint['parents'] = _get_string_annotation_constraint_parents(
        constraint, visited_constraint_names)
    
    return constraint
        
    
def _get_string_annotation_constraint_parents(
        constraint, visited_constraint_names):
    
    augmented_constraint_names = \
        visited_constraint_names + [constraint['name']]
    
    extends = constraint.get('extends')
    
    if extends is None:
        # constraint has no parents
        
        return []
    
    elif isinstance(extends, str):
        # `extends` is a parent constraint name
        
        return [_get_string_annotation_constraint_dict_aux(
            extends, augmented_constraint_names)]
        
    elif isinstance(extends, list):
        # `extends` is a list of parent constraint names
        
        return [
            _get_string_annotation_constraint_dict_aux(
                name, augmented_constraint_names)
            for name in extends]
        
    else:
        class_name = extends.__class__.__name__
        raise ValueError(
            ('Unexpected type "{}" for value of string annotation '
             'constraint "extends" item.').format(class_name))
    

def _get_string_annotation_constraint_values(constraint):
    
    parent_value_sets = [
        _get_string_annotation_constraint_values(parent)
        for parent in constraint['parents']]
        
    values = _get_string_annotation_constraint_own_values(constraint['values'])
    
    return values.union(*parent_value_sets)
    
    
def _get_string_annotation_constraint_own_values(values):
    
    flattened_values = set()
    
    for value in values:
        
        if isinstance(value, str):
            # value is string
            
            flattened_values.add(value)
            
        elif isinstance(value, dict):
            
            for parent, children in value.items():
                
                flattened_children = \
                    _get_string_annotation_constraint_own_values(children)
                
                sep = _STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR
                flattened_values |= set(
                    parent + sep + child
                    for child in flattened_children)
                
    return flattened_values


def _invert(d):
    return dict((v, k) for k, v in d.items())


def _get_string_annotation_archive_value_specs(annotation_values):
    
    """
    Gets a sorted list of annotation archive value specs derived from the
    specified annotation archive values.
    
    In addition to the specified archive values, the list includes specs
    for all ancestors of multicomponent values, as well as two wildcard
    specs for each ancestor. The list begins with specs for any or no
    annotation, no annotation, and any annotation.
    """
    
    default_specs = [
        _NOT_APPLICABLE,
        _STRING_ANNOTATION_VALUE_NONE,
        _STRING_ANNOTATION_VALUE_WILDCARD
    ]
    
    specs = set()
    for value in annotation_values:
        specs.add(value)
        specs |= _get_string_annotation_archive_value_specs_aux(value)
        
    return default_specs + sorted(specs)
        
        
def _get_string_annotation_archive_value_specs_aux(annotation_value):
    
    separator = _STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR
    wildcard = _STRING_ANNOTATION_VALUE_WILDCARD
    
    components = annotation_value.split(separator)
    
    specs = []
    
    for i in range(1, len(components)):
        
        spec = separator.join(components[:i])
        
        specs.append(spec)
        specs.append(spec + wildcard)
        specs.append(spec + separator + wildcard)
        
    return frozenset(specs)
