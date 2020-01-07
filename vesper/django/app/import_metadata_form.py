from django import forms
from django.forms import ValidationError

import vesper.util.yaml_utils as yaml_utils


class ImportMetadataForm(forms.Form):
    

    metadata = forms.CharField(
        label='Metadata YAML',
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


    def clean_metadata(self):
        try:
            return yaml_utils.load(self.cleaned_data['metadata'])
        except Exception:
            raise ValidationError('Could not parse metadata YAML.')
