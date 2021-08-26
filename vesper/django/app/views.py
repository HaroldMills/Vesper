from urllib.parse import quote
import datetime
import itertools
import json
import logging

from django import forms, urls
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import (
    Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
    HttpResponseNotAllowed, HttpResponseRedirect, HttpResponseServerError,
    JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import numpy as np

from vesper.django.app.add_recording_audio_files_form import \
    AddRecordingAudioFilesForm
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
    AnnotationInfo, Clip, Job, StringAnnotation, Tag, TagInfo)
from vesper.django.app.refresh_recording_audio_file_paths_form import \
    RefreshRecordingAudioFilePathsForm
from vesper.django.app.transfer_call_classifications_form import \
    TransferCallClassificationsForm
from vesper.django.app.untag_clips_form import UntagClipsForm
from vesper.ephem.sun_moon import SunMoon
from vesper.old_bird.export_clip_counts_csv_file_form import \
    ExportClipCountsCsvFileForm as OldBirdExportClipCountsCsvFileForm
from vesper.old_bird.import_clips_form import ImportClipsForm
from vesper.singleton.archive import archive
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.job_manager import job_manager
from vesper.singleton.preference_manager import preference_manager
from vesper.singleton.preset_manager import preset_manager
from vesper.util.bunch import Bunch
import vesper.django.app.model_utils as model_utils
import vesper.external_urls as external_urls
from vesper.old_bird.add_old_bird_clip_start_indices_form import \
    AddOldBirdClipStartIndicesForm
import vesper.old_bird.export_clip_counts_csv_file_utils as \
    old_bird_export_clip_counts_csv_file_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.calendar_utils as calendar_utils
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils
import vesper.version as version


# Commented out along with recording view code at the end of this file.
# from pathlib import Path
# from vesper.django.app.models import RecordingFile
# from vesper.signal.wave_audio_file import WaveAudioFileReader
# from vesper.singleton.recording_manager import recording_manager
# from vesper.util.byte_buffer import ByteBuffer
# import vesper.util.audio_file_utils as audio_file_utils


# A note about Vesper security:
#
# For security, Vesper must require user authentication for all Django
# views that can modify server state. In most cases, it suffices to
# decorate the view with `@login_required`. In some cases, however,
# such as for views that receive requests via calls to the JavaScript
# `fetch` function on the client (see the `annotate_clip_batch`,
# `unannotate_clip_batch`, `tag_clip_batch`, and `untag_clip_batch`
# view functions), this does not seem to do what we need (see TODO
# item preceding the `annotate_clip_batch` function), and we call
# the `User.is_authenticated` method from within the view to check
# that the user is logged in.
#
# Vesper must also defend against cross site request forgeries (CSRFs).
# We use Django's CSRF protection for this, which requires that we
# include the CSRF token in all HTTP requests that can modify the
# server state. To do this, we use the `{% csrf_token %}` tag in HTML
# template forms, which causes the `X-CSRFToken` header to be included
# in the POST requests made when the forms are submitted, and we include
# the `X-CSRFToken` header ourselves in calls to the JavaScript `fetch`
# function that send POST requests to the server that can modify server
# state. There are some Django views (e.g. `get_clip_audios` and
# `get_clip_metadata`) that process POST requests that can never modify
# server state, and we disable Django's CSRF protection for these views
# with Django's `@csrf_exempt` decorator.


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
        
      - name: Untag clips
        url_name: untag-clips
        
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
        
- name: Admin
  dropdown:
 
      - name: Refresh recording audio file paths
        url_name: refresh-recording-audio-file-paths
        
      # - name: Add recording audio files
      #   url_name: add-recording-audio-files
        
      # - name: Add Old Bird clip start indices
      #   url_name: add-old-bird-clip-start-indices
        
      # - name: Create clip audio files
      #   url_name: create-clip-audio-files
        
      # - name: Delete clip audio files
      #   url_name: delete-clip-audio-files
   
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
    default_data = _get_default_navbar_data()
    data = preference_manager.preferences.get('navbar', default_data)
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
            'defer_clip_creation': data['defer_clip_creation']
        }
    }


def _start_job(command_spec, user):
    job_id = job_manager.start_job(command_spec, user)
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
            'station_mics': data['station_mics'],
            'start_date': data['start_date'],
            'end_date': data['end_date'],
            'detectors': data['detectors'],
            'tag': data['tag']
        }
    }


