from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
from vesper.singleton.preset_manager import preset_manager
import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Export clip metadata to CSV file'
_TABLE_FORMAT_FIELD_LABEL = 'Table format'


def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_TITLE, name, default)


class ExportClipMetadataToCsvFileForm(ClipSetForm):
    
    table_format = forms.ChoiceField(
        label=_TABLE_FORMAT_FIELD_LABEL,
        initial=_get_field_default(_TABLE_FORMAT_FIELD_LABEL, None),
        required=False)
    
    output_file_path = forms.CharField(
        label='Output file', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate table format field.
        presets = preset_manager.get_presets('Clip Table Format')
        preset_paths = ['/'.join(p.path[1:]) for p in presets]
        choices = [(p, p) for p in preset_paths]
        self.fields['table_format'].choices = choices
