from pathlib import Path
from urllib.parse import quote
import datetime
import itertools
import json
import logging

from django import forms, urls
from django.db import transaction
from django.db.models import F, Max, Min
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import (
    Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
    HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseServerError)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import numpy as np

from vesper.django.app.add_recording_audio_files_form import \
    AddRecordingAudioFilesForm
from vesper.django.app.adjust_clips_form import AdjustClipsForm
from vesper.django.app.classify_form import ClassifyForm
from vesper.django.app.clip_set_form import ClipSetForm
from vesper.django.app.delete_clips_form import DeleteClipsForm
from vesper.django.app.delete_recordings_form import DeleteRecordingsForm
from vesper.django.app.detect_form import DetectForm
from vesper.django.app.execute_deferred_actions_form import \
    ExecuteDeferredActionsForm
from vesper.django.app.export_clip_metadata_to_csv_file_form import \
    ExportClipMetadataToCsvFileForm
from vesper.django.app.export_clips_to_audio_files_form import \
    ExportClipsToAudioFilesForm
from vesper.django.app.export_clips_to_hdf5_file_form import \
    ExportClipsToHdf5FileForm
from vesper.django.app.import_metadata_form import ImportMetadataForm
from vesper.django.app.import_recordings_form import ImportRecordingsForm
from vesper.django.app.models import (
    AnnotationInfo, Clip, Job, Station, StringAnnotation)
from vesper.django.app.transfer_call_classifications_form import \
    TransferCallClassificationsForm
from vesper.django.app.refresh_recording_audio_file_paths_form import \
    RefreshRecordingAudioFilePathsForm
from vesper.old_bird.export_clip_counts_csv_file_form import \
    ExportClipCountsCsvFileForm as OldBirdExportClipCountsCsvFileForm
from vesper.old_bird.import_clips_form import ImportClipsForm
from vesper.singletons import (
    archive, clip_manager, job_manager, preference_manager, preset_manager)
from vesper.util.bunch import Bunch
from vesper.util.byte_buffer import ByteBuffer
import vesper.django.app.model_utils as model_utils
import vesper.ephem.ephem_utils as ephem_utils
import vesper.external_urls as external_urls
from vesper.old_bird.add_old_bird_clip_start_indices_form import \
    AddOldBirdClipStartIndicesForm
import vesper.old_bird.export_clip_counts_csv_file_utils as \
    old_bird_export_clip_counts_csv_file_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.calendar_utils as calendar_utils
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils
import vesper.version as version


class HttpError(Exception):

    def __init__(self, status_code, reason=None):
        self._status_code = status_code
        self._reason = reason

    @property
    def http_response(self):
        return HttpResponse(status=self._status_code, reason=self._reason)


# A note about UTC vs. local times on client and server:
#
# Our preferred approach to timekeeping is to work with UTC times as
# much as possible, and to convert those times to local times only
# when needed, for example for display to the user.
#
# At present (January 2017), however, we send only local times from
# server to client. I would prefer to send UTC times to the client and
# have it convert them to local times, but it appears that there is not
# yet a reliable way to do that in some browsers. According to
# https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/
# Global_Objects/Date/toLocaleTimeString, though, help is on its way.
# When it becomes easy enough to convert UTC times to local times in
# all of the major browsers we should switch to that practice.


# Default navbar data for read-write archives.
# Note that as of 2016-07-19, nested navbar dropdowns do not work.
# The generated HTML looks right to me so the problem may be a
# Bootstrap limitation.
_DEFAULT_NAVBAR_DATA_READ_WRITE = yaml_utils.load(f'''

- name: File
  dropdown:

      - name: Import metadata
        url_name: import-metadata
        
      - name: Import recordings
        url_name: import-recordings
        
      - separator
      
      # - name: Export clip counts to CSV file
      #   url_name: export-clip-counts-csv-file
 
      - name: Export clip metadata to CSV file
        url_name: export-clip-metadata-to-csv-file
        
      - name: Export clips to audio files
        url_name: export-clips-to-audio-files
        
      # - name: Export clips to HDF5 file
      #   url_name: export-clips-to-hdf5-file
      
- name: Edit
  dropdown:
 
      - name: Delete recordings
        url_name: delete-recordings
 
      - name: Delete clips
        url_name: delete-clips
        
- name: View
  dropdown:

      - name: View clip calendar
        url_name: clip-calendar

      - name: View clip album
        url_name: clip-album

- name: Process
  dropdown:
  
      - name: Detect
        url_name: detect
     
      - name: Classify
        url_name: classify
      
      - name: Transfer call classifications
        url_name: transfer-call-classifications
 
      - name: Execute deferred actions
        url_name: execute-deferred-actions
        
      # - name: Adjust clips
      #   url_name: adjust-clips
        
- name: Admin
  dropdown:
 
      - name: Refresh recording audio file paths
        url_name: refresh-recording-audio-file-paths
        
      # - name: Add recording audio files
      #   url_name: add-recording-audio-files
        
      # - name: Add Old Bird clip start indices
      #   url_name: add-old-bird-clip-start-indices
        
      - name: Create clip audio files
        url_name: create-clip-audio-files
        
      - name: Delete clip audio files
        url_name: delete-clip-audio-files
   
- name: Help
  dropdown:
  
      - name: About Vesper
        url_name: about-vesper
        
      - name: View documentation
        url: {external_urls.documentation_url}
        
''')


# Default navbar data for read-only archives.
_DEFAULT_NAVBAR_DATA_READ_ONLY = yaml_utils.load(f'''

- name: View
  dropdown:

      - name: View clip calendar
        url_name: clip-calendar

      - name: View clip album
        url_name: clip-album

- name: Help
  dropdown:
  
      - name: About Vesper
        url_name: about-vesper
        
      - name: View documentation
        url: {external_urls.documentation_url}
        
''')


def _create_navbar_items():
    preferences = preference_manager.instance.preferences
    default_data = _get_default_navbar_data()
    data = preferences.get('navbar', default_data)
    return _create_navbar_items_aux(data)


def _get_default_navbar_data():
    if settings.ARCHIVE_READ_ONLY:
        return _DEFAULT_NAVBAR_DATA_READ_ONLY
    else:
        return _DEFAULT_NAVBAR_DATA_READ_WRITE
        
    
def _create_navbar_items_aux(data):
    return tuple(_create_navbar_item(d) for d in data)


