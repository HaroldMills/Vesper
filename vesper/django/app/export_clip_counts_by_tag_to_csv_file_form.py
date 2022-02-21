from django import forms

import vesper.django.app.form_utils as form_utils


_FORM_TITLE = 'Export clip counts by tag to CSV file'


class ExportClipCountsByTagToCsvFileForm(forms.Form):
    

    output_file_path = forms.CharField(
        label='Output file', max_length=255,
        widget=forms.TextInput(attrs={'class': 'command-form-wide-input'}))
