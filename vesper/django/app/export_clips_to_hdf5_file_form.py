from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class ExportClipsToHdf5FileForm(ClipSetForm):
    
    output_file_path = forms.CharField(
        label='Output file', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
