from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Export clips to HDF5 file'
_SETTINGS_PRESET_FIELD_LABEL = 'Clip HDF5 file export settings preset'
_FILE_PATH_FIELD_LABEL = 'Output file'


def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)
    
    
class ExportClipsToHdf5FileForm(ClipSetForm):
    

    clip_hdf5_file_export_settings_preset = forms.ChoiceField(
        label=_SETTINGS_PRESET_FIELD_LABEL,
        initial=_get_field_default(_SETTINGS_PRESET_FIELD_LABEL, None),
        required=False)
    
    output_file_path = forms.CharField(
        label=_FILE_PATH_FIELD_LABEL, max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate settings preset field.
        self.fields['clip_hdf5_file_export_settings_preset'].choices = \
            form_utils.get_preset_choices('Clip HDF5 File Export Settings')
