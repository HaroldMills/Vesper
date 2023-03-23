from django.http import HttpResponse


# TODO: Make this able to function as either synchronous or asynchronous
# middleware. See
# https://docs.djangoproject.com/en/4.1/topics/http/ middleware/#asynchronous-support.


def healthCheckMiddleware(get_response):

    def middleware(request):
        if request.META['PATH_INFO'] == '/health-check/':
            return HttpResponse('Hello from Vesper!')
        else:
            return get_response(request)

    return middleware