@login_required
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
                f'attachment; filename="{file_name}"'

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

    spec = {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clip Metadata CSV File Exporter',
                'arguments': {
                    'table_format': data['table_format'],
                    'output_file_path': data['output_file_path'],
                }
            }
        }
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


_CLIP_SET_ARG_NAMES = (
    'station_mics',
    'start_date',
    'end_date',
    'detectors',
    'classification',
    'tag'
)


def _add_clip_set_command_arguments(command_spec, form_data):
    
    args = command_spec['arguments']
    
    for name in _CLIP_SET_ARG_NAMES:
        args[name] = form_data[name]
       

@login_required
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

    spec = {
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
        }
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec



@login_required
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

    spec = {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clips HDF5 File Exporter',
                'arguments': {
                    'output_file_path': data['output_file_path'],
                }
            },
        }
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


@login_required
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

    spec = {
        'name': 'delete_clips',
        'arguments': {
            'retain_count': data['retain_count']
        }
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


@login_required
def untag_clips(request):

    if request.method in _GET_AND_HEAD:
        form = UntagClipsForm()

    elif request.method == 'POST':

        form = UntagClipsForm(request.POST)

        if form.is_valid():
            command_spec = _create_untag_clips_command_spec(form)
            return _start_job(command_spec, request.user)

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))

    context = _create_template_context(request, 'Other', form=form)

    return render(request, 'vesper/untag-clips.html', context)


