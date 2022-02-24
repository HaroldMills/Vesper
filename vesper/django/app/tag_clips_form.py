from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class TagClipsForm(ClipSetForm):
    
    clip_count = forms.IntegerField(
        label='Clip count', min_value=0, required=False)
