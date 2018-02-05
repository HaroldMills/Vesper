# Django template filters for Vesper.


from django import template
from django.utils.safestring import mark_safe


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
