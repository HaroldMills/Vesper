from django.conf.urls import url

from vesper.django.app import views

urlpatterns = [
               
    url(r'^$', views.index, name='index'),
    url(r'^calendar$', views.calendar, name='calendar'),
    url(r'^night$', views.night, name='night'),
#    url(r'^view$', views.view, name='view'),
    url(r'^detect$', views.detect, name='detect'),
    url(r'^classify$', views.classify, name='classify'),
    url(r'^import$', views.import_, name='import'),
    url(r'^export$', views.export, name='export'),
    
    url(r'^stations/$', views.stations, name='stations'),
    
    url(r'^stations/(?P<station_name>[a-zA-Z0-9_\-\. ]+)/$',
        views.station, name='station'),
               
    url(r'^stations/(?P<station_name>[a-zA-Z0-9_\-\. ]+)/clips/$',
        views.station_clips, name='station-clips'),
               
    url(r'^clips/$', views.clips, name='clips'),
    
    url(r'^clips/(?P<clip_id>[0-9]+)$', views.clip, name='clip'),

    url(r'^clips/(?P<clip_id>[0-9]+)/wav$', views.clip_wav, name='clip-wav'),
    
    url(r'^clips/(?P<clip_id>[0-9]+)/annotations/(?P<annotation_name>[a-zA-Z0-9_\-\. ]+)$', views.annotation, name='annotation'),
               
    url(r'^presets/(?P<preset_type_name>[a-zA-Z0-9_\-\. ]+)/json$', views.presets_json, name='presets-json')
#     url(r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/$',
#         views.view_station, name='station')

#     url((r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/'
#          r'(?P<classification>[a-zA-Z0-9_\-\.]+)/$'),
#         views.view_station, name='station')

]