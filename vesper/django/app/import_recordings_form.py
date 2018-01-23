import os.path

from django import forms
from django.forms import ValidationError

from vesper.archive_paths import archive_paths
import vesper.django.app.form_utils as form_utils


_FORM_NAME = 'import_recordings'
    
    
def _get_field_default(name, default):
    return form_utils.get_field_default(_FORM_NAME, name, default)
    
    
def _get_paths_default():
    paths = _get_field_default('paths', None)
    if paths is None:
        paths = [str(p) for p in archive_paths.recording_dir_paths]
    return ''.join(p + '\n' for p in paths)


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
        initial=_get_field_default('recursive', True),
        required=False,
        help_text='''
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
