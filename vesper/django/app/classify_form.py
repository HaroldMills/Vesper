from django import forms

import vesper.django.app.model_utils as model_utils
import vesper.django.app.ui_utils as ui_utils


class ClassifyForm(forms.Form):
    

    classifier = forms.ChoiceField(label='Classifier')
    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate classifiers field.
        self.fields['classifier'].choices = \
            ui_utils.get_processor_choices('Classifier')
        
        # Populate detectors field.
        self.fields['detectors'].choices = \
            ui_utils.get_processor_choices('Detector')
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
