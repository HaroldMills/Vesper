import os.path

from django import forms
from django.forms import ValidationError

from vesper.singleton.preference_manager import preference_manager


_preferences = preference_manager.preferences


def _get_default(name, default):
    defaults = _preferences.get('import_old_bird_clips_defaults', {})
    return defaults.get(name, default)


def _get_paths_default():
    paths = _get_default('paths', [])
    return ''.join(p + '\n' for p in paths)


class ImportClipsForm(forms.Form):
    

    paths = forms.CharField(
        label='Directory paths',
        initial=_get_paths_default(),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control command-form-wide-input',
                'rows': '5'}),
        help_text='''
            Specify the paths of one or more directories containing .wav
            files to import those files as clips. Each path should be
            specified on a separate line. Each of the specified directories
            will be searched recursively (i.e. the search will include
            subdirectories, subdirectories of subdirectories, etc.) for
            .wav files.''')

    start_date = forms.DateField(label='Start date', required=False)
    end_date = forms.DateField(label='End date', required=False)


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
