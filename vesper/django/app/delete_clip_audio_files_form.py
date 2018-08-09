from django import forms

import vesper.django.app.model_utils as model_utils


class DeleteClipAudioFilesForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    classification = forms.ChoiceField(label='Classification')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        detectors = model_utils.get_processors('Detector')
        choices = [(d.name, d.name) for d in detectors]
        self.fields['detectors'].choices = choices
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(n, n) for n in names]
        self.fields['station_mics'].choices = choices
        
        # Populate classification field.
        specs = model_utils.get_string_annotation_value_specs('Classification')
        choices = [(s, s) for s in specs]
        self.fields['classification'].choices = choices