def _create_navbar_item(data):
    if isinstance(data, str):
        if data == 'separator':
            return _create_navbar_separator_item()
        else:
            return _create_navbar_unrecognized_item()
    elif 'url_name' in data or 'url' in data:
        return _create_navbar_link_item(data)
    elif 'dropdown' in data:
        return _create_navbar_dropdown_item(data)
    else:
        return _create_navbar_unrecognized_item(data)


def _create_navbar_separator_item():
    return Bunch(type='separator')


def _create_navbar_unrecognized_item():
    return Bunch(type='unrecognized')

    
def _create_navbar_link_item(data):
    name = data['name']
    url = _get_navbar_link_url(data)
    return Bunch(type='link', name=name, url=url)


def _get_navbar_link_url(data):
    if 'url_name' in data:
        return urls.reverse_lazy(data['url_name'])
    else:
        return data['url']


def _create_navbar_dropdown_item(data):
    name = data['name']
    items = _create_navbar_items_aux(data['dropdown'])
    return Bunch(type='dropdown', name=name, items=items)


def _create_navbar_right_items(request):

    if settings.ARCHIVE_READ_ONLY:
        return []
    
    else:
        
        user = request.user
    
        # The value of the "next" parameter is a URL that is embedded in the
        # URL of which the "next" parameter is a part. We must quote the
        # embedded URL to ensure that it does not interfere with parsing the
        # containing URL.
        query = '?next=' + quote(request.get_full_path())
    
        if user.is_authenticated:
            # user is logged in
    
            item = Bunch(
                name=user.username,
                type='dropdown',
                items=[
                    Bunch(
                        name='Log out',
                        type='link',
                        url='/logout/' + query)
                ])
    
        else:
            # user is not logged in
    
            item = Bunch(
                name='Log in',
                type='link',
                url='/login/' + query)
    
        return [item]


_navbar_items = _create_navbar_items()


_ONE_DAY = datetime.timedelta(days=1)
_GET_AND_HEAD = ('GET', 'HEAD')


def index(request):
    return redirect(reverse('clip-calendar'))


@login_required
@csrf_exempt
def detect(request):

    if request.method in _GET_AND_HEAD:
        form = DetectForm()

    elif request.method == 'POST':

        form = DetectForm(request.POST)

        if form.is_valid():
            command_spec = _create_detect_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Detect', form=form)

    return render(request, 'vesper/detect.html', context)


def _create_detect_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'detect',
        'arguments': {
            'detectors': data['detectors'],
            'stations': data['stations'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'schedule': data['schedule'],
            # 'create_clip_files': data['create_clip_files'],
            'defer_clip_creation': data['defer_clip_creation']
        }
    }


def _start_job(command_spec, user):
    job_id = job_manager.instance.start_job(command_spec, user)
    url = urls.reverse('job', args=[job_id])
    return HttpResponseRedirect(url)


def _create_template_context(
        request, active_navbar_item='', **kwargs):

    kwargs.update(
        navbar_items=_navbar_items,
        navbar_right_items=_create_navbar_right_items(request),
        active_navbar_item=active_navbar_item)

    return kwargs


def _render_coming_soon(request, action, message):
    context = _create_template_context(request, action, message=message)
    return render(request, 'vesper/coming-soon.html', context)


@login_required
@csrf_exempt
def classify(request):

    if request.method in _GET_AND_HEAD:
        form = ClassifyForm()

    elif request.method == 'POST':

        form = ClassifyForm(request.POST)

        if form.is_valid():
            command_spec = _create_classify_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Classify', form=form)

    return render(request, 'vesper/classify.html', context)


def _create_classify_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'classify',
        'arguments': {
            'classifier': data['classifier'],
            'annotation_name': 'Classification',
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'tag': data['tag']
        }
    }


@login_required
@csrf_exempt
def execute_deferred_actions(request):

    if request.method in _GET_AND_HEAD:
        form = ExecuteDeferredActionsForm()

    elif request.method == 'POST':

        form = ExecuteDeferredActionsForm(request.POST)

        if form.is_valid():
            command_spec = _create_execute_deferred_actions_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Import', form=form)

    return render(request, 'vesper/execute-deferred-actions.html', context)


def _create_execute_deferred_actions_command_spec(form):

    return {
        'name': 'execute_deferred_actions',
        'arguments': {}
    }


@login_required
@csrf_exempt
def old_bird_export_clip_counts_csv_file(request):

    if request.method in _GET_AND_HEAD:
        form = OldBirdExportClipCountsCsvFileForm()

    elif request.method == 'POST':

        form = OldBirdExportClipCountsCsvFileForm(request.POST)

        if form.is_valid():

            # TODO: Create the CSV file with a command (i.e. in a separate
            # process) rather than in the view?

            utils = old_bird_export_clip_counts_csv_file_utils

            d = form.cleaned_data

            file_name = utils.get_clip_counts_csv_file_name(
                d['file_name'], d['detector'], d['station_mic'],
                d['start_date'], d['end_date'])

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = \
                'attachment; filename="{}"'.format(file_name)

            utils.write_clip_counts_csv_file(
                response, d['detector'], d['station_mic'], d['start_date'],
                d['end_date'])

            return response

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Export', form=form)

    return render(
        request, 'vesper/old-bird-export-clip-counts-csv-file.html', context)


@login_required
@csrf_exempt
def export_clip_metadata_to_csv_file(request):

    if request.method in _GET_AND_HEAD:
        form = ExportClipMetadataToCsvFileForm()

    elif request.method == 'POST':

        form = ExportClipMetadataToCsvFileForm(request.POST)

        if form.is_valid():
            command_spec = \
                _create_export_clip_metadata_to_csv_file_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Export', form=form)

    return render(
        request, 'vesper/export-clip-metadata-to-csv-file.html', context)


def _create_export_clip_metadata_to_csv_file_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clip Metadata CSV File Exporter',
                'arguments': {
                    'output_file_path': data['output_file_path'],
                }
            },
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
    }


@login_required
@csrf_exempt
def export_clips_to_audio_files(request):

    if request.method in _GET_AND_HEAD:
        form = ExportClipsToAudioFilesForm()

    elif request.method == 'POST':

        form = ExportClipsToAudioFilesForm(request.POST)

        if form.is_valid():
            command_spec = \
                _create_export_clips_to_audio_files_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Export', form=form)

    return render(request, 'vesper/export-clips-to-audio-files.html', context)


def _create_export_clips_to_audio_files_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clip Audio Files Exporter',
                'arguments': {
                    'output_dir_path': data['output_dir_path'],
                    'clip_file_name_formatter': {
                        'name': 'Simple Clip File Name Formatter',
                        # TODO: Add arguments for format control?
                    }
                }
            },
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
    }


