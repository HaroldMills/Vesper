"""
Vesper URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""


from django.conf import settings
from django.urls import include, path


urlpatterns = [
    path('', include('vesper.django.app.urls')),
]


if not settings.ARCHIVE_READ_ONLY:
    
    from django.contrib import admin
    
    urlpatterns += [
        path('', include('django.contrib.auth.urls')),
        path('admin/', admin.site.urls)
    ]


# Django Debug Toolbar
# See https://django-debug-toolbar.readthedocs.io/en/stable/installation.html.

if settings.INCLUDE_DJANGO_DEBUG_TOOLBAR:
     
    import debug_toolbar
     
    urlpatterns = [
        path('debug/', include(debug_toolbar.urls)),
    ] + urlpatterns
