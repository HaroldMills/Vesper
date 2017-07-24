import os.path

from django import forms
from django.forms import ValidationError

from vesper.singletons import preference_manager


_preferences = preference_manager.instance.preferences


def _get_default(name, default):
    defaults = _preferences.get('import_recordings_defaults', {})
    return defaults.get(name, default)


def _get_paths_default():
    paths = _get_default('paths', [])
    return ''.join(p + '\n' for p in paths)


def _get_recursive_default():
    return _get_default('recursive', False)


class ImportRecordingsForm(forms.Form):
    

    paths = forms.CharField(
        label='File and/or directory paths',
        initial=_get_paths_default(),
        widget=forms.Textarea(
            attrs={
                'class': 'form-control command-form-wide-input',
                'rows': '5'}),
        help_text='''
            Specify the paths of one or more .wav files and/or directories
            containing .wav files to import those files as recordings. Each
            path should be specified on a separate line. Multi-file recordings
            are automatically recognized from the stations, start times, and
            durations of the imported files.''')


    recursive = forms.BooleanField(
        label='Recursive',
        label_suffix='',
        initial=_get_recursive_default(),
        required=False,
        help_text = '''
            Check the box to recursively include .wav files in subdirectories
            of any specified directories. Uncheck the box to exclude such
            files.''')


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
