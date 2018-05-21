from django.conf.urls import url

from vesper.django.app import views

urlpatterns = [

    url(r'^$', views.index, name='index'),
    url(r'^clip-calendar/$', views.clip_calendar, name='clip-calendar'),
    url(r'^clip-album/$', views.clip_album, name='clip-album'),
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
    url(r'^export-clip-counts-csv-file/$', views.export_clip_counts_csv_file,
        name='export-clip-counts-csv-file'),
    url(r'^export-clips-csv-file/$', views.export_clips_csv_file,
        name='export-clips-csv-file'),
    url(r'^export-clip-sound-files/$', views.export_clip_sound_files,
        name='export-clip-sound-files'),
    url(r'^export-clips-hdf5-file/$', views.export_clips_hdf5_file,
        name='export-clips-hdf5-file'),
    url(r'^update-recording-file-paths/$', views.update_recording_file_paths,
        name='update-recording-file-paths'),
    url(r'^delete-recordings/$', views.delete_recordings,
        name='delete-recordings'),
    url(r'^delete-clips/$', views.delete_clips,
        name='delete-clips'),

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

    url((r'^clips/(?P<clip_id>[0-9]+)/annotations/'
         r'(?P<annotation_name>[a-zA-Z0-9_\-\. ]+)/$'),
        views.annotation, name='annotation'),

    url(r'^annotations/(?P<annotation_name>[a-zA-Z0-9_\-\. ]+)/$',
        views.annotations, name='annotations'),

    url(r'^presets/(?P<preset_type_name>[a-zA-Z0-9_\-\. ]+)/json/$',
        views.presets_json, name='presets-json'),

    url(r'^jobs/(?P<job_id>[0-9]+)/$', views.job, name='job'),

    # url(r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/$',
    #     views.view_station, name='station')

    # url((r'^view/(?P<station_name>[a-zA-Z0-9_\-\.]+)/'
    #      r'(?P<classification>[a-zA-Z0-9_\-\.]+)/$'),
    #     views.view_station, name='station')

]


# The above set of Vesper URLs has evolved as needed, and is incomplete
# and (probably) inconsistent. The rest of this file contains the beginnings
# of an attempt to design a more complete, consistent set of URLs.


# Channel number specifications: 1,3,5-7
# Date specifications: 20180412,20180414,20180416-20180418


'''
Recordings:

    /recordings:
        Methods:
            GET:
                Query Parameters:
                    - stations=1
                    - nights=20180412
                    - days=20180412
                Description: Gets HTML for the specified recordings.
            POST: >
                Creates a new, empty recording. Station, night, channels,
                start time, sample rate, data format, etc. are specified
                in request.

    /recordings/metadata/json:
        Methods:
            GET:
                Query Parameters:
                    - stations=1
                    - nights=20180412
                    - days=20180412
                    - fields=...
                Description: Gets metadata for the specified recordings.


    /recordings/123456:
        Methods:
            GET: Gets HTML for a recording.

    /recordings/123456/metadata/json:
        Methods:
            GET: Gets metadata for a recording.

    /recordings/123456/samples/<format>:
        Methods:
            GET:
                Query Parameters:
                    - channels=0,2,4-7
                    - start_index=10000
                    - end_index=20000
                Description:
                    Gets recording samples.
            POST: >
                Appends sample to a recording. The samples are converted
                from the specified format to the recording data format as
                needed.
        Notes:
            - <format> can be "wav" (GET only), "i16", "i24", or "f32".


Clips:

    /clips:
        Methods:
            GET:
                Query Parameters:
                    - station_mics=1
                    - detectors=1
                    - nights=20180412
                    - days=20180412
                    - annotations=Classification:AMRE
                Description:
                    Gets HTML for the specified clips.
            POST: >
                Creates a new clip. Both metadata and samples are
                specified in request (or must we separate the two?).

    /clips/metadata/json:
        Methods:
            GET:
                Query Parameters:
                    - station_mics=1
                    - detectors=1
                    - nights=20180412
                    - days=20180412
                    - annotations=Classification:AMRE
                Description:
                    Gets metadata for the specified clips.

    /clips/123456:
        Methods:
            GET: Gets HTML for a clip.

    /clips/123456/metadata/json:
        Methods:
            GET:
                Query Parameters:
                    - include_annotations=true
                    - include_tags=true
                Description: Gets metadata for a clip.

    /clips/123456/samples/<format>:
        Methods:
            GET: Gets the samples of a clip.
        Notes:
            - <format> can be "wav", "i16", "i24", or "f32".

    /clips/123456/annotations/json:
        Methods:
            GET: Gets all annotations for a clip.
            POST: Sets zero or more annotations for a clip.

    /clips/123456/tags/json:
        Methods:
            GET: Gets all tags for a clip.
            POST: Sets zero or more tags for a clip.


Annotations:

    /annotations:
        Methods:
            POST: >
                Annotates zero or more clips. Request JSON specifies an
                annotation info, an annotation value, and the clips to
                be annotated. We might expand this to support multiple
                annotations per clip, and perhaps different annotations
                for different clips.
'''
