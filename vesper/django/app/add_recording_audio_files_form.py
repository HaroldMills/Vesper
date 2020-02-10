from django import forms


class AddRecordingAudioFilesForm(forms.Form):
    
    
    dry_run = forms.BooleanField(
        label='Dry run',
        label_suffix='',
        initial=False,
        required=False)