@login_required
@csrf_exempt
def export_clips_to_hdf5_file(request):

    if request.method in _GET_AND_HEAD:
        form = ExportClipsToHdf5FileForm()

    elif request.method == 'POST':

        form = ExportClipsToHdf5FileForm(request.POST)

        if form.is_valid():
            command_spec = _create_export_clips_to_hdf5_file_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Export', form=form)

    return render(request, 'vesper/export-clips-to-hdf5-file.html', context)


def _create_export_clips_to_hdf5_file_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clips HDF5 File Exporter',
                'arguments': {
                    'output_file_path': data['output_file_path'],
                }
            },
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
    }


@login_required
@csrf_exempt
def refresh_recording_audio_file_paths(request):

    if request.method in _GET_AND_HEAD:
        form = RefreshRecordingAudioFilePathsForm()

    elif request.method == 'POST':

        form = RefreshRecordingAudioFilePathsForm(request.POST)

        if form.is_valid():
            command_spec = \
                _create_refresh_recording_audio_file_paths_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(
        request, 'vesper/refresh-recording-audio-file-paths.html', context)


def _create_refresh_recording_audio_file_paths_command_spec(form):

    return {
        'name': 'refresh_recording_audio_file_paths',
        'arguments': {}
    }


@login_required
@csrf_exempt
def delete_recordings(request):

    if request.method in _GET_AND_HEAD:
        form = DeleteRecordingsForm()

    elif request.method == 'POST':

        form = DeleteRecordingsForm(request.POST)

        if form.is_valid():
            command_spec = _create_delete_recordings_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/delete-recordings.html', context)


def _create_delete_recordings_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'delete_recordings',
        'arguments': {
            'stations': data['stations'],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
    }


@login_required
@csrf_exempt
def delete_clips(request):

    if request.method in _GET_AND_HEAD:
        form = DeleteClipsForm()

    elif request.method == 'POST':

        form = DeleteClipsForm(request.POST)

        if form.is_valid():
            command_spec = _create_delete_clips_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/delete-clips.html', context)


def _create_delete_clips_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'delete_clips',
        'arguments': {
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'retain_count': data['retain_count']
        }
    }


@login_required
@csrf_exempt
def adjust_clips(request):

    if request.method in _GET_AND_HEAD:
        form = AdjustClipsForm()

    elif request.method == 'POST':

        form = AdjustClipsForm(request.POST)

        if form.is_valid():
            command_spec = _create_adjust_clips_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/adjust-clips.html', context)


def _create_adjust_clips_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'adjust_clips',
        'arguments': {
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'duration': data['duration'],
            'annotation_name': data['annotation_name']
        }
    }


@login_required
@csrf_exempt
def create_clip_audio_files(request):

    if request.method in _GET_AND_HEAD:
        form = ClipSetForm()

    elif request.method == 'POST':

        form = ClipSetForm(request.POST)

        if form.is_valid():
            command_spec = _create_create_clip_audio_files_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/create-clip-audio-files.html', context)


def _create_create_clip_audio_files_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'create_clip_audio_files',
        'arguments': {
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
        }
    }


@login_required
@csrf_exempt
def delete_clip_audio_files(request):

    if request.method in _GET_AND_HEAD:
        form = ClipSetForm()

    elif request.method == 'POST':

        form = ClipSetForm(request.POST)

        if form.is_valid():
            command_spec = _create_delete_clip_audio_files_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/delete-clip-audio-files.html', context)


def _create_delete_clip_audio_files_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'delete_clip_audio_files',
        'arguments': {
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'classification': data['classification'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
        }
    }


@login_required
@csrf_exempt
def transfer_call_classifications(request):

    if request.method in _GET_AND_HEAD:
        form = TransferCallClassificationsForm()

    elif request.method == 'POST':

        form = TransferCallClassificationsForm(request.POST)

        if form.is_valid():
            command_spec = \
                _create_transfer_call_classifications_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(
        request, 'vesper/transfer-call-classifications.html', context)


def _create_transfer_call_classifications_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'transfer_call_classifications',
        'arguments': {
            'source_detector': data['source_detector'],
            'target_detector': data['target_detector'],
            'station_mics': data['station_mics'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
        }
    }


def stations(request):
    stations = Station.objects.order_by('name')
    context = dict(stations=stations)
    return render(request, 'vesper/stations.html', context)


def station(request, station_name):
    station = Station.objects.get(name=station_name)
    context = dict(station=station)
    return render(request, 'vesper/station.html', context)


def station_clips(request, station_name):
    station = Station.objects.get(name=station_name)
    first_time, last_time = _get_station_clip_start_time_extrema(station)
    context = dict(
        station=station,
        first_time=str(first_time),
        last_time=str(last_time))
    return render(request, 'vesper/station-clips.html', context)


def _get_station_clip_start_time_extrema(station):
    # TODO: How expensive is the clip query below? I believe it requires a
    # join on three tables, namely Clip, Recording, and StationDevice.
    clips = Clip.objects.filter(recording__station_recorder__station=station)
    times = clips.aggregate(
        first_time=Min('start_time'),
        last_time=Max('start_time'))
    return (times['first_time'], times['last_time'])


def clips(request):
    first_time, last_time = _get_clip_start_time_extrema()
    context = dict(
        station=station,
        first_time=str(first_time),
        last_time=str(last_time))
    return render(request, 'vesper/clips.html', context)


def _get_clip_start_time_extrema():
    times = Clip.objects.aggregate(
        first_time=Min('start_time'),
        last_time=Max('start_time'))
    return (times['first_time'], times['last_time'])


def clip(request, clip_id):
    clip = Clip.objects.get(id=clip_id)
    context = dict(
        clip=clip,
        start_time=str(clip.start_time))
    return render(request, 'vesper/clip.html', context)


def clip_wav(request, clip_id):
    
    clip = get_object_or_404(Clip, pk=clip_id)
    
    content_type = 'audio/wav'
    
    try:
        content = clip_manager.instance.get_audio_file_contents(
            clip, content_type)
        
    except Exception as e:
        logger = logging.getLogger('django.server')
        logger.error((
            'Attempt to get audio file contents for clip "{}" failed with '
            '{} exception. Exception message was: {}').format(
                str(clip), e.__class__.__name__, str(e)))
        return HttpResponseServerError()

    response = HttpResponse()
    response.write(content)
    response['Content-Type'] = content_type
    response['Content-Length'] = len(content)
    return response


