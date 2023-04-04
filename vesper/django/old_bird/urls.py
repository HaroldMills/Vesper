from django.conf import settings
from django.urls import path

from vesper.django.old_bird.views import CreateLrgvClipsView


if settings.VESPER_ARCHIVE_READ_ONLY:
    urlpatterns = []

else:
    urlpatterns = [
        path('create-lrgv-clips/', CreateLrgvClipsView.as_view(),
             name='create-lrgv-clips'),
    ]
