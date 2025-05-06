from django.conf import settings
from django.urls import path

from vesper.django.old_bird.views import ImportRecordingsAndClipsView


if settings.VESPER_ARCHIVE_READ_ONLY:
    urlpatterns = []

else:
    urlpatterns = [
        path(
            'import-recordings-and-clips/',
            ImportRecordingsAndClipsView.as_view(),
             name='import-recordings-and-clips'),
    ]
