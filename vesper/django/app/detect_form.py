from django import forms

from vesper.django.app.models import Processor, Station


class DetectForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start Date')
    end_date = forms.DateField(label='End Date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        detectors = Processor.objects.filter(
            algorithm_version__algorithm__type='Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]
        
        # Populate stations field.
        stations = Station.objects.all()
        self.fields['stations'].choices = [(s.name, s.name) for s in stations]
