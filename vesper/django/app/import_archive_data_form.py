from django import forms
from django.forms import ValidationError
import yaml


class ImportArchiveDataForm(forms.Form):
    

    archive_data = forms.CharField(
        label='Archive data YAML',
        widget=forms.Textarea(
            attrs={
                'id': 'yaml-text-area',
                'class': 'form-control command-form-wide-input',
                'rows': '15',
                'ondragover': 'onDragOver(event);',
                'ondrop': 'onDrop(event);'
            }
        )
    )


    def clean_archive_data(self):
        try:
            return yaml.load(self.cleaned_data['archive_data'])
        except Exception:
            raise ValidationError('Could not parse specified YAML.')
    