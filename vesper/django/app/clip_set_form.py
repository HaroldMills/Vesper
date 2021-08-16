"""
Form with fields for specifying a set of clips.

The clips are specified as a set of detectors, a set of station/mic pairs,
a classification, and a range of dates.

This form can be used by a Django view either as is, or with additional
fields specified in a subclass.
"""


from django import forms

import vesper.django.app.form_utils as form_utils
import vesper.django.app.model_utils as model_utils


class ClipSetForm(forms.Form):
    

    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    detectors = forms.MultipleChoiceField(label='Detectors')
    classification = forms.ChoiceField(label='Classification')
    tag = forms.ChoiceField(label='Tag')
    
    
    def __init__(self, *args, **kwargs):
        
        # Copy `kwargs` so we can delete our keyword arguments from the
        # copy before passing it to the `forms.Form` initializer. That
        # initializer will raise an exception if it receives any of our
        # keyword arguments, since it does not recognize them.
        kwargs_copy = dict(kwargs)
        
        tag_required = self._get_optional_kwarg(
            kwargs_copy, 'clip_set_tag_required', False)
        
        super().__init__(*args, **kwargs_copy)
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
        
        # Populate detectors field.
        self.fields['detectors'].choices = \
            form_utils.get_processor_choices('Detector')

        # Populate classification field.
        self.fields['classification'].choices = \
            form_utils.get_string_annotation_value_choices('Classification')
            
        # Populate tag field.
        include_not_applicable = not tag_required
        self.fields['tag'].choices = \
            form_utils.get_tag_choices(include_not_applicable)


    def _get_optional_kwarg(self, kwargs, name, default_value):
        
        if name in kwargs:
            # argument present
            
            value = kwargs[name]
            del kwargs[name]
            return value
            
        else:
            # argument not present
            
            return default_value
        