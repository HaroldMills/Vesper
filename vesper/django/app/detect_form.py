from django import forms

from vesper.django.app.models import Station
from vesper.singleton.preset_manager import preset_manager
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Detect'
_SCHEDULE_FIELD_LABEL = 'Schedule'
_DEFER_CLIP_CREATION_LABEL = 'Defer clip creation'
    
    
def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)
    
    
class DetectForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')
    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    schedule = forms.ChoiceField(
        label=_SCHEDULE_FIELD_LABEL,
        initial=_get_field_default(_SCHEDULE_FIELD_LABEL, None),
        required=False)
    
    defer_clip_creation = forms.BooleanField(
        label=_DEFER_CLIP_CREATION_LABEL,
        label_suffix='',
        initial=_get_field_default(_DEFER_CLIP_CREATION_LABEL, False),
        required=False)
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        self.fields['detectors'].choices = \
            form_utils.get_processor_choices('Detector')
        
        # Populate stations field.
        station_names = sorted(s.name for s in Station.objects.all())
        self.fields['stations'].choices = [(n, n) for n in station_names]
        
        # Populate schedule field.
        presets = preset_manager.get_presets('Detection Schedule')
        preset_paths = ['/'.join(p.path[1:]) for p in presets]
        choices = [(None, 'None')] + [(p, p) for p in preset_paths]
        self.fields['schedule'].choices = choices
