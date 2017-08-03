from django.conf.urls import url

from vesper.django.app import views

urlpatterns = [
               
    url(r'^$', views.index, name='index'),
    url(r'^calendar/$', views.calendar, name='calendar'),
    url(r'^night/$', views.night, name='night'),
    url(r'^test-command/$', views.test_command, name='test-command'),
    
    url(r'^import-archive-data/$', views.import_archive_data,
        name='import-archive-data'),
               
    url(r'^import-recordings/$', views.import_recordings,
        name='import-recordings'),
               
    url(r'^import-old-bird-clips/$', views.import_old_bird_clips,
        name='import-old-bird-clips'),
               
    url(r'^detect/$', views.detect, name='detect'),
    url(r'^classify/$', views.classify, name='classify'),
    url(r'^export-clips-csv-file/$', views.export_clips_csv_file,
        name='export-clips-csv-file'),
    url(r'^export-clip-sound-files/$', views.export_clip_sound_files,
        name='export-clip-sound-files'),
    
    url(r'^stations/$', views.stations, name='stations'),
    
    url(r'^stations/(?P<station_name>[a-zA-Z0-9_\-\. ]+)/$',
        views.station, name='station'),
               
    url(r'^stations/(?P<station_name>[a-zA-Z0-9_\-\. ]+)/clips/$',
        views.station_clips, name='station-clips'),
               
    url(r'^clips/$', views.clips, name='clips'),
    
    url(r'^clips/(?P<clip_id>[0-9]+)/$', views.clip, name='clip'),

    url(r'^clips/(?P<clip_id>[0-9]+)/wav/$', views.clip_wav, name='clip-wav'),
    
    url(r'^clips/(?P<clip_id>[0-9]+)/annotations/json/$',
        views.annotations_json, name='annotations'),
    
    url(r'^clips/(?P<clip_id>[0-9]+)/annotations/(?P<annotation_name>[a-zA-Z0-9_\-\. ]+)/$',
        views.annotation, name='annotation'),
               
    url(r'^presets/(?P<preset_type_name>[a-zA-Z0-9_\-\. ]+)/json/$',
        views.presets_json, name='presets-json'),

    url(r'^jobs/(?P<job_id>[0-9]+)/$', views.job, name='job'),
    
#     url(r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/$',
#         views.view_station, name='station')

#     url((r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/'
#          r'(?P<classification>[a-zA-Z0-9_\-\.]+)/$'),
#         views.view_station, name='station')

]