from django.conf import settings
from django.urls import path, register_converter

import vesper.django.app.views as views
from vesper.django.app.name_converter import NameConverter


register_converter(NameConverter, 'name')


urlpatterns = [
    
    path('', views.index, name='index'),
    path('clip-calendar/', views.clip_calendar, name='clip-calendar'),
    path('clip-album/', views.clip_album, name='clip-album'),
    path('night/', views.night, name='night'),
    
    path('batch/read/clip-audios/',
         views.batch_read_clip_audios,
         name='batch-read-clip-audios'),
        
    path('batch/read/clip-annotations/',
         views.batch_read_clip_annotations,
         name='batch-read-clip-annotations'),
        
    path('clips/<int:clip_id>/wav/', views.clip_wav, name='clip-wav'),
    path('clips/<int:clip_id>/annotations/json/', views.annotations_json,
         name='annotations')
    
]


if not settings.ARCHIVE_READ_ONLY:
    
    urlpatterns += [
    
        # path('test-command/', views.test_command, name='test-command'),
    
        path('import-archive-data/', views.import_archive_data,
             name='import-archive-data'),
        path('import-recordings/', views.import_recordings,
             name='import-recordings'),
        path('import-old-bird-clips/', views.import_old_bird_clips,
             name='import-old-bird-clips'),
    
        path('detect/', views.detect, name='detect'),
        path('classify/', views.classify, name='classify'),
        path('execute-deferred-actions/', views.execute_deferred_actions,
             name='execute-deferred-actions'),
        
        path('old-bird-export-clip-counts-csv-file/',
             views.old_bird_export_clip_counts_csv_file,
             name='old-bird-export-clip-counts-csv-file'),
        path('export-clips-csv-file/', views.export_clips_csv_file,
             name='export-clips-csv-file'),
        path('export-clip-audio-files/', views.export_clip_audio_files,
             name='export-clip-audio-files'),
        path('export-clips-hdf5-file/', views.export_clips_hdf5_file,
             name='export-clips-hdf5-file'),
        
        path('update-recording-file-paths/',
             views.update_recording_file_paths,
             name='update-recording-file-paths'),
        path('delete-recordings/', views.delete_recordings,
             name='delete-recordings'),
        path('adjust-clips/', views.adjust_clips, name='adjust-clips'),
        path('delete-clips/', views.delete_clips, name='delete-clips'),
        path('create-clip-audio-files/', views.create_clip_audio_files,
             name='create-clip-audio-files'),
        path('delete-clip-audio-files/', views.delete_clip_audio_files,
             name='delete-clip-audio-files'),
        path('transfer-call-classifications/',
             views.transfer_call_classifications,
             name='transfer-call-classifications'),
    
        path('stations/', views.stations, name='stations'),
        path('stations/<name:station_name>/', views.station, name='station'),
        path('stations/<name:station_name>/clips/', views.station_clips,
             name='station-clips'),
    
        path('clips/', views.clips, name='clips'),
        path('clips/<int:clip_id>/', views.clip, name='clip'),
        path('clips/<int:clip_id>/annotations/<name:annotation_name>/',
             views.annotation, name='annotation'),
        
        path('annotations/<name:annotation_name>/', views.annotations,
             name='annotations'),

        path('presets/<name:preset_type_name>/json/', views.presets_json,
             name='presets-json'),
    
        path('jobs/<int:job_id>/', views.job, name='job'),
    
    ]


# The above set of Vesper URLs has evolved as needed, and is incomplete
# and (probably) inconsistent. The rest of this file contains notes
# regarding a more complete, consistent set of URLs.

# URLs are limited to a couple thousand characters, which limits the number
# of resources that can be specified by ID in GET requests. (GET requests
# can have bodies, but they should "have no semantic meaning to the request"
# according to https://groups.yahoo.com/neo/groups/rest-discuss/
# conversations/messages/9962, so the IDs can't simply be moved there.)
# So in the interest of simplicity, it might be best to support requests
# for batches of audios, annotations, etc. by clip IDs only in some sort of
# batch POST request, and not in GET requests.

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

    /recordings/123456/audio/<format>:
        Methods:
            GET:
                Query Parameters:
                    - channels=0,2,4-7
                    - start_index=10000
                    - end_index=20000
                Description:
                    Gets recording audio data.
            POST: >
                Appends audio data to a recording. The data are converted
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
                Creates a new clip. Both metadata and audio data are
                specified in request (or must we separate the two?).

    /clips/metadata/json:
        Methods:
            GET:
                Query Parameters:
                    - ids=1234,2345,3456
                    - station_mics=1
                    - detectors=1
                    - nights=20180412
                    - days=20180412
                    - annotations=Classification:AMRE
                Description:
                    Gets metadata for the specified clips.

    /clips/audio/<format>
        Methods:
            GET:
                Query Parameters:
                    - ids=1234,2345,3456
                    - station_mics=1
                    - detectors=1
                    - nights=20180412
                    - days=20180412
                    - annotations=Classification:AMRE
                Description:
                    Gets the audio data of the specified clips.

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

    /clips/123456/audio/<format>:
        Methods:
            GET: Gets the audio data of a clip.
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
            

Batch operations:

    /batch:
        Methods:
            POST: >
                Reads or writes a batch of resources, e.g. clip audios
                or annotations. The details of the operation, as well as
                any data to be written, are specified in the request body
                rather than in request query parameters.
'''
