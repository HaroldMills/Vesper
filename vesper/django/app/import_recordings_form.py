import os.path

from django import forms
from django.forms import ValidationError


class ImportRecordingsForm(forms.Form):
    

    paths = forms.CharField(
        label='File and/or directory paths',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}))


    recursive = forms.BooleanField(label='Recursive', required=False)


    def clean_paths(self):
        paths = self.cleaned_data['paths'].strip()
        paths = [line.strip() for line in paths.split('\n')]
        print('clean_paths', paths)
        for path in paths:
            if not os.path.exists(path):
                raise ValidationError('Path "{}" does not exist.'.format(path))
        return paths
    