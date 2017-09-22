from django import forms

from vesper.django.app.models import Station
import vesper.django.app.model_utils as model_utils


class DetectForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        detectors = model_utils.get_processors('Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]
        
        # Populate stations field.
        stations = Station.objects.all()
        self.fields['stations'].choices = [(s.name, s.name) for s in stations]
