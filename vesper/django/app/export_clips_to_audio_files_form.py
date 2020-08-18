from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class ExportClipsToAudioFilesForm(ClipSetForm):
    
    output_dir_path = forms.CharField(
        label='Output directory', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
