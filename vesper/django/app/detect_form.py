from django import forms

from vesper.django.app.models import Station
from vesper.singletons import preset_manager
import vesper.django.app.model_utils as model_utils


class DetectForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    schedule = forms.ChoiceField(label='Schedule', required=False)
    
    create_clip_files = forms.BooleanField(
        label='Create clip sound files',
        label_suffix='',
        required=False)
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        detectors = model_utils.get_processors('Detector')
        self.fields['detectors'].choices = \
            [(d.name, d.name) for d in detectors]
        
        # Populate stations field.
        station_names = sorted(s.name for s in Station.objects.all())
        self.fields['stations'].choices = [(n, n) for n in station_names]
        
        # Populate schedule field.
        presets = preset_manager.instance.get_flattened_presets(
            'Detection Schedule')
        preset_names = ['/'.join(p[0]) for p in presets]
        choices = [(None, 'None')] + [(n, n) for n in preset_names]
        self.fields['schedule'].choices = choices
