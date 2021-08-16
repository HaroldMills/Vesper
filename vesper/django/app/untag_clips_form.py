from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class UntagClipsForm(ClipSetForm):
    
    retain_count = forms.IntegerField(
        label='Retain count', min_value=0, initial=0)
    
    def __init__(self, *args, **kwargs):
        kwargs['clip_set_tag_required'] = True
        super().__init__(*args, **kwargs)
