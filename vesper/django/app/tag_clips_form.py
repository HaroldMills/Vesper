from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
import vesper.django.app.form_utils as form_utils


class TagClipsForm(ClipSetForm):

    add_tag = forms.ChoiceField(label='Add tag')

    clip_count = forms.IntegerField(
        label='Clip count', min_value=0, required=False)


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate add tag field.
        self.fields['add_tag'].choices = form_utils.get_tag_choices()

