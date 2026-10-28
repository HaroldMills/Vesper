from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Create dataset call clips'
_CLIP_DURATION_FIELD_LABEL = 'Clip duration'
    

def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)


class CreateDatasetCallClipsForm(ClipSetForm):

    clip_duration = forms.FloatField(
        label=_CLIP_DURATION_FIELD_LABEL,
        initial=_get_field_default(_CLIP_DURATION_FIELD_LABEL, None),
        min_value=0
    )
        
