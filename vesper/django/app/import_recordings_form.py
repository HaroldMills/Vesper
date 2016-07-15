from django import forms


class ImportRecordingsForm(forms.Form):
    path = forms.CharField(label='File or directory path')
