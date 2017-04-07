from django import forms

from vesper.django.app.models import Processor
import vesper.django.app.model_utils as model_utils


class ClassifyForm(forms.Form):
    

    classifier = forms.ChoiceField(label='Classifier')
    detectors = forms.MultipleChoiceField(label='Detectors')
    station_mics = forms.MultipleChoiceField(label='Station/mics')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate classifiers field.
        classifiers = ['MPG Ranch Outside', 'MPG Ranch NFC Coarse']
        self.fields['classifier'].choices = [(c, c) for c in classifiers]
        
        # Populate detectors field.
        detectors = Processor.objects.filter(
            algorithm_version__algorithm__type='Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]
        
        # Populate station/mics field.
        names = model_utils.get_station_mic_output_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
