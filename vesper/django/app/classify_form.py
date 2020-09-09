from django import forms

import vesper.django.app.model_utils as model_utils
import vesper.django.app.form_utils as form_utils


class ClassifyForm(forms.Form):
    

    classifier = forms.ChoiceField(label='Classifier')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    detectors = forms.MultipleChoiceField(label='Detectors')
    tag = forms.ChoiceField(label='Tag')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate classifiers field.
        self.fields['classifier'].choices = \
            form_utils.get_processor_choices('Classifier')
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
 
        # Populate detectors field.
        self.fields['detectors'].choices = \
            form_utils.get_processor_choices('Detector')
        
        # Populate tag field.
        self.fields['tag'].choices = form_utils.get_tag_choices()
