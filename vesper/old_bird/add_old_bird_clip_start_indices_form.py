from django import forms

from vesper.django.app.models import Station


class AddOldBirdClipStartIndicesForm(forms.Form):
    
    
    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    dry_run = forms.BooleanField(
        label='Dry run',
        label_suffix='',
        initial=False,
        required=False)

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate stations field.
        stations = Station.objects.all()
        self.fields['stations'].choices = [(s.name, s.name) for s in stations]
