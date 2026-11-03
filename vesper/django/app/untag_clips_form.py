from django import forms

from vesper.django.app.clip_set_form import ClipSetForm
import vesper.django.app.form_utils as form_utils


class UntagClipsForm(ClipSetForm):
    
    remove_tag = forms.ChoiceField(label='Remove tag')

    retain_count = forms.IntegerField(
        label='Retain count', min_value=0, required=False)
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        # Populate remove tag field.
        self.fields['remove_tag'].choices = form_utils.get_tag_choices()
