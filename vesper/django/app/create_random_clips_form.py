from django import forms

from vesper.django.app.models import Station
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Create random clips'
_SCHEDULE_FIELD_LABEL = 'Detection schedule preset'
_CLIP_DURATION_FIELD_LABEL = 'Clip duration'
_CLIP_COUNT_FIELD_LABEL = 'Clip count'
    

# TODO: Consider creating a `VesperForm` class that includes field
# default method(s) and perhaps other functionality, like a form title.


def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)
    
    
class CreateRandomClipsForm(forms.Form):
    

    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    schedule = forms.ChoiceField(
        label=_SCHEDULE_FIELD_LABEL,
        initial=_get_field_default(_SCHEDULE_FIELD_LABEL, None),
        required=False)

    clip_duration = forms.FloatField(
        label=_CLIP_DURATION_FIELD_LABEL,
        initial=_get_field_default(_CLIP_DURATION_FIELD_LABEL, None),
        min_value=0
    )

    clip_count = forms.IntegerField(
        label=_CLIP_COUNT_FIELD_LABEL,
        initial=_get_field_default(_CLIP_COUNT_FIELD_LABEL, None),
        min_value=0
    )
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate stations field.
        station_names = sorted(s.name for s in Station.objects.all())
        self.fields['stations'].choices = [(n, n) for n in station_names]
        
        # Populate schedule field.
        self.fields['schedule'].choices = \
            form_utils.get_preset_choices('Detection Schedule')
