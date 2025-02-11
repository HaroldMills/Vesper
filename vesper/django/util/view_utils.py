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


def add_url_base(pathname):
    prefix = get_script_prefix()
    if pathname.startswith('/'):
        return prefix + pathname[1:]
    else:
        return prefix + pathname


import asyncio
from functools import wraps
from urllib.parse import urlparse

from asgiref.sync import async_to_sync, sync_to_async

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.urls import get_script_prefix


# TODO: Understand better why I've had to create a custom version of
# the `login_required` decorator. Am I doing something wrong that causes
# the standard `login_required` decorator to fail when the URL base
# (i.e. `settings.FORCE_SCRIPT_NAME`) is not just "/"? If not, is there a
# good way to modify the standard decorator to work for non-"/" URL bases,
# and would the Django project accept such a change?
def login_required(
    function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None
):
    
    """
    This function and the `_user_passes_test` function below are identical
    to the functions of the same name in Django except for one line of
    `_user_passes_test`, which prepends the URL pathname base to the
    request URL pathname.

    For our purposes I believe these functions could be simplified a lot,
    since we don't use async views and the URL schemes and net locations
    of the login URL and request URL are always the same. I haven't made
    the simplifications, however, since I'm hoping our use of this
    customized `login_required` decorator will be temporary.

    I have had to bend over backwards to get the Vesper Server to work
    with a non-"/" URL pathname base. I'm hoping that this is just
    because there's something I don't understand yet about Django and
    NGINX configuration, and that when I do understand it some of the
    complexity of my code will go away, including this customized
    decorator.
    """

    actual_decorator = _user_passes_test(
        lambda u: u.is_authenticated,
        login_url=login_url,
        redirect_field_name=redirect_field_name,
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def _user_passes_test(
    test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME
):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """

    def decorator(view_func):
        def _redirect_to_login(request):
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            # If the login url is the same scheme and net location then just
            # use the path as the "next" url.
            login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
            current_scheme, current_netloc = urlparse(path)[:2]
            # print(f'_user_passes_test: path "{path}"')
            # print(f'_user_passes_test: login URL "{resolved_login_url}"')
            if (not login_scheme or login_scheme == current_scheme) and (
                not login_netloc or login_netloc == current_netloc
            ):
                path = add_url_base(request.get_full_path())
            print(f'_user_passes_test: full path "{request.get_full_path()}"')
            print(f'_user_passes_test: full path info "{request.get_full_path_info()}"')
            print(f'_user_passes_test: path "{path}"')
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(path, resolved_login_url, redirect_field_name)

        if asyncio.iscoroutinefunction(view_func):

            async def _view_wrapper(request, *args, **kwargs):
                auser = await request.auser()
                if asyncio.iscoroutinefunction(test_func):
                    test_pass = await test_func(auser)
                else:
                    test_pass = await sync_to_async(test_func)(auser)

                if test_pass:
                    return await view_func(request, *args, **kwargs)
                return _redirect_to_login(request)

        else:

            def _view_wrapper(request, *args, **kwargs):
                if asyncio.iscoroutinefunction(test_func):
                    test_pass = async_to_sync(test_func)(request.user)
                else:
                    test_pass = test_func(request.user)

                if test_pass:
                    return view_func(request, *args, **kwargs)
                return _redirect_to_login(request)

        # Attributes used by LoginRequiredMiddleware.
        _view_wrapper.login_url = login_url
        _view_wrapper.redirect_field_name = redirect_field_name

        return wraps(view_func)(_view_wrapper)

    return decorator
