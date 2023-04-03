"""Utility functions for Django views."""


import json

from django.http import HttpResponse, HttpResponseBadRequest

from vesper.util.bunch import Bunch


class _HttpError(Exception):

    def __init__(self, status_code, reason=None):
        self._status_code = status_code
        self._reason = reason

    @property
    def http_response(self):
        return HttpResponse(status=self._status_code, reason=self._reason)


def handle_json_post(request, content_handler, *args):
        
    try:
        content = _get_json_request_body(request)
    except _HttpError as e:
        return e.http_response

    try:
        content = json.loads(content)
    except json.JSONDecodeError as e:
        return HttpResponseBadRequest(
            reason='Could not decode request JSON')

    return content_handler(content, *args)
    
        
def _get_json_request_body(request):

    # According to rfc4627, utf-8 is the default charset for the
    # application/json media type.

    return _get_request_body(request, 'application/json', 'utf-8')


def _get_request_body(request, content_type_name, default_charset_name):

    content_type = _parse_content_type(request.META['CONTENT_TYPE'])

    # Make sure content type is text/plain.
    if content_type.name != content_type_name:
        raise _HttpError(
            status_code=415,
            reason=f'Request content type must be {content_type_name}')

    charset = content_type.params.get('charset', default_charset_name)

    return request.body.decode(charset)


# TODO: Does Django already include functions for parsing HTTP headers?
# If so, I couldn't find them.
def _parse_content_type(content_type):

    parts = [p.strip() for p in content_type.split(';')]

    params = {}
    for part in parts[1:]:
        try:
            name, value = part.split('=', 1)
        except ValueError:
            continue
        params[name] = value

    return Bunch(name=parts[0], params=params)
