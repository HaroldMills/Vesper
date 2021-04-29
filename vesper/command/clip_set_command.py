"""Module containing class `ClipSetCommand`."""


import logging

from vesper.command.command import Command
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils


_logger = logging.getLogger()


class ClipSetCommand(Command):
    
    """Command that operates on each clip of a set of clips."""
    
    
    def __init__(self, args, is_mutating):
        
        super().__init__(args)
        
        self._is_mutating = is_mutating
        
        get = command_utils.get_required_arg
        
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._detector_names = get('detectors', args)
        
        classification = get('classification', args)
        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', classification)
            
        tag = get('tag', args)
        self._tag_name = model_utils.get_clip_query_tag_name(tag)
            
        
    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._sm_pair_ui_names, self._start_date, self._end_date,
                self._detector_names)
            
        except Exception as e:
            
            if self._is_mutating:
                result_text = 'The archive was not modified.'
            else:
                result_text = None
                
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction', result_text)