def presets_json(request, preset_type_name):

    preset_manager.instance.reload_presets()

    if request.method in _GET_AND_HEAD:
        content = _get_presets_json(preset_type_name)
        return HttpResponse(content, content_type='application/json')

    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)


def _get_presets_json(preset_type_name):

    """
    Gets all presets of the specified type as JSON.

    The returned JSON is a list of [<preset path>, <preset JSON>]
    pairs, where the preset path is the path relative to the directory
    for the preset type.
    """

    presets = preset_manager.instance.get_flattened_presets(preset_type_name)
    presets = [(path, preset.camel_case_data) for path, preset in presets]
    return json.dumps(presets)


@csrf_exempt
def annotations_json(request, clip_id):

    if request.method in _GET_AND_HEAD:
        content = _get_annotations_json(clip_id)
        return HttpResponse(content, content_type='application/json')

    elif request.method == 'POST':

        if request.user.is_authenticated:

            try:
                content = _get_request_body_as_json(request)
            except HttpError as e:
                return e.http_response

            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                return HttpResponseBadRequest(
                    reason='Could not decode request JSON')

            # TODO: Typecheck JSON?

            with archive_lock.atomic():
                with transaction.atomic():

                    clip = get_object_or_404(Clip, pk=clip_id)

                    for name, value in content.items():

                        # We respond with a 404 (Not Found) client error if
                        # the named `AnnotationInfo` does not already exist.
                        # This assumes that an `AnnotationInfo` is created
                        # explicitly by a request at some other URL, not
                        # implicitly by naming a nonexistent `AnnotationInfo`
                        # at this URL.
                        info = get_object_or_404(AnnotationInfo, name=name)

                        user = request.user

                        if value is None:
                            model_utils.delete_clip_annotation(
                                clip, info, creating_user=user)

                        else:
                            model_utils.annotate_clip(
                                clip, info, value, creating_user=user)

            return HttpResponse()

        else:
            # user not logged in

            return HttpResponseForbidden()

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))


def _parse_json_request_body(request):
    return {}


def _get_annotations_json(clip_id):
    annotations = _get_annotations(clip_id)
    return json.dumps(annotations)


def _get_annotations(clip_id):
    
    annotations = StringAnnotation.objects.filter(
        clip_id=clip_id
    ).annotate(name=F('info__name'))

    return dict((a.name, a.value) for a in annotations)


@csrf_exempt
def annotation(request, clip_id, annotation_name):

    name = annotation_name

    if request.method in _GET_AND_HEAD:
        info = get_object_or_404(AnnotationInfo, name=name)
        annotation = get_object_or_404(
            StringAnnotation, clip__id=clip_id, info=info)
        response = HttpResponse()
        response.write(annotation.value)
        return response

    elif request.method == 'PUT':

        if request.user.is_authenticated:

            clip = get_object_or_404(Clip, pk=clip_id)
            info = get_object_or_404(AnnotationInfo, name=name)

            # TODO: If the request body is not plain text, we should
            # respond with an appropriate HTTP error, not just raise
            # an exception, which results in an internal server error
            # (500) response.
            value = _get_request_body_as_text(request).strip()

            model_utils.annotate_clip(
                clip, info, value, creating_user=request.user)

            return HttpResponse()

        else:
            # user not logged in

            return HttpResponseForbidden()


    elif request.method == 'DELETE':

        if request.user.is_authenticated:

            clip = get_object_or_404(Clip, pk=clip_id)
            info = get_object_or_404(AnnotationInfo, name=name)

            model_utils.delete_clip_annotation(
                clip, info, creating_user=request.user)

            return HttpResponse()

        else:
            # user not logged in

            return HttpResponseForbidden()

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'PUT', 'DELETE'))


def _get_request_body_as_text(request):

    # According to rfc6657, us-ascii is the default charset for the
    # text/plain media type.

    return _get_request_body(request, 'text/plain', 'us-ascii')


def _get_request_body(request, content_type_name, default_charset_name):

    content_type = _parse_content_type(request.META['CONTENT_TYPE'])

    # Make sure content type is text/plain.
    if content_type.name != content_type_name:
        raise HttpError(
            status_code=415,
            reason='Request content type must be {}'.format(content_type_name))

    charset = content_type.params.get('charset', default_charset_name)

    return request.body.decode(charset)


# TODO: Does Django already include functions for parsing HTTP headers?
# If so, I couldn't find it.
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


@csrf_exempt
def batch_read_clip_audios(request):
    
    if request.method == 'POST':
        
        
        # Parse request content JSON.
        
        try:
            content = _get_request_body_as_json(request)
        except HttpError as e:
            return e.http_response

        try:
            content = json.loads(content)
        except json.JSONDecodeError as e:
            return HttpResponseBadRequest(
                reason='Could not decode request JSON')


        # Get requested clip audios.
        
        clip_ids = content['clip_ids']
        
        clips = [get_object_or_404(Clip, pk=i) for i in clip_ids]

        content_type = 'audio/wav'
        
        audios = []
        
        for clip in clips:
            
            try:
                audio = clip_manager.instance.get_audio_file_contents(
                    clip, content_type)
                
            except Exception as e:
                logger = logging.getLogger('django.server')
                logger.error((
                    'Attempt to get audio file contents for clip "{}" failed '
                    'with {} exception. Exception message was: {}').format(
                        str(clip), e.__class__.__name__, str(e)))
                return HttpResponseServerError()
            
            audios.append(audio)
            
            
        # Concatenate alternating binary audio sizes and audios to make
        # response content.
        audio_sizes = [_get_uint32_bytes(len(a)) for a in audios]
        pairs = zip(audio_sizes, audios)
        parts = itertools.chain.from_iterable(pairs)
        content = b''.join(parts)
        
        # Construct response
        return HttpResponse(content, content_type='application/octet-stream')
    
    else:
        return HttpResponseNotAllowed(['POST'])        


def _get_uint32_bytes(i):
    return np.array([i], dtype=np.dtype('<u4')).tobytes()


@csrf_exempt
def batch_read_clip_annotations(request):
    
    if request.method == 'POST':
        
        try:
            content = _get_request_body_as_json(request)
        except HttpError as e:
            return e.http_response

        try:
            content = json.loads(content)
        except json.JSONDecodeError as e:
            return HttpResponseBadRequest(
                reason='Could not decode request JSON')

        clip_ids = content['clip_ids']
        annotations = dict((i, _get_annotations(i)) for i in clip_ids)
        content = json.dumps(annotations)       
        return HttpResponse(content, content_type='application/json')
    
    else:
        return HttpResponseNotAllowed(['POST'])        
        
        
