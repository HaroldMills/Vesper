from django import forms

import vesper.django.app.form_utils as form_utils
import vesper.django.app.model_utils as model_utils


_FORM_NAME = 'export_clip_counts_csv_file'
    
    
def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_NAME, name, default)


class ExportClipCountsCsvFileForm(forms.Form):
    
    
    detector = forms.ChoiceField(
        label='Detector',
        initial=_get_field_default('detector', ''))
    
    station_mic = forms.ChoiceField(
        label='Station/mic',
        initial=_get_field_default('station_mic', ''))
    
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')

    file_name = forms.CharField(
        label='CSV file name', required=False, max_length=255,
        widget=forms.TextInput())


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        self.fields['detector'].choices = \
            form_utils.get_processor_choices('Detector')

        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mic'].choices = choices
