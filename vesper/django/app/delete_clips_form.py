from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class DeleteClipsForm(ClipSetForm):
    
    retain_count = forms.IntegerField(
        label='Retain count', min_value=0, initial=0)
