import os.path

from django import forms
from django.forms import ValidationError


class ImportRecordingsForm(forms.Form):
    

    paths = forms.CharField(
        label='File and/or directory paths',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '5'}))

    recursive = forms.BooleanField(label='Recursive', required=False)


    def clean_paths(self):
        
        # Strip surrounding whitespace and quotes from paths.
        paths = self.cleaned_data['paths'].strip()
        paths = [_strip(line) for line in paths.split('\n')]
        paths = [path for path in paths if len(path) > 0]
        
        # Check that paths exist.
        for path in paths:
            if not os.path.exists(path):
                raise ValidationError('Path "{}" does not exist.'.format(path))
            
        return paths
    
    
def _strip(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s