def _create_untag_clips_command_spec(form):

    data = form.cleaned_data

    spec = {
        'name': 'untag_clips',
        'arguments': {
            'retain_count': data['retain_count']
        }
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


@login_required
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

    spec = {
        'name': 'create_clip_audio_files',
        'arguments': {}
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


@login_required
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

    spec = {
        'name': 'delete_clip_audio_files',
        'arguments': {}
    }
    
    _add_clip_set_command_arguments(spec, data)
    
    return spec


@login_required
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


# def clip_audio(request, clip_id):
#
#     clip = get_object_or_404(Clip, pk=clip_id)
#
#     content_type = 'audio/wav'
#
#     try:
#         content = clip_manager.get_audio_file_contents(clip, content_type)
#
#     except Exception as e:
#         logger = logging.getLogger('django.server')
#         logger.error(
#             f'Attempt to get audio for clip "{str(clip)}" failed with '
#             f'{e.__class__.__name__} exception. Exception message was: '
#             f'{str(e)}')
#         return HttpResponseServerError()
#
#     response = HttpResponse()
#     response.write(content)
#     response['Content-Type'] = content_type
#     response['Content-Length'] = len(content)
#     return response


# def presets(request, preset_type_name):
#
#     if request.method in _GET_AND_HEAD:
#         content = _get_presets_json(preset_type_name)
#         return HttpResponse(content, content_type='application/json')
#
#     else:
#         return HttpResponseNotAllowed(_GET_AND_HEAD)


def _get_presets_json(preset_type_name):

    """
    Gets all presets of the specified type as JSON.

    The returned JSON is a list of [<preset path>, <preset JSON>]
    pairs, where the preset path is the path relative to the directory
    for the preset type.
    """

    # Force reloading of presets to be sure we're working with the latest.
    preset_manager.unload_presets(preset_type_name)

    presets = preset_manager.get_presets(preset_type_name)
    presets = [(p.path[1:], p.camel_case_data) for p in presets]
    return json.dumps(presets)


# TODO: Does Django already include functions for parsing HTTP headers?
# If so, I couldn't find them.
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


# This view handles an HTTP POST request to read data from the server,
# but does not modify the server state. It uses the POST method rather
# than the GET method since the request includes information (namely
# a list of clip IDs) in its body that the view must read to understand
# the request, and that is not allowed for GET requests: the meaning of
# a GET request must be specified entirely by its URI (see
# https://stackoverflow.com/questions/978061/http-get-with-request-body).
# We exempt the view from Django's CSRF protection since, even though it
# handles POST requests, it does not modify the server state.
@csrf_exempt
def get_clip_audios(request):
    if request.method == 'POST':
        return _handle_json_post(request, _get_clip_audios_aux)
    else:
        return HttpResponseNotAllowed(['POST'])
    
    
def _handle_json_post(request, content_handler):
        
    try:
        content = _get_json_request_body(request)
    except HttpError as e:
        return e.http_response

    try:
        content = json.loads(content)
    except json.JSONDecodeError as e:
        return HttpResponseBadRequest(
            reason='Could not decode request JSON')

    return content_handler(content)
    
        
def _get_json_request_body(request):

    # According to rfc4627, utf-8 is the default charset for the
    # application/json media type.

    return _get_request_body(request, 'application/json', 'utf-8')


def _get_request_body(request, content_type_name, default_charset_name):

    content_type = _parse_content_type(request.META['CONTENT_TYPE'])

    # Make sure content type is text/plain.
    if content_type.name != content_type_name:
        raise HttpError(
            status_code=415,
            reason=f'Request content type must be {content_type_name}')

    charset = content_type.params.get('charset', default_charset_name)

    return request.body.decode(charset)


def _get_clip_audios_aux(content):
    
    clip_ids = content['clip_ids']
    
    # TODO: Consider querying database for batches of clips instead
    # of one clip at a time. This could dramatically reduce the
    # number of database queries this functions performs. The Django
    # QuerySet `in` field lookup or `in_bulk` method might be useful.
    clips = [get_object_or_404(Clip, pk=i) for i in clip_ids]

    content_type = 'audio/wav'
    
    audios = []
    
    for clip in clips:
        
        try:
            audio = clip_manager.get_audio_file_contents(
                clip, content_type)
            
        except Exception as e:
            logger = logging.getLogger('django.server')
            logger.error(
                f'Attempt to get audio file contents for clip '
                f'"{str(clip)}" failed with {e.__class__.__name__} '
                f'exception. Exception message was: {str(e)}')
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
    


def _get_uint32_bytes(i):
    return np.array([i], dtype=np.dtype('<u4')).tobytes()


# This view handles an HTTP POST request to read data from the server,
# but does not modify the server state. It uses the POST method rather
# than the GET method since the request includes information (namely
# a list of clip IDs) in its body that the view must read to understand
# the request, and that is not allowed for GET requests: the meaning of
# a GET request must be specified entirely by its URI (see
# https://stackoverflow.com/questions/978061/http-get-with-request-body).
# We exempt the view from Django's CSRF protection since, even though it
# handles POST requests, it does not modify the server state.
@csrf_exempt
def get_clip_metadata(request):
    if request.method == 'POST':
        return _handle_json_post(request, _get_clip_metadata_aux)
    else:
        return HttpResponseNotAllowed(['POST'])        
        
        
def _get_clip_metadata_aux(content):
    
    clip_ids = content['clip_ids']
    
    # TODO: Consider querying database for batches of clips instead
    # of one clip at a time. This could dramatically reduce the
    # number of database queries this functions performs. The Django
    # QuerySet `in` field lookup or `in_bulk` method might be useful.
    metadata = dict((i, _get_clip_metadata(i)) for i in clip_ids)
    
    return JsonResponse(metadata)
            

def _get_clip_metadata(clip_id):
    return {
        'annotations': _get_annotations(clip_id),
        'tags': _get_tags(clip_id)
    }


def _get_annotations(clip_id):
    
    annotations = StringAnnotation.objects. \
        filter(clip_id=clip_id). \
        select_related('info')

    # We return a list of (name, value) pairs instead of a dictionary
    # so that the JSON analog is iterable and ordered (JavaScript
    # objects are not iterable).
    return sorted((a.info.name, a.value) for a in annotations)


def _get_tags(clip_id):
    tags = Tag.objects.filter(clip_id=clip_id).select_related('info')
    return sorted(t.info.name for t in tags)
                
                
# TODO: Understand why decorating this view (or any of the
# `unannotate_clip_batch`, `tag_clip_batch`, and `untag_clip_batch`
# views) with `@login_required` causes the view to not be executed
# when the user is not logged in (as expected), but return a 200
# response instead of a redirect response. The views receive
# requests from the clip album JavaScript `_editClipMetadataAux`
# method. It might help to look at the code for `@login_required`.
def annotate_clip_batch(request):

    '''
    This view expects a request body that is a UTF-8 encoded JSON object.
    The object must have a "clip_ids" property whose value is a list
    of the IDs of the clips to be annotated, and an "annotations"
    property whose value is a JSON object mapping annotation names to
    annotation values. The specified annotations are set on all specified
    clips.
    
    This view is named `annotate_clip_batch` instead of `annotate_clips`
    to leave room for an `annotate_clips` Vesper command.
    '''

    return _edit_clip_metadata(request, _annotate_clips)
    
    
def _edit_clip_metadata(request, edit_function, *args):
    
    '''
    The `edit_function` argument is a function that can be applied to
    a set of clips to edit them. The edit function has four required
    positional arguments:
    
        clip_ids: iterable of clip IDs.
        creation_time: the creation time to record for the edits.
        creating_user: the creating user to record for the edits.
        content: HTTP request content, a Python dictionary parsed from JSON.
        
    The edit function can also take additional, trailing positional
    arguments, supplied to this function and passed on to the edit
    function as `*args`.
    '''
    
    def handle_content(content):
        
        clip_ids = content['clip_ids']
        creation_time = time_utils.get_utc_now()
        creating_user = request.user
                
        # We lock the archive just once for all of the clips that
        # we process, rather than once for each clip. This means
        # that we may hold the lock for several seconds, during
        # which no other threads or processes can hold it. This
        # method is several times faster this way, and since it
        # is typically invoked interactively, the improved
        # performance is especially important.
        with archive_lock.atomic():
            with transaction.atomic():
                edit_function(
                    clip_ids, creation_time, creating_user, content, *args)
                
        return HttpResponse()

    if request.method == 'POST':
        if request.user.is_authenticated:
            return _handle_json_post(request, handle_content)
        else:
            return HttpResponseForbidden()
    else:
        return HttpResponseNotAllowed(['POST'])


def _annotate_clips(clip_ids, creation_time, creating_user, content):
    
    annotations = content['annotations']
    
    for name, value in annotations.items():
        
        info = get_object_or_404(AnnotationInfo, name=name)

        for clip_id in clip_ids:

            clip = get_object_or_404(Clip, pk=clip_id)

            model_utils.annotate_clip(
                clip, info, value, creation_time=creation_time,
                creating_user=creating_user)
            
            
def unannotate_clip_batch(request):

    '''
    This view expects a request body that is a UTF-8 encoded JSON object.
    The object must have a "clip_ids" property whose value is a list
    of the IDs of the clips to be unannotated, and an "annotation_names"
    property whose value is a JSON array of annotation names. The
    specified annotations are deleted for all specified clips, if they
    exist.
    
    This view is named `unannotate_clip_batch` instead of `unannotate_clips`
    to leave room for an `unannotate_clips` Vesper command.
    '''

    args = ('annotation_names', AnnotationInfo, model_utils.unannotate_clip)
    
    return _edit_clip_metadata(request, _edit_clip_metadata_aux, *args)
    
    
def _edit_clip_metadata_aux(
        clip_ids, creation_time, creating_user, content, name_key,
        info_class, edit_function):
    
    item_names = content.get(name_key)
    
    if item_names is not None:
    
        for name in item_names:
            
            info = get_object_or_404(info_class, name=name)
    
            for clip_id in clip_ids:
    
                clip = get_object_or_404(Clip, pk=clip_id)
    
                edit_function(
                    clip, info, creation_time=creation_time,
                    creating_user=creating_user)
                
                
def tag_clip_batch(request):

    '''
    This view expects a request body that is a UTF-8 encoded JSON object.
    The object must have a "clip_ids" property whose value is a list
    of the IDs of the clips to be tagged, and a "tags" property whose
    value is a JSON array of tags. The specified tags are added to all
    specified clips, when they don't exist already.
    
    This view is named `tag_clip_batch` instead of `tag_clips` to leave
    room for a `tag_clips` Vesper command.
    '''

    args = ('tags', TagInfo, model_utils.tag_clip)
    return _edit_clip_metadata(request, _edit_clip_metadata_aux, *args)
    
    
def untag_clip_batch(request):

    '''
    This view expects a request body that is a UTF-8 encoded JSON object.
    The object must have a "clip_ids" property whose value is a list
    of the IDs of the clips to be untagged, and a "tags" property whose
    value is a JSON array of tags. The specified tags are removed from
    all specified clips, when they are present.
    
    This view is named `untag_clip_batch` instead of `untag_clips`
    to leave room for an `untag_clips` Vesper command.
    '''

    args = ('tags', TagInfo, model_utils.untag_clip)
    return _edit_clip_metadata(request, _edit_clip_metadata_aux, *args)
    
    
# def clip_metadata(request, clip_id):
#
#     if request.method in _GET_AND_HEAD:
#         metadata = _get_clip_metadata(clip_id)
#         return JsonResponse(metadata)
#
#     else:
#         return HttpResponseNotAllowed(_GET_AND_HEAD)


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
    
    preference_manager.reload_preferences()
    preferences = preference_manager.preferences

    message = _check_for_stations_detectors_and_classification_annotation(
        'clip calendar')
    
    if message is not None:
        
        context = _create_template_context(
            request, 'View', error_message=message)
        
        return _render_clip_calendar(request, context)

    settings_preset_path, commands_preset_path = \
        _get_preset_paths(params, preferences)
    
    d = _get_clip_filter_data(params, preferences)

    periods_json = _get_periods_json(
        d.sm_pair, d.detector, d.annotation_name, d.annotation_value,
        d.tag_name)

    context = _create_template_context(
        request, 'View',
        station_mic_names=d.sm_pair_ui_names,
        station_mic_name=d.sm_pair_ui_name,
        detector_names=d.detector_ui_names,
        detector_name=d.detector_ui_name,
        classifications=d.annotation_ui_value_specs,
        classification=d.annotation_ui_value_spec,
        tags=d.tag_specs,
        tag=d.tag_spec,
        periods_json=periods_json,
        settings_preset_path=settings_preset_path,
        commands_preset_path=commands_preset_path)

    return _render_clip_calendar(request, context)


def _check_for_stations_detectors_and_classification_annotation(view_name):
    
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    
    if len(sm_pairs) == 0:
        # archive contains no station/mics
        
        return _create_missing_entities_text(
            view_name, 'station/microphone pairs')
        
    detectors = archive.get_processors_of_type('Detector')
    
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
        raise Http404(f'Archive contains no {type_name} objects.')

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

    spec = _get_calendar_query_field_value(
        'classification', params, preferences)
    
    spec = archive.get_string_annotation_ui_value('Classification', spec)

    if spec is None or spec not in annotation_ui_value_specs:
        spec = archive.NOT_APPLICABLE

    return spec


def _get_string_annotation_info(annotation_name, annotation_ui_value_spec):

    value_spec = archive.get_string_annotation_archive_value(
        annotation_name, annotation_ui_value_spec)
    
    if value_spec == archive.NOT_APPLICABLE:
        
        # We return an `annotation_name` of `None` to denote all clips.
        annotation_name = None
        annotation_value = None

    else:

        if value_spec == archive.STRING_ANNOTATION_VALUE_NONE:
            annotation_value = None
        else:
            annotation_value = value_spec

    return annotation_name, annotation_value


def _get_tag_spec(tag_specs, params, preferences):
    
    spec = _get_calendar_query_field_value('tag', params, preferences)
    
    if spec is None or spec not in tag_specs:
        spec = archive.NOT_APPLICABLE
        
    return spec
    
    
def _get_tag_name(tag_spec):
    if tag_spec == archive.NOT_APPLICABLE:
        return None
    else:
        return tag_spec
    
    
def _get_periods_json(
        sm_pair, detector, annotation_name=None, annotation_value=None,
        tag_name=None):

    if sm_pair is None or detector is None:
        return '[]'

    else:

        station, mic_output = sm_pair

        clip_counts = model_utils.get_clip_counts(
            station, mic_output, detector, annotation_name=annotation_name,
            annotation_value=annotation_value, tag_name=tag_name)

        dates = sorted(list(clip_counts.keys()))
        periods = calendar_utils.get_calendar_periods(dates)

        return calendar_utils.get_calendar_periods_json(periods, clip_counts)


def night(request):

    # TODO: Combine this view with `clip_album` view?

    # TODO: Check URL query items.
    params = request.GET
    
    # Unload presets and reload preferences to make sure we work with
    # the latest of each.
    preset_manager.unload_presets()
    preference_manager.reload_preferences()
    preferences = preference_manager.preferences

    sm_pair_ui_name = params['station_mic']
    sm_pairs = model_utils.get_station_mic_output_pairs_dict()
    station, mic_output = sm_pairs[sm_pair_ui_name]
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]
    
    detector_name = params['detector']
    detector = archive.get_processor(detector_name)
    detector_ui_name = archive.get_processor_ui_name(detector)
    detectors = archive.get_visible_processors_of_type('Detector')
    detector_ui_names = [archive.get_processor_ui_name(d) for d in detectors]
    
    annotation_name = 'Classification'
    annotation_ui_value_specs = \
        archive.get_visible_string_annotation_ui_value_specs(annotation_name)
    annotation_value_spec = params['classification']
    annotation_name, annotation_value = \
        _get_string_annotation_info(annotation_name, annotation_value_spec)

    tag_specs = archive.get_tag_specs()
    tag_spec = _get_tag_spec(tag_specs, params, preferences)
    tag_name = _get_tag_name(tag_spec)

    date_string = params['date']
    date = time_utils.parse_date(*date_string.split('-'))

    solar_event_times_json = _get_solar_event_times_json(station, date)

    time_interval = station.get_night_interval_utc(date)
    recordings = model_utils.get_recordings(station, mic_output, time_interval)
    recordings_json = _get_recordings_json(recordings, station)

    clips = model_utils.get_clips(
        station=station,
        mic_output=mic_output,
        date=date,
        detector=detector,
        annotation_name=annotation_name,
        annotation_value=annotation_value,
        tag_name=tag_name)
    clips_json = _get_clips_json(clips, station)

    page_num = params.get('page', 1)
    
    settings_presets_json = _get_presets_json('Clip Album Settings')
    commands_presets_json = _get_presets_json('Clip Album Commands')
    
    settings_preset_path, commands_preset_path = \
        _get_preset_paths(params, preferences)
    
    context = _create_template_context(
        request, 'View',
        station_mic_names=sm_pair_ui_names,
        station_mic_name=sm_pair_ui_name,
        detector_names=detector_ui_names,
        detector_name=detector_ui_name,
        classifications=annotation_ui_value_specs,
        classification=annotation_value_spec,
        tags=tag_specs,
        tag=tag_spec,
        date=date_string,
        solar_event_times_json=solar_event_times_json,
        recordings_json=recordings_json,
        clips_json=clips_json,
        page_num = page_num,
        settings_presets_json=settings_presets_json,
        settings_preset_path=settings_preset_path,
        commands_presets_json=commands_presets_json,
        commands_preset_path=commands_preset_path,
        archive_read_only=settings.ARCHIVE_READ_ONLY)

    return render(request, 'vesper/night.html', context)


def _get_solar_event_times_json(station, night):

    # See note near the top of this file about why we send local
    # instead of UTC times to clients.

    sun_moon = SunMoon(
        station.latitude, station.longitude, station.tz,
        result_times_local=True)
    
    events = sun_moon.get_solar_events(night, day=False)
    
    times = dict(
        (_get_solar_event_variable_name(e.name), _format_time(e.time))
        for e in events)
    
    return json.dumps(times)


def _get_solar_event_variable_name(event_name):
    
    """Creates a JavaScript variable name from a solar event name."""
    
    return (event_name[0].lower() + event_name[1:]).replace(' ', '')


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
    millis = f'{millis:03d}'
    while len(millis) != 0 and millis[-1] == '0':
        millis = millis[:-1]
    if len(millis) != 0:
        millis = '.' + millis

    time_zone = time.strftime('%Z')

    return prefix + millis + ' ' + time_zone


def _get_preset_paths(params, preferences):
    
    settings_path = _get_preset_path(
        'settings', params, 'Clip Album Settings', preferences)
    
    commands_path = _get_preset_path(
        'commands', params, 'Clip Album Commands', preferences)
    
    return settings_path, commands_path


def _get_preset_path(param_name, params, preset_type_name, preferences):
    try:
        return params[param_name]
    except KeyError:
        preset_name = 'default_presets.' + preset_type_name
        return preferences.get(preset_name)


def clip_album(request):

    # TODO: Check URL query items.
    params = request.GET
    
    # Unload presets and reload preferences to make sure we work with
    # the latest of each.
    preset_manager.unload_presets()
    preference_manager.reload_preferences()
    preferences = preference_manager.preferences

    message = _check_for_stations_detectors_and_classification_annotation(
        'clip album')
    
    if message is not None:
        
        context = _create_template_context(
            request, 'View', error_message=message)
        
        return _render_clip_album(request, context)

    d = _get_clip_filter_data(params, preferences)

    station, mic_output = d.sm_pair
    clips = model_utils.get_clips(
        station=station,
        mic_output=mic_output,
        detector=d.detector,
        annotation_name=d.annotation_name,
        annotation_value=d.annotation_value,
        tag_name=d.tag_name)
    clips_json = _get_clips_json(clips, station)
    
    page_num = params.get('page', 1)

    settings_presets_json = _get_presets_json('Clip Album Settings')
    commands_presets_json = _get_presets_json('Clip Album Commands')

    settings_preset_path, commands_preset_path = \
        _get_preset_paths(params, preferences)

    context = _create_template_context(
        request, 'View',
        station_mic_names=d.sm_pair_ui_names,
        station_mic_name=d.sm_pair_ui_name,
        detector_names=d.detector_ui_names,
        detector_name=d.detector_ui_name,
        classifications=d.annotation_ui_value_specs,
        classification=d.annotation_ui_value_spec,
        tags=d.tag_specs,
        tag=d.tag_spec,
        solar_event_times_json='null',
        recordings_json='[]',
        clips_json=clips_json,
        page_num=page_num,
        settings_presets_json=settings_presets_json,
        settings_preset_path=settings_preset_path,
        commands_presets_json=commands_presets_json,
        commands_preset_path=commands_preset_path,
        archive_read_only=settings.ARCHIVE_READ_ONLY)

    return _render_clip_album(request, context)


def _get_clip_filter_data(params, preferences):
    
    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pair = _get_calendar_query_object(
        sm_pairs, 'station_mic', params, preferences, name_getter=get_ui_name)
    sm_pair_ui_name = None if sm_pair is None else get_ui_name(sm_pair)
    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]

    detector_name = _get_calendar_query_field_value(
        'detector', params, preferences)
    detector = archive.get_processor(detector_name)
    detectors = archive.get_visible_processors_of_type('Detector')
    detector_ui_names = [archive.get_processor_ui_name(d) for d in detectors]
    detector_ui_name = archive.get_processor_ui_name(detector)
    
    annotation_name = 'Classification'
    annotation_ui_value_specs = \
        archive.get_visible_string_annotation_ui_value_specs(annotation_name)
    annotation_ui_value_spec = _get_string_annotation_ui_value_spec(
        annotation_ui_value_specs, params, preferences)
    annotation_name, annotation_value = \
        _get_string_annotation_info(annotation_name, annotation_ui_value_spec)
        
    tag_specs = archive.get_tag_specs()
    tag_spec = _get_tag_spec(tag_specs, params, preferences)
    tag_name = _get_tag_name(tag_spec)
        
    return Bunch(
        
        sm_pair=sm_pair,
        sm_pair_ui_names=sm_pair_ui_names,
        sm_pair_ui_name=sm_pair_ui_name,
        
        detector=detector,
        detector_ui_names=detector_ui_names,
        detector_ui_name=detector_ui_name,
        
        annotation_name=annotation_name,
        annotation_value=annotation_value,
        annotation_ui_value_specs=annotation_ui_value_specs,
        annotation_ui_value_spec=annotation_ui_value_spec,
        
        tag_name=tag_name,
        tag_specs=tag_specs,
        tag_spec=tag_spec
        
    )


