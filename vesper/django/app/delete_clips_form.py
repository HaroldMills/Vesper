from django import forms

import vesper.django.app.model_utils as model_utils
import vesper.django.app.ui_utils as ui_utils


class DeleteClipsForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    classification = forms.ChoiceField(label='Classification')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    retain_count = forms.IntegerField(
        label='Retain count', min_value=0, initial=0)
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        self.fields['detectors'].choices = \
            ui_utils.get_processor_choices('Detector')
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(n, n) for n in names]
        self.fields['station_mics'].choices = choices
        
        # Populate classification field.
        specs = model_utils.get_string_annotation_value_specs('Classification')
        choices = [(s, s) for s in specs]
        self.fields['classification'].choices = choices