@csrf_exempt
def annotations(request, annotation_name):

    '''
    This view expects a request body that is UTF-8 encoded JSON like:

        { "value": null, "clip_ids": [1, 2, 3, 4, 5] }
    '''

    if request.method == 'POST':

        if request.user.is_authenticated:

            try:
                content = _get_request_body_as_json(request)
            except HttpError as e:
                return e.http_response

            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                return HttpResponseBadRequest(
                    reason='Could not decode request JSON')

            # TODO: Typecheck JSON?
            value = content['value']
            clip_ids = content['clip_ids']

            # We lock the archive just once for all of the clips that
            # we process, rather than once for each clip. This means
            # that we may hold the lock for several seconds, during
            # which no other threads or processes can hold it. This
            # method is several times faster this way, and since it
            # is typically invoked interactively, the improved
            # performance is especially important.
            with archive_lock.atomic():
                with transaction.atomic():

                    info = get_object_or_404(
                        AnnotationInfo, name=annotation_name)

                    # TODO: Try to speed up the following, which currently
                    # takes several seconds per thousand clips. Perhaps we
                    # don't need for Django to create Clip instances for us,
                    # but instead can use raw SQL to query the
                    # vesper_string_annotation table just once to get the
                    # information we need to decide what updates are needed,
                    # and then a second time to perform the updates.

                    for clip_id in clip_ids:

                        clip = get_object_or_404(Clip, pk=clip_id)
                        user = request.user

                        if value is None:
                            model_utils.delete_clip_annotation(
                                clip, info, creating_user=user)

                        else:
                            model_utils.annotate_clip(
                                clip, info, value, creating_user=user)

            return HttpResponse()

        else:

            return HttpResponseForbidden()

    else:
        return HttpResponseNotAllowed(['POST'])


def _get_request_body_as_json(request):

    # According to rfc4627, utf-8 is the default charset for the
    # application/json media type.

    return _get_request_body(request, 'application/json', 'utf-8')


def clip_calendar(request):

    '''
    We should display an error message when an archive contains no
    station/mics or detectors, since in that case no clip calendar
    can be displayed.
    
    Otherwise, we should display a clip calendar. The clip calendar's
    station/mic and detector, and classification value spec should be set
    to those specified in the URL, to those specified in the
    preference file, or to the first ones in a list of all of the
    valid options, in that order. If a station/mic, detector, or
    classification value spec is specified in the URL or preferences
    file that does not exist, we should display an error message in
    a blocking popup dialog.
    
    Example error messages:
    
    This page can't display a clip calendar since this archive contains
    no station/microphone pairs. Please add one or more station/microphone
    pairs to the archive and then visit this page again.
    
    Warning: the URL for this page specifies a station/mic "Bobo / 21c"
    that does not exist in this archive. The page displays data for
    another station/mic instead.
        
    * Get the archive's station/mics and detectors. If there are no
      station/mics or no detectors, display an error message.
      
    * Get the station/mic to display a calendar for. If the station/mic
      differs from the one requested in either the URL or the user
      preferences, remember the requested station/mic.
      
    * Get the detector to display a calendar for. If the detector differs
      from the one requested in either the URL or the user preferences,
      remember the requested detector.
      
    * Get the classification value spec to display a calendar for.
    
    * Get the UI names of the archive's station/mics and detectors and
      the archive's classification value specs.
    
    * Get the UI name of the station/mic to display a calendar for.
      
    * Get the UI name of the detector to display a calendar for.
      
    * Get whatever other data are needed for the specified
      calendar and display it.
    '''
        
    params = request.GET
    
    archive_ = archive.instance

    preference_manager.instance.reload_preferences()
    preferences = preference_manager.instance.preferences

    message = _check_for_stations_detectors_and_classification_annotation(
        'clip calendar')
    
    if message is not None:
        
        context = _create_template_context(
            request, 'View', error_message=message)
        
        return _render_clip_calendar(request, context)

    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pair = _get_calendar_query_object(
        sm_pairs, 'station_mic', params, preferences, name_getter=get_ui_name)

    detector_name = _get_calendar_query_field_value(
        'detector', params, preferences)
    detector = archive_.get_processor(detector_name)
    
    annotation_name = 'Classification'
    annotation_ui_value_specs = \
        archive_.get_visible_string_annotation_ui_value_specs(annotation_name)
    annotation_ui_value_spec = _get_string_annotation_ui_value_spec(
        annotation_ui_value_specs, params, preferences)

    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]
    sm_pair_ui_name = None if sm_pair is None else get_ui_name(sm_pair)

    detectors = archive_.get_visible_processors_of_type('Detector')
    detector_ui_names = [archive_.get_processor_ui_name(d) for d in detectors]
    detector_ui_name = archive_.get_processor_ui_name(detector)
    
    annotation_name, annotation_value = \
        _get_string_annotation_info(annotation_name, annotation_ui_value_spec)
    periods_json = _get_periods_json(
        sm_pair, detector, annotation_name, annotation_value)

    context = _create_template_context(
        request, 'View',
        station_mic_names=sm_pair_ui_names,
        station_mic_name=sm_pair_ui_name,
        detector_names=detector_ui_names,
        detector_name=detector_ui_name,
        classifications=annotation_ui_value_specs,
        classification=annotation_ui_value_spec,
        periods_json=periods_json)

    return _render_clip_calendar(request, context)


def _check_for_stations_detectors_and_classification_annotation(view_name):
    
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    
    if len(sm_pairs) == 0:
        # archive contains no station/mics
        
        return _create_missing_entities_text(
            view_name, 'station/microphone pairs')
        
    detectors = archive.instance.get_processors_of_type('Detector')
    
    if len(detectors) == 0:
        # archive contains no detectors
        
        return _create_missing_entities_text(view_name, 'detectors')
        
    try:
        AnnotationInfo.objects.get(name='Classification')
        
    except AnnotationInfo.DoesNotExist:
        # archive contains no "Classification" annotation
        
        return _create_missing_entities_text(
            view_name, '"Classification" annotation')
                   
    return None
        

def _create_missing_entities_text(view_name, entities_text):
    
    return (
        f'<p>This page can&#39t display a {view_name} since this archive '
        f'contains no {entities_text}.</p>'
        '<p>See the '
        f'<a href="{external_urls.tutorial_url}">Vesper tutorial</a> '
        'for an example of how to import metadata  and recordings into an '
        'archive.</p>')


