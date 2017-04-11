from django import forms

import vesper.django.app.model_utils as model_utils


class ExportClipsForm(forms.Form):
    

    detectors = forms.MultipleChoiceField(label='Detectors')

    station_mics = forms.MultipleChoiceField(
        label='Station/mics',
        help_text='''
            This is the station/mic help text. I'm going to make it
            rather long so we can see how such text is displayed. I hope
            the display is reasonable. If it isn't perhaps we can develop
            a help text formatting function that can pre-process the text
            to make it look better.''')
    
    start_date = forms.DateField(label='Start date')
    
    end_date = forms.DateField(label='End date')
    
    output_dir_path = forms.CharField(
        label='Output directory', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate detectors field.
        detectors = model_utils.get_processors('Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]

        # Populate station/mics field.
        names = model_utils.get_station_mic_output_pair_ui_names()
        choices = [(name, name) for name in names]
        self.fields['station_mics'].choices = choices
