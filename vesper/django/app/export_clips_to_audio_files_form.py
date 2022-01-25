from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Export clips to audio files'
_SETTINGS_PRESET_FIELD_LABEL = 'Clip audio file export settings preset'
_DIR_PATH_FIELD_LABEL = 'Output directory'


def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)
    
    
class ExportClipsToAudioFilesForm(ClipSetForm):
    

    clip_audio_file_export_settings_preset = forms.ChoiceField(
        label=_SETTINGS_PRESET_FIELD_LABEL,
        initial=_get_field_default(_SETTINGS_PRESET_FIELD_LABEL, None),
        required=False)
    
    output_dir_path = forms.CharField(
        label=_DIR_PATH_FIELD_LABEL, max_length=255,
        initial=_get_field_default(_DIR_PATH_FIELD_LABEL, ''),
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate settings preset field.
        self.fields['clip_audio_file_export_settings_preset'].choices = \
            form_utils.get_preset_choices('Clip Audio File Export Settings')
