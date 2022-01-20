from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
from vesper.singleton.preset_manager import preset_manager
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Export clips to audio files'
_TIME_INTERVAL_FIELD_LABEL = 'Clip export time interval preset'
_DIR_PATH_FIELD_LABEL = 'Output directory'


def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)
    
    
class ExportClipsToAudioFilesForm(ClipSetForm):
    

    time_interval = forms.ChoiceField(
        label=_TIME_INTERVAL_FIELD_LABEL,
        initial=_get_field_default(_TIME_INTERVAL_FIELD_LABEL, None),
        required=False)
    
    output_dir_path = forms.CharField(
        label=_DIR_PATH_FIELD_LABEL, max_length=255,
        initial=_get_field_default(_DIR_PATH_FIELD_LABEL, ''),
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate time interval field.
        self.fields['time_interval'].choices = \
            form_utils.get_preset_choices('Clip Export Time Interval')