def _render_clip_calendar(request, context):
    return render(request, 'vesper/clip-calendar.html', context)


def _get_calendar_query_object(
        objects, type_name, params, preferences, name_getter=lambda o: o.name):

    if len(objects) == 0:
        raise Http404('Archive contains no {} objects.'.format(type_name))

    else:

        object_name = \
            _get_calendar_query_field_value(type_name, params, preferences)

        if object_name is not None:
            # object name specified in `params` or `preferences`

            objects_dict = dict((name_getter(o), o) for o in objects)

            try:
                return objects_dict[object_name]
            except KeyError:
                return objects[0]

        else:
            # object name not specified in `params` or `preferences`

            return objects[0]


def _get_calendar_query_field_value(field_name, params, preferences):
    try:
        return params[field_name]
    except KeyError:
        return preferences.get('calendar_defaults.' + field_name)


def _get_string_annotation_ui_value_spec(
        annotation_ui_value_specs, params, preferences):

    archive_ = archive.instance
    
    spec = _get_calendar_query_field_value(
        'classification', params, preferences)
    
    spec = archive_.get_string_annotation_ui_value('Classification', spec)

    if spec is None or spec not in annotation_ui_value_specs:
        spec = archive_.STRING_ANNOTATION_VALUE_ANY_OR_NONE

    return spec


def _get_string_annotation_info(annotation_name, annotation_ui_value_spec):

    archive_ = archive.instance
    
    value_spec = archive_.get_string_annotation_archive_value(
        annotation_name, annotation_ui_value_spec)
    
    if value_spec == archive_.STRING_ANNOTATION_VALUE_ANY_OR_NONE:
        
        # We return an `annotation_name` of `None` to denote all clips.
        annotation_name = None
        annotation_value = None

    else:

        if value_spec == archive_.STRING_ANNOTATION_VALUE_NONE:
            annotation_value = None
        else:
            annotation_value = value_spec

    return annotation_name, annotation_value


def _get_periods_json(
        sm_pair, detector, annotation_name=None, annotation_value=None):

    if sm_pair is None or detector is None:
        return '[]'

    else:

        station, mic_output = sm_pair

        clip_counts = model_utils.get_clip_counts(
            station, mic_output, detector, annotation_name=annotation_name,
            annotation_value=annotation_value)

        dates = sorted(list(clip_counts.keys()))
        periods = calendar_utils.get_calendar_periods(dates)

        return calendar_utils.get_calendar_periods_json(periods, clip_counts)


def night(request):

    # TODO: Combine this view with `clip_album` view.

    # TODO: Check URL query items.
    params = request.GET
    
    archive_ = archive.instance

    # Reload presets and preferences to make sure we have the latest.
    # TODO: For efficiency's sake, be more selective about what we reload.
    # We might reload only presets of specified types, for example.
    preset_manager.instance.reload_presets()
    preference_manager.instance.reload_preferences()
    preferences = preference_manager.instance.preferences

    sm_pair_ui_name = params['station_mic']
    sm_pairs = model_utils.get_station_mic_output_pairs_dict()
    station, mic_output = sm_pairs[sm_pair_ui_name]
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]
    
    detector_name = params['detector']
    detector = archive_.get_processor(detector_name)
    detector_ui_name = archive_.get_processor_ui_name(detector)
    detectors = archive_.get_visible_processors_of_type('Detector')
    detector_ui_names = [archive_.get_processor_ui_name(d) for d in detectors]
    
    annotation_name = 'Classification'
    annotation_ui_value_specs = \
        archive_.get_visible_string_annotation_ui_value_specs(annotation_name)
    annotation_value_spec = params['classification']
    annotation_name, annotation_value = \
        _get_string_annotation_info(annotation_name, annotation_value_spec)

    date_string = params['date']
    date = time_utils.parse_date(*date_string.split('-'))

    solar_event_times_json = _get_solar_event_times_json(station, date)

    time_interval = station.get_night_interval_utc(date)
    recordings = model_utils.get_recordings(station, mic_output, time_interval)
    recordings_json = _get_recordings_json(recordings, station)

    clips = model_utils.get_clips(
        station, mic_output, detector, date, annotation_name, annotation_value)
    clips_json = _get_clips_json(clips, station)

    settings_presets_json = _get_presets_json('Clip Album Settings')
    commands_presets_json = _get_presets_json('Clip Album Commands')

    settings_preset_path = \
        preferences.get('default_presets.Clip Album Settings')
    commands_preset_path = \
        preferences.get('default_presets.Clip Album Commands')

    context = _create_template_context(
        request, 'View',
        station_mic_names=sm_pair_ui_names,
        station_mic_name=sm_pair_ui_name,
        detector_names=detector_ui_names,
        detector_name=detector_ui_name,
        classifications=annotation_ui_value_specs,
        classification=annotation_value_spec,
        date=date_string,
        solar_event_times_json=solar_event_times_json,
        recordings_json=recordings_json,
        clips_json=clips_json,
        settings_presets_json=settings_presets_json,
        settings_preset_path=settings_preset_path,
        commands_presets_json=commands_presets_json,
        commands_preset_path=commands_preset_path,
        archive_read_only=settings.ARCHIVE_READ_ONLY)

    return render(request, 'vesper/night.html', context)


def _get_solar_event_times_json(station, night):

    lat = station.latitude
    lon = station.longitude

    if lat is None or lon is None:
        return 'null'

    else:
        # have station latitude and longitude

        # See note near the top of this file about why we send local
        # instead of UTC times to clients.

        utc_to_local = station.utc_to_local

        times = {}

        # TODO: Fix issue 85 and then simplify the following code.

        def get(e):
            return _get_solar_event_time(e, lat, lon, night, utc_to_local)

        times['sunset'] = get('Sunset')
        times['civilDusk'] = get('Civil Dusk')
        times['nauticalDusk'] = get('Nautical Dusk')
        times['astronomicalDusk'] = get('Astronomical Dusk')

        next_day = night + _ONE_DAY

        def get(e):
            return _get_solar_event_time(e, lat, lon, next_day, utc_to_local)

        times['astronomicalDawn'] = get('Astronomical Dawn')
        times['nauticalDawn'] = get('Nautical Dawn')
        times['civilDawn'] = get('Civil Dawn')
        times['sunrise'] = get('Sunrise')

        return json.dumps(times)


