from django.urls import path

from vesper.django.s3_clip_tests.views import (
    AsyncS3ClipTestView, S3ClipTestView, SyncToAsyncS3ClipTestView)


urlpatterns = [
    
    path('s3-clip-test/', S3ClipTestView.as_view(), name='s3-clip-test'),

    path('async-s3-clip-test/', AsyncS3ClipTestView.as_view(),
         name='async-s3-clip-test'),

    path('sync-to-async-s3-clip-test/', SyncToAsyncS3ClipTestView.as_view(),
         name='sync-to-async-s3-clip-test'),
    
]