def _render_clip_album(request, context):
    return render(request, 'vesper/clip-album.html', context)


@login_required
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


def about_vesper(request):

    if request.method not in _GET_AND_HEAD:
        return HttpResponseNotAllowed(_GET_AND_HEAD)

    context = _create_template_context(
        request, 'Help',
        version=version.full_version,
        source_code_url=external_urls.source_code_url,
        documentation_url=external_urls.documentation_url)

    return render(request, 'vesper/about-vesper.html', context)


# # TODO: Handle authentication in `record` and `recordings` views.
#
# # TODO: Record to the archive's first recording directory.
# _RECORDING_DIR_PATH = Path('/Users/harold/Desktop/Vesper Recordings')
# _SAMPLE_RATE = 24000
# _CHANNEL_COUNT = 1
# _SAMPLE_SIZE = 16
#
# # TODO: Create new recording in database and use its ID.
# _recording_id = 0
#
#
# def record(request):
#
#     if request.method in _GET_AND_HEAD:
#         context = {}
#         return render(request, 'vesper/record.html', context)
#
#     elif request.method == 'POST':
#
#         global _recording_id
#
#         recording_id = _recording_id
#
#         file_path = _get_recording_file_path(recording_id)
#
#         audio_file_utils.write_empty_wave_file(
#             file_path, _CHANNEL_COUNT, _SAMPLE_RATE, _SAMPLE_SIZE)
#
#         content = {'recordingId': recording_id}
#
#         _recording_id += 1
#
#         return JsonResponse(content)
#
#     else:
#         return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))
#
#
# def _get_recording_file_path(recording_id):
#     file_name = f'{recording_id}.wav'
#     return _RECORDING_DIR_PATH / file_name
#
#
# def recordings(request):
#
#     if request.method == 'POST':
#
#         try:
#             data = _parse_recordings_post_data(request.body)
#         except Exception:
#             return HttpResponseBadRequest(
#                 'Could not parse received recording data.')
#
#         if data.action == 'append':
#
#             recording_id = data.recording_id
#             start_index = data.start_index
#             samples = data.samples
#
#             _write_recording_samples(recording_id, start_index, samples)
#
#         else:
#             print('stop')
#
#         return HttpResponse()
#
#     else:
#         return HttpResponseNotAllowed(('POST',))
#
#
# def _write_recording_samples(recording_id, start_index, samples):
#     # _show_append_info(recording_id, start_index, samples)
#     file_path = _get_recording_file_path(recording_id)
#     audio_file_utils.write_wave_file_samples(file_path, start_index, samples)
#
#
# def _show_append_info(recording_id, start_index, samples):
#
#     sample_count = len(samples)
#     min_sample = np.min(samples)
#     max_sample = np.max(samples)
#
#     print(
#         f'append {recording_id} {start_index} {sample_count} '
#         f'{min_sample} {max_sample}')
#
#
# def _parse_recordings_post_data(data):
#
#     b = ByteBuffer(data)
#
#     # Get action.
#     action_code = b.read_value('<I')
#     if action_code == 0:
#         action = 'append'
#     elif action_code == 1:
#         action = 'stop'
#     else:
#         raise ValueError(f'Unrecognized action code {action_code}.')
#
#     # TODO: Send 64-bit integers rather than doubles for recording ID
#     # and start index.
#
#     # Get recording ID.
#     recording_id = int(b.read_value('<d'))
#
#     result = Bunch(
#         action=action,
#         recording_id=recording_id
#     )
#
#     if action == 'append':
#
#         # Get start index.
#         start_index = int(b.read_value('<d'))
#
#         # Get endianness.
#         little_endian = b.read_value('<I')
#
#         # Get samples.
#         dtype = '<i2' if little_endian else '>i2'
#         samples = np.frombuffer(b.bytes, dtype, -1, b.offset)
#
#         # Make sample array two-dimensional.
#         samples = samples.reshape((_CHANNEL_COUNT, -1))
#
#         result.start_index = start_index
#         result.samples = samples
#
#     return result
#
#
# def show_recording_capabilities(request):
#     context = {}
#     return render(request, 'vesper/show-recording-capabilities.html', context)
#
#
# from threading import Lock
#
# _recording_file_reader_cache = {}
# _read_lock = Lock()
#
#
# def _clear_recording_file_reader_cache():
#
#     global _recording_file_reader_cache
#
#     for reader in _recording_file_reader_cache.values():
#         reader.close()
#
#     _recording_file_reader_cache = {}
#
#
# def _get_recording_file_reader(path):
#
#     global _recording_file_reader_cache
#
#     try:
#
#         return _recording_file_reader_cache[path]
#
#     except KeyError:
#
#         # Create new reader.
#         reader = WaveAudioFileReader(str(path))
#
#         # Cache new reader.
#         _recording_file_reader_cache[path] = reader
#
#         return reader
#
#
# def recording_audio(request, recording_id):
#
#     params = request.GET
#     start_index = int(params['start_index'])
#     length = int(params['length'])
#     # print(f'start index {start_index} length {length}')
#
#     file = RecordingFile.objects.get(recording__id=recording_id)
#     path = recording_manager.get_absolute_recording_file_path(file.path)
#     with _read_lock:
#         reader = _get_recording_file_reader(path)
#         samples = reader.read(start_index, length)
#     content = samples.tobytes()
#     return HttpResponse(content, content_type='application/octet-stream')
