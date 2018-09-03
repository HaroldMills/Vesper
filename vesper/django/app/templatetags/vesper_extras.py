# Django template filters for Vesper.


import json

from django import template
from django.utils.safestring import mark_safe

import vesper.util.case_utils as case_utils


register = template.Library()


_DIV_CLASS = 'form-group form-spacing command-form-spacing'


@register.filter()
def form_element(field):
    return _form_element(field, False)


def _form_element(field, wrap_input_element):

    if wrap_input_element:
        start_tag = '<div>'
        end_tag = '</div>'
    else:
        start_tag = ''
        end_tag = ''

    return mark_safe('''
        <div class="{}">
          {}
          {}{}{}
          {}
        </div>'''.format(
            _DIV_CLASS, field.label_tag(), start_tag, field, end_tag,
            field.errors))


@register.filter()
def block_form_element(field):
    return _form_element(field, True)


@register.filter()
def form_checkbox(field):
    return mark_safe('''
        <div class="{}">
          {}
          {}
          {}
        </div>'''.format(_DIV_CLASS, field, field.label_tag(), field.errors))


@register.filter()
def to_json(obj):
    obj = case_utils.snake_keys_to_camel(obj)
    return json.dumps(obj)


@register.filter()
def bunch_to_json(bunch):
    return to_json(bunch.__dict__)
