import itertools

from django import forms

from vesper.django.app.models import Processor, Station


class ExportClipSoundFilesForm(forms.Form):
    

    station_mics = forms.MultipleChoiceField(
        label='Station/microphone pairs',
        help_text='''
            This is the station/microphone help text. I'm going to make it
            rather long so we can see how such text is displayed. I hope
            the display is reasonable. If it isn't perhaps we can develop
            a help text formatting function that can pre-process the text
            to make it look better.''')
    
    detectors = forms.MultipleChoiceField(label='Detectors')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    output_dir_path = forms.CharField(
        label='Output directory', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate stations field.
        stations = Station.objects.all()
        choices = list(itertools.chain.from_iterable(
            _get_station_mic_choices(s) for s in stations))
        self.fields['station_mics'].choices = choices

        # Populate detectors field.
        detectors = Processor.objects.filter(
            algorithm_version__algorithm__type='Detector')
        self.fields['detectors'].choices = [(d.name, d.name) for d in detectors]


def _get_station_mic_choices(station):
    # We put station/microphone pairs into a set and then create a sorted
    # list from the set since there can be more than one `StationDevice`
    # object for a given station/microphone pair.
    return sorted(set(
        _get_station_mic_choice(sd)
        for sd in station.get_station_devices('Microphone')))    
    
    
def _get_station_mic_choice(sd):
    name = '{} / {}'.format(sd.station.name, sd.device.name)
    return (name, name)
    