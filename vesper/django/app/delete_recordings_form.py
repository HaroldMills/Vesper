from django import forms

from vesper.django.app.models import Station


class DeleteRecordingsForm(forms.Form):
    

    stations = forms.MultipleChoiceField(label='Stations')
    start_date = forms.DateField(label='Start date')
    end_date = forms.DateField(label='End date')
    
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate stations field.
        stations = Station.objects.all()
        self.fields['stations'].choices = [(s.name, s.name) for s in stations]