def _get_solar_event_time(event, lat, lon, date, utc_to_local):

    utc_time = ephem_utils.get_event_time(event, lat, lon, date)

    if utc_time is None:
        # event does not exist for specified date (e.g. at high latitude)

        return None

    else:
        # event exists for specified date

        local_time = utc_to_local(utc_time)
        return _format_time(local_time)


def _get_recordings_json(recordings, station):

    # Make sure recordings are in order of increasing start time.
    recordings = sorted(recordings, key=lambda r: r.start_time)

    # See note near the top of this file about why we send local
    # instead of UTC times to clients.

    utc_to_local = station.utc_to_local
    recording_dicts = [
        _get_recording_dict(r, utc_to_local) for r in recordings]
    return json.dumps(recording_dicts)


def _get_recording_dict(recording, utc_to_local):

    start_time = _format_time(utc_to_local(recording.start_time))
    end_time = _format_time(utc_to_local(recording.end_time))

    return {
        'startTime': start_time,
        'endTime': end_time
    }


def _get_clips_json(clips, station):

    # See note near the top of this file about why we send local
    # instead of UTC times to clients.

    utc_to_local = station.utc_to_local
    clip_lists = [_get_clip_list(c, utc_to_local) for c in clips]
    result = json.dumps(clip_lists)
    return result


def _get_clip_list(c, utc_to_local):

    # See note about UTC and local times near the top of this file.
    start_time = _format_time(utc_to_local(c.start_time))

    return [c.id, c.start_index, c.length, c.sample_rate, start_time]


def _format_time(time):

    prefix = time.strftime('%Y-%m-%d %H:%M:%S')

    millis = int(round(time.microsecond / 1000.))
    millis = '{:03d}'.format(millis)
    while len(millis) != 0 and millis[-1] == '0':
        millis = millis[:-1]
    if len(millis) != 0:
        millis = '.' + millis

    time_zone = time.strftime('%Z')

    return prefix + millis + ' ' + time_zone


def _limit_index(index, min_index, max_index):
    if index < min_index:
        return min_index
    elif index > max_index:
        return max_index
    else:
        return index


def clip_album(request):

    # TODO: Combine this view with `night` view.

    # TODO: Check URL query items.
    params = request.GET
    
    archive_ = archive.instance

    # Reload presets and preferences to make sure we have the latest.
    # TODO: For efficiency's sake, be more selective about what we reload.
    # We might reload only presets of specified types, for example.
    preset_manager.instance.reload_presets()
    preference_manager.instance.reload_preferences()
    preferences = preference_manager.instance.preferences

    message = _check_for_stations_detectors_and_classification_annotation(
        'clip album')
    
    if message is not None:
        
        context = _create_template_context(
            request, 'View', error_message=message)
        
        return _render_clip_album(request, context)

    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pair = _get_calendar_query_object(
        sm_pairs, 'station_mic', params, preferences, name_getter=get_ui_name)
    sm_pair_ui_name = None if sm_pair is None else get_ui_name(sm_pair)
    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]

    detector_name = _get_calendar_query_field_value(
        'detector', params, preferences)
    detector = archive_.get_processor(detector_name)
    detectors = archive_.get_visible_processors_of_type('Detector')
    detector_ui_names = [archive_.get_processor_ui_name(d) for d in detectors]
    detector_ui_name = archive_.get_processor_ui_name(detector)
    
    annotation_name = 'Classification'
    annotation_ui_value_specs = \
        archive_.get_visible_string_annotation_ui_value_specs(annotation_name)
    annotation_ui_value_spec = _get_string_annotation_ui_value_spec(
        annotation_ui_value_specs, params, preferences)
    annotation_name, annotation_value = \
        _get_string_annotation_info(annotation_name, annotation_ui_value_spec)

    station, mic_output = sm_pair
    clips = model_utils.get_clips(
        station, mic_output, detector, None, annotation_name, annotation_value)
    clips_json = _get_clips_json(clips, station)

    settings_presets_json = _get_presets_json('Clip Album Settings')
    commands_presets_json = _get_presets_json('Clip Album Commands')

    settings_preset_path = \
        preferences.get('default_presets.Clip Album Settings')
    commands_preset_path = \
        preferences.get('default_presets.Clip Album Commands')

    context = _create_template_context(
        request, 'View',
        station_mic_names=sm_pair_ui_names,
        station_mic_name=sm_pair_ui_name,
        detector_names=detector_ui_names,
        detector_name=detector_ui_name,
        classifications=annotation_ui_value_specs,
        classification=annotation_ui_value_spec,
        solar_event_times_json='null',
        recordings_json='[]',
        clips_json=clips_json,
        settings_presets_json=settings_presets_json,
        settings_preset_path=settings_preset_path,
        commands_presets_json=commands_presets_json,
        commands_preset_path=commands_preset_path,
        archive_read_only=settings.ARCHIVE_READ_ONLY)

    return _render_clip_album(request, context)


def _render_clip_album(request, context):
    return render(request, 'vesper/clip-album.html', context)


@login_required
@csrf_exempt
def test_command(request):

    if request.method in _GET_AND_HEAD:
        form = forms.Form()

    elif request.method == 'POST':

        form = forms.Form(request.POST)

        if form.is_valid():
            print('form valid')
            command_spec = {'name': 'test'}
            return _start_job(command_spec, request.user)

        else:
            print('form invalid')

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    return render(request, 'vesper/test-command.html', {'form': form})


@login_required
@csrf_exempt
def import_metadata(request):

    if request.method in _GET_AND_HEAD:
        form = ImportMetadataForm()

    elif request.method == 'POST':

        form = ImportMetadataForm(request.POST)

        if form.is_valid():
            command_spec = _create_import_metadata_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Import', form=form)

    return render(request, 'vesper/import-metadata.html', context)


def _create_import_metadata_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'import',
        'arguments': {
            'importer': {
                'name': 'Metadata Importer',
                'arguments': {
                    'metadata': data['metadata']
                }
            }
        }
    }


@login_required
@csrf_exempt
def import_old_bird_clips(request):

    if request.method in _GET_AND_HEAD:
        form = ImportClipsForm()

    elif request.method == 'POST':

        form = ImportClipsForm(request.POST)

        if form.is_valid():
            command_spec = _create_import_old_bird_clips_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Import', form=form)

    return render(request, 'vesper/import-old-bird-clips.html', context)


def _create_import_old_bird_clips_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'import',
        'arguments': {
            'importer': {
                'name': 'Old Bird Clip Importer',
                'arguments': {
                    'paths': data['paths'],
                    'start_date': data['start_date'],
                    'end_date': data['end_date']
                }
            }
        }
    }


@login_required
@csrf_exempt
def import_recordings(request):

    if request.method in _GET_AND_HEAD:
        form = ImportRecordingsForm()

    elif request.method == 'POST':

        form = ImportRecordingsForm(request.POST)

        if form.is_valid():
            command_spec = _create_import_recordings_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Import', form=form)

    return render(request, 'vesper/import-recordings.html', context)


def _create_import_recordings_command_spec(form):

    data = form.cleaned_data

    # TODO: Put select element on form for station name aliases preset.
    data['station_name_aliases_preset'] = 'Station Name Aliases'

    return {
        'name': 'import',
        'arguments': {
            'importer': {
                'name': 'Recording Importer',
                'arguments': {
                    'paths': data['paths'],
                    'recursive': data['recursive'],
                    'recording_file_parser': {
                        'name': 'MPG Ranch Recording File Parser',
                        'arguments': {
                            'station_name_aliases_preset':
                                data['station_name_aliases_preset']
                        }
                    }
                }
            }
        }
    }


@login_required
@csrf_exempt
def add_recording_audio_files(request):

    if request.method in _GET_AND_HEAD:
        form = AddRecordingAudioFilesForm()

    elif request.method == 'POST':

        form = AddRecordingAudioFilesForm(request.POST)

        if form.is_valid():
            command_spec = _create_add_recording_audio_files_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Admin', form=form)

    return render(request, 'vesper/add-recording-audio-files.html', context)


def _create_add_recording_audio_files_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'add_recording_audio_files',
        'arguments': {
            'stations': data['stations'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'dry_run': data['dry_run']
        }
    }


@login_required
@csrf_exempt
def add_old_bird_clip_start_indices(request):

    if request.method in _GET_AND_HEAD:
        form = AddOldBirdClipStartIndicesForm()

    elif request.method == 'POST':

        form = AddOldBirdClipStartIndicesForm(request.POST)

        if form.is_valid():
            command_spec = \
                _create_add_old_bird_clip_start_indices_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Admin', form=form)

    return render(
        request, 'vesper/add-old-bird-clip-start-indices.html', context)


def _create_add_old_bird_clip_start_indices_command_spec(form):

    data = form.cleaned_data

    return {
        'name': 'add_old_bird_clip_start_indices',
        'arguments': {
            'stations': data['stations'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'dry_run': data['dry_run']
        }
    }


def job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    command_spec = json.loads(job.command)
    context = _create_template_context(
        request, job=job, command_name=command_spec['name'])
    return render(request, 'vesper/job.html', context)


@csrf_exempt
def about_vesper(request):

    if request.method not in _GET_AND_HEAD:
        return HttpResponseNotAllowed(_GET_AND_HEAD)

    context = _create_template_context(
        request, 'Help',
        version=version.full_version,
        source_code_url=external_urls.source_code_url,
        documentation_url=external_urls.documentation_url)

    return render(request, 'vesper/about-vesper.html', context)


# TODO: Handle authentication in `record` and `recordings` views.

# TODO: Record to the archive's first recording directory.
_RECORDING_DIR_PATH = Path('/Users/harold/Desktop/Vesper Recordings')
_SAMPLE_RATE = 24000
_CHANNEL_COUNT = 1
_SAMPLE_SIZE = 16

# TODO: Create new recording in database and use its ID.
_recording_id = 0


def record(request):

    if request.method in _GET_AND_HEAD:
        context = {}
        return render(request, 'vesper/record.html', context)

    elif request.method == 'POST':

        global _recording_id
        
        recording_id = _recording_id
        
        file_path = _get_recording_file_path(recording_id)
        
        audio_file_utils.write_empty_wave_file(
            file_path, _CHANNEL_COUNT, _SAMPLE_RATE, _SAMPLE_SIZE)
    
        content = json.dumps(dict(recordingId=recording_id))
        
        _recording_id += 1
        
        return HttpResponse(content, content_type='application/json')
 
    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))


def _get_recording_file_path(recording_id):
    file_name = f'{recording_id}.wav'
    return _RECORDING_DIR_PATH / file_name


def recordings(request):
    
    if request.method == 'POST':
        
        try:
            data = _parse_recordings_post_data(request.body)
        except Exception:
            return HttpResponseBadRequest(
                'Could not parse received recording data.')
             
        if data.action == 'append':
            
            recording_id = data.recording_id
            start_index = data.start_index
            samples = data.samples

            _write_recording_samples(recording_id, start_index, samples)
            
        else:
            print('stop')
        
        return HttpResponse()
    
    else:
        return HttpResponseNotAllowed(('POST',))


def _write_recording_samples(recording_id, start_index, samples):
    # _show_append_info(recording_id, start_index, samples)
    file_path = _get_recording_file_path(recording_id)
    audio_file_utils.write_wave_file_samples(file_path, start_index, samples)
                
            
def _show_append_info(recording_id, start_index, samples):
    
    sample_count = len(samples)
    min_sample = np.min(samples)
    max_sample = np.max(samples)
                 
    print(
        f'append {recording_id} {start_index} {sample_count} '
        f'{min_sample} {max_sample}')
    

def _parse_recordings_post_data(data):

    b = ByteBuffer(data)
    
    # Get action.
    action_code = b.read_value('<I')
    if action_code == 0:
        action = 'append'
    elif action_code == 1:
        action = 'stop'
    else:
        raise ValueError(f'Unrecognized action code {action_code}.')

    # TODO: Send 64-bit integers rather than doubles for recording ID
    # and start index.
    
    # Get recording ID.
    recording_id = int(b.read_value('<d'))
    
    result = Bunch(
        action=action,
        recording_id=recording_id
    )
    
    if action == 'append':
        
        # Get start index.
        start_index = int(b.read_value('<d'))
        
        # Get endianness.
        little_endian = b.read_value('<I')
        
        # Get samples.
        dtype = '<i2' if little_endian else '>i2'
        samples = np.frombuffer(b.bytes, dtype, -1, b.offset)
        
        # Make sample array two-dimensional.
        samples = samples.reshape((_CHANNEL_COUNT, -1))
    
        result.start_index = start_index
        result.samples = samples
 
    return result


def show_recording_capabilities(request):
    context = {}
    return render(request, 'vesper/show-recording-capabilities.html', context)
