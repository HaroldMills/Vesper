from django import forms

import vesper.django.app.model_utils as model_utils


class TransferCallClassificationsForm(forms.Form):
    

    source_detector = forms.ChoiceField(label='Source detector')
    target_detector = forms.ChoiceField(label='Target detector')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detector fields.
        detectors = model_utils.get_processors('Detector')
        choices = [(d.name, d.name) for d in detectors]
        self.fields['source_detector'].choices = choices
        self.fields['target_detector'].choices = choices
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(n, n) for n in names]
        self.fields['station_mics'].choices = choices
