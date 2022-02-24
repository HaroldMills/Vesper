from django import forms

from vesper.django.app.clip_set_form import ClipSetForm


class TagClipsForm(ClipSetForm):
    
    clip_count = forms.IntegerField(
        label='Clip count', min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        kwargs['clip_set_tag_required'] = True
        super().__init__(*args, **kwargs)
