from collections import defaultdict
from urllib.parse import quote
import datetime
import itertools
import json

from django import forms, urls
from django.db.models import F, Max, Min
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed,
    HttpResponseRedirect)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
import pytz
import yaml

from vesper.django.app.classify_form import ClassifyForm
from vesper.django.app.detect_form import DetectForm
from vesper.django.app.export_clip_sound_files_form import \
    ExportClipSoundFilesForm
from vesper.django.app.export_clips_csv_file_form import \
    ExportClipsCsvFileForm
from vesper.django.app.import_archive_data_form import ImportArchiveDataForm
from vesper.django.app.import_recordings_form import ImportRecordingsForm
from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Clip, Job, Recording, Station,
    StringAnnotation)
from vesper.singletons import job_manager, preference_manager, preset_manager
from vesper.util.bunch import Bunch
import vesper.django.app.model_utils as model_utils
import vesper.ephem.ephem_utils as ephem_utils
import vesper.util.calendar_utils as calendar_utils
import vesper.util.time_utils as time_utils


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


def _create_navbar_items(data):
    return tuple(_create_navbar_item(d) for d in data)


def _create_navbar_item(data):
    if 'url_name' in data or 'url' in data:
        return _create_navbar_link_item(data)
    else:
        return _create_navbar_dropdown_item(data)
    

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
    items = _create_navbar_items(data['dropdown'])
    return Bunch(type='dropdown', name=name, items=items)


def _create_navbar_right_items(request):
    
    user = request.user
    
    # The value of the "next" parameter is a URL that is embedded in the
    # URL of which the "next" parameter is a part. We must quote the
    # embedded URL to ensure that it does not interfere with parsing the
    # containing URL.
    query = '?next=' + quote(request.get_full_path())
    
    if user.is_authenticated():
        # user is logged in
        
        item = Bunch(
            name=user.username,
            type='dropdown',
            items = [
                Bunch(
                    name='Log Out',
                    type='link',
                    url='/logout/' + query)
            ])
        
    else:
        # user is not logged in
        
        item = Bunch(
            name='Log In',
            type='link',
            url='/login/' + query)
        
    return [item]


# Note that as of 2016-07-19, nested navbar dropdowns do not work.
# The generated HTML looks right to me so the problem may be a
# Bootstrap limitation.
_NAVBAR_ITEMS = _create_navbar_items(yaml.load('''
  
- name: View
  url_name: calendar
    
- name: Import
  dropdown:
  
      - name: Archive Data
        url_name: import-archive-data
        
      - name: Recordings
        url_name: import-recordings
          
- name: Detect
  url_name: detect
    
- name: Classify
  url_name: classify
    
- name: Export
  dropdown:
  
      - name: Clips CSV File
        url_name: export-clips-csv-file
        
      - name: Clip Sound Files
        url_name: export-clip-sound-files
  
'''))


_ONE_DAY = datetime.timedelta(days=1)
_GET_AND_HEAD = ('GET', 'HEAD')

_WILDCARD = '*'
_NONE = 'Unclassified'
_IGNORE_ANNOTATION = _WILDCARD + ' | ' + _NONE
_NO_ANNOTATION = _NONE
_ANY_ANNOTATION = _WILDCARD
_ANNOTATION_VALUE_COMPONENT_SEPARATOR = '.'


def index(request):
    return redirect(reverse('calendar'))


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
            'end_date': data['end_date']
        }
    }


def _start_job(command_spec, user):
    job_id = job_manager.instance.start_job(command_spec, user)
    url = urls.reverse('job', args=[job_id])
    return HttpResponseRedirect(url)


def _create_template_context(
        request, active_navbar_item='', **kwargs):
    
    kwargs.update(
        navbar_items=_NAVBAR_ITEMS,
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
            'end_date': data['end_date']
        }
    }


def import_(request):
    context = _create_template_context(request, 'Import')
    return render(request, 'vesper/import.html', context)
    
    
@login_required
@csrf_exempt
def export_clips_csv_file(request):
    
    if request.method in _GET_AND_HEAD:
        form = ExportClipsCsvFileForm()
         
    elif request.method == 'POST':
  
        form = ExportClipsCsvFileForm(request.POST)
          
        if form.is_valid():
            command_spec = _create_export_clips_csv_file_command_spec(form)
            return _start_job(command_spec, request.user)
             
    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))
     
    context = _create_template_context(request, 'Export', form=form)
     
    return render(request, 'vesper/export-clips-csv-file.html', context)


def _create_export_clips_csv_file_command_spec(form):
    
    data = form.cleaned_data
    
    return {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'MPG Ranch Clips CSV File',
                'arguments': {
                    'output_file_path': data['output_file_path'],
                }
            },
            'detectors': data['detectors'],
            'station_mics': data['station_mics'],
            'start_date': data['start_date'],
            'end_date': data['end_date']
        }
    }


@login_required
@csrf_exempt
def export_clip_sound_files(request):
    
    if request.method in _GET_AND_HEAD:
        form = ExportClipSoundFilesForm()
         
    elif request.method == 'POST':
  
        form = ExportClipSoundFilesForm(request.POST)
          
        if form.is_valid():
            command_spec = _create_export_clip_sound_files_command_spec(form)
            return _start_job(command_spec, request.user)
             
    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))
     
    context = _create_template_context(request, 'Export', form=form)
     
    return render(request, 'vesper/export-clip-sound-files.html', context)


def _create_export_clip_sound_files_command_spec(form):
    
    data = form.cleaned_data
    
    return {
        'name': 'export',
        'arguments': {
            'exporter': {
                'name': 'Clip Sound Files',
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
            'start_date': data['start_date'],
            'end_date': data['end_date']
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
    # TODO: Set appropriate response status code on failure, e.g. if
    # there is no such clip or if its sound file is missing.
    clip = Clip.objects.get(id=clip_id)
    content = clip.wav_file_contents
    response = HttpResponse()
    response.write(content)
    response['Content-Type'] = 'audio/wav'
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
    
    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)


def _get_annotations_json(clip_id):
    
    annotations = StringAnnotation.objects.filter(
        clip_id=clip_id
    ).annotate(name=F('info__name'))
    
    annotations_dict = dict((a.name, a.value) for a in annotations)
    
    return json.dumps(annotations_dict)
    
    
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
        
        if request.user.is_authenticated():
            
            clip = get_object_or_404(Clip, pk=clip_id)
            info = get_object_or_404(AnnotationInfo, name=name)
            value = _get_request_body_as_text(request).strip()
            model_utils.annotate_clip(
                clip, info, value, creating_user=request.user)
            
            return HttpResponse()
        
        else:
            # user not logged in
            
            return HttpResponseForbidden()
        
    
    elif request.method == 'DELETE':
        
        if request.user.is_authenticated():
            
            info = get_object_or_404(AnnotationInfo, name=name)
            model_utils.delete_clip_annotation(clip_id, info, user=request.user)
            
            return HttpResponse()
        
        else:
            # user not logged in
            
            return HttpResponseForbidden()

    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'PUT', 'DELETE'))
    

def _get_request_body_as_text(request):
    
    content_type = _parse_content_type(request.META['CONTENT_TYPE'])
    
    # Make sure content type is text/plain.
    if content_type.name != 'text/plain':
        raise ValueError(
            ('Received HTTP request content type was {}, but {} '
             'is required.').format(content_type.name, 'text/plain'))

    # Get charset, defaulting to us-ascii. (According to rfc6657,
    # us-ascii is the default charset for the text/plain media type.)
    charset = content_type.params.get('charset', 'us-ascii')
            
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
    
    
def calendar(request):
    
    params = request.GET
        
    preference_manager.instance.reload_preferences()
    preferences = preference_manager.instance.preferences

    sm_pairs = model_utils.get_station_mic_output_pairs_list()
    get_ui_name = model_utils.get_station_mic_output_pair_ui_name
    sm_pair = _get_calendar_query_object(
        sm_pairs, 'station_mic', params, preferences, name_getter=get_ui_name)
    
    detectors = model_utils.get_processors('Detector')
    detector = _get_calendar_query_object(
        detectors, 'detector', params, preferences)
    
    classifications = _get_classifications()
    classification = _get_classification(classifications, params, preferences)
    
    annotation_name, annotation_value = \
        _get_classification_annotation_info(classification)
    periods_json = _get_periods_json(
        sm_pair, detector, annotation_name, annotation_value)
    
    sm_pair_ui_names = [get_ui_name(p) for p in sm_pairs]
    sm_pair_ui_name = None if sm_pair is None else get_ui_name(sm_pair)
    
    detector_names = [d.name for d in detectors]
    detector_name = None if detector is None else detector.name
    
    context = _create_template_context(
        request, 'View',
        station_mic_names=sm_pair_ui_names,
        station_mic_name=sm_pair_ui_name,
        detector_names=detector_names,
        detector_name=detector_name,
        classifications=classifications,
        classification=classification,
        periods_json=periods_json)
    
    return render(request, 'vesper/calendar.html', context)
    
    
def _get_calendar_query_object(
        objects, type_name, params, preferences,
        name_getter=lambda object: object.name):
    
    if len(objects) == 0:
        return None
    
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
            

def _get_classifications():
    

    # Get classification choices.
    
    classifications = [
        _NO_ANNOTATION,
        _IGNORE_ANNOTATION,
        _ANY_ANNOTATION
    ]
    
    values = _get_string_annotation_values('Classification')
    
    if values is not None:
        classifications += _add_wildcard_classifications(values)
        
    return classifications
        
        
def _get_classification(classifications, params, preferences):
    
    classification = _get_calendar_query_field_value(
        'classification', params, preferences)

    if classification is None or classification not in classifications:
        classification = _ANY_ANNOTATION
        
    return classification


def _get_string_annotation_values(annotation_name):
    
    try:
        info = AnnotationInfo.objects.get(name=annotation_name)
    except AnnotationInfo.DoesNotExist:
        return None
    
    constraint = info.constraint
    
    if constraint is None:
        return None
    
    else:
        
        # We get the annotation values specified by the named constraint
        # in a two-stage process. In the first stage, we retrieve the
        # constraint's YAML, and the YAML of all of its ancestors, from
        # the database, parse it into constraint dictionaries, and
        # substitute parent constraint dictionaries for parent names.
        # We also look for inheritance graph cycles in this stage and
        # raise an exception if one is found.
        #
        # In the second stage, we create a flat tuple of annotation
        # values from the graph of constraint dictionaries produced
        # by the first stage.
        #
        # In retrospect I'm not sure it was really a good idea to
        # separate the processing into two stages rather than doing
        # it all in one. I don't think the single-stage processing
        # would really be any more difficult to write or understand.

        constraint = _get_string_annotation_constraint_dict(constraint.name)
        values = _get_string_annotation_constraint_values(constraint)
        return tuple(sorted(values))


def _get_string_annotation_constraint_dict(constraint_name):
    return _get_string_annotation_constraint_dict_aux(constraint_name, [])


def _get_string_annotation_constraint_dict_aux(
        constraint_name, visited_constraint_names):
    
    """
    Gets the specified string annotation value constraint from the
    database, parses its YAML to produce a constraint dictionary, and
    recursively substitutes similarly parsed constraint dictionaries for
    constraint names in the `extends` value (if there is one) of the result.
    
    This method detects cycles in constraint inheritance graphs, raising
    a `ValueError` when one is found.
    """
    
    if constraint_name in visited_constraint_names:
        # constraint inheritance graph is cyclic
        
        i = visited_constraint_names.index(constraint_name)
        cycle = ' -> '.join(visited_constraint_names[i:] + [constraint_name])
        raise ValueError(
            ('Cycle detected in constraint inheritance graph. '
             'Cycle is: {}.').format(cycle))
        
    constraint = AnnotationConstraint.objects.get(name=constraint_name)
    constraint = yaml.load(constraint.text)
    
    constraint['parents'] = _get_string_annotation_constraint_parents(
        constraint, visited_constraint_names)
    
    return constraint
        
    
def _get_string_annotation_constraint_parents(
        constraint, visited_constraint_names):
    
    augmented_constraint_names = visited_constraint_names + [constraint['name']]
    
    extends = constraint.get('extends')
    
    if extends is None:
        # constraint has no parents
        
        return []
    
    elif isinstance(extends, str):
        # `extends` is a parent constraint name
        
        return [_get_string_annotation_constraint_dict_aux(
            extends, augmented_constraint_names)]
        
    elif isinstance(extends, list):
        # `extends` is a list of parent constraint names
        
        return [
            _get_string_annotation_constraint_dict_aux(
                name, augmented_constraint_names)
            for name in extends]
        
    else:
        class_name = extends.__class__.__name__
        raise ValueError(
            ('Unexpected type "{}" for value of string annotation '
             'constraint "extends" item.').format(class_name))
    

def _get_string_annotation_constraint_values(constraint):
    
    parent_value_sets = [
        _get_string_annotation_constraint_values(parent)
        for parent in constraint['parents']]
        
    values = _get_string_annotation_constraint_own_values(constraint['values'])
    
    return values.union(*parent_value_sets)
    
    
def _get_string_annotation_constraint_own_values(values):
    
    flattened_values = set()
    
    for value in values:
        
        if isinstance(value, str):
            # value is string
            
            flattened_values.add(value)
            
        elif isinstance(value, dict):
            
            for parent, children in value.items():
                
                flattened_children = \
                    _get_string_annotation_constraint_own_values(children)
                
                flattened_values |= set(
                    parent + _ANNOTATION_VALUE_COMPONENT_SEPARATOR + child
                    for child in flattened_children)
                
    return flattened_values


def _get_classification_annotation_info(classification):
    
    if classification == _IGNORE_ANNOTATION:
        annotation_name = None
        annotation_value = None
        
    else:
        
        annotation_name = 'Classification'
        
        if classification == _NO_ANNOTATION:
            annotation_value = None
        else:
            annotation_value = classification
            
    return annotation_name, annotation_value
        

def _get_station_microphone_outputs_json(station_microphone_outputs):
    station_microphone_output_names = dict(
        (station_name, [o.name for o in outputs])
        for station_name, outputs in station_microphone_outputs.items())
    return json.dumps(station_microphone_output_names)


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
      
    params = request.GET
    
    # TODO: Type check and range check query items.
    sm_pair_ui_name = params['station_mic']
    detector_name = params['detector']
    classification = params['classification']
    date = params['date']
      
    sm_pairs = model_utils.get_station_mic_output_pairs_dict()
    station, mic_output = sm_pairs[sm_pair_ui_name]
    
    date = time_utils.parse_date(*date.split('-'))
    
    solar_event_times_json = _get_solar_event_times_json(station, date)

    detector = model_utils.get_processor(detector_name, 'Detector')
    time_interval = station.get_night_interval_utc(date)
  
    recordings = model_utils.get_recordings(station, mic_output, time_interval)
    
#     rc_pairs = model_utils.get_recording_channel_num_pairs(
#         station, mic_output, time_interval)
#     recordings = [recording for recording, _ in rc_pairs]
    
    recordings_json = _get_recordings_json(recordings, station)
    
    annotation_name, annotation_value = \
        _get_classification_annotation_info(classification)
        
    clips = model_utils.get_clips(
        station, mic_output, detector, date, annotation_name, annotation_value)
    
#     clips = _chain_rc_pair_clips(
#         rc_pairs, time_interval, detector, annotation_name, annotation_value)
    
    clips_json = _get_clips_json(clips, station)
    
#     annotations = _get_rc_pair_annotations(
#         rc_pairs, time_interval, detector, annotation_name, annotation_value)
#     clips_json = _get_clips_json(annotations, station)
      
    # Reload presets and preferences to make sure we have the latest.
    # TODO: For efficiency's sake, be more selective about what we reload.
    # We might reload only presets of specified types, for example, or
    # only ones belonging to the current user.
    preset_manager.instance.reload_presets()
    preference_manager.instance.reload_preferences()
    
    view_settings_presets_json = _get_presets_json('Clip Album Settings')
    keyboard_commands_presets_json = _get_presets_json('Clip Album Commands')
        
    preferences = preference_manager.instance.preferences
    
    view_settings_preset_path = \
        preferences.get('default_presets.Clip Album Settings')
    keyboard_commands_preset_path = \
        preferences.get('default_presets.Clip Album Commands')
        
    context = _create_template_context(
        request, 'View',
        station_mic_name=sm_pair_ui_name,
        detector_name=detector_name,
        classification=classification,
        date=date,
        solar_event_times_json=solar_event_times_json,
        recordings_json=recordings_json,
        clips_json=clips_json,
        view_settings_presets_json=view_settings_presets_json,
        view_settings_preset_path=view_settings_preset_path,
        keyboard_commands_presets_json=keyboard_commands_presets_json,
        keyboard_commands_preset_path=keyboard_commands_preset_path)
          
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
        
        get = lambda e: _get_solar_event_time(e, lat, lon, night, utc_to_local)
        times['sunset'] = get('Sunset')
        times['civilDusk'] = get('Civil Dusk')
        times['nauticalDusk'] = get('Nautical Dusk')
        times['astronomicalDusk'] = get('Astronomical Dusk')
        
        next_day = night + _ONE_DAY
        get = lambda e: _get_solar_event_time(
            e, lat, lon, next_day, utc_to_local)
        times['astronomicalDawn'] = get('Astronomical Dawn')
        times['nauticalDawn'] = get('Nautical Dawn')
        times['civilDawn'] = get('Civil Dawn')
        times['sunrise'] = get('Sunrise')
        
        return json.dumps(times)

    
def _get_solar_event_time(event, lat, lon, date, utc_to_local):
    utc_time = ephem_utils.get_event_time(event, lat, lon, date)
    local_time = utc_to_local(utc_time)
    return _format_time(local_time)


def _get_recordings_json(recordings, station):
    
    # Make sure recordings are in order of increasing start time.
    recordings = sorted(recordings, key=lambda r: r.start_time)
    
    # See note near the top of this file about why we send local
    # instead of UTC times to clients.
    
    utc_to_local = station.utc_to_local
    recording_dicts = [_get_recording_dict(r, utc_to_local) for r in recordings]
    return json.dumps(recording_dicts)

    
def _get_recording_dict(recording, utc_to_local):
    
    start_time = _format_time(utc_to_local(recording.start_time))
    end_time = _format_time(utc_to_local(recording.end_time))
    
    return {
        'startTime': start_time,
        'endTime': end_time
    }
    
    
def _chain_rc_pair_clips(
        rc_pairs, time_interval, detector, annotation_name, annotation_value):
        
    clip_iterators = [
        _get_rc_pair_clips(
            recording, channel_num, time_interval, detector, annotation_name,
            annotation_value)
        for recording, channel_num in rc_pairs]

    return list(itertools.chain.from_iterable(clip_iterators))


def _get_clips_json(clips, station):
    
    # See note near the top of this file about why we send local
    # instead of UTC times to clients.
        
    utc_to_local = station.utc_to_local
    clip_dicts = [_get_clip_dict(c, utc_to_local) for c in clips]
    result = json.dumps(clip_dicts)
    return result


def _get_clip_dict(clip, utc_to_local):
    
    # See note about UTC and local times near the top of this file.
    start_time = _format_time(utc_to_local(clip.start_time))
    
    return {
        'id': clip.id,
        'url': clip.wav_file_url,
        'length': clip.length,
        'sampleRate': clip.sample_rate,
        'startTime': start_time,
    }

    
# def _get_rc_pair_annotations(
#         rc_pairs, time_interval, detector, annotation_name, annotation_value):
#      
#     annotation_iterators = [
#         _get_annotations(
#             recording, channel_num, time_interval, detector, annotation_name,
#             annotation_value)
#         for recording, channel_num in rc_pairs]
#      
#     return list(itertools.chain.from_iterable(annotation_iterators))
# 
# 
# def _get_clips_json(annotations, station):
#      
#     # See note near the top of this file about why we send local
#     # instead of UTC times to clients.
#          
#     utc_to_local = station.utc_to_local
#     clip_dicts = [_get_clip_dict(a, utc_to_local) for a in annotations]
#     return json.dumps(clip_dicts)
#      
#      
# def _get_clip_dict(annotation, utc_to_local):
#      
#     clip = annotation.clip
#      
#     # See note about UTC and local times near the top of this file.
#     start_time = _format_time(utc_to_local(clip.start_time))
#     return {
#         'id': clip.id,
#         'url': clip.wav_file_url,
#         'length': clip.length,
#         'sampleRate': clip.sample_rate,
#         'startTime': start_time,
#         'classification': annotation.value
#     }

    
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
    
    
def _add_wildcard_classifications(classifications):
    prefixes = set()
    for c in classifications:
        prefixes.add(c)
        prefixes |= _add_wildcard_classifications_aux(c)
    return sorted(prefixes)
        
        
def _add_wildcard_classifications_aux(classification):
    parts = classification.split(_ANNOTATION_VALUE_COMPONENT_SEPARATOR)
    prefixes = []
    for i in range(1, len(parts)):
        prefix = _ANNOTATION_VALUE_COMPONENT_SEPARATOR.join(parts[:i])
        prefixes.append(prefix)
        prefixes.append(prefix + _WILDCARD)
        prefixes.append(
            prefix + _ANNOTATION_VALUE_COMPONENT_SEPARATOR + _WILDCARD)
    return frozenset(prefixes)
        
        
def _get_clip_counts_old(
        station, microphone_output, detector, annotation_name,
        annotation_value):

    time_zone = pytz.timezone(station.time_zone)
    rm_infos = model_utils.get_recorder_microphone_infos(
        station, microphone_output)
    microphone_output_id = microphone_output.id
    
    recordings = Recording.objects.filter(station=station)
    clip_counts = defaultdict(int)
    
    for recording in recordings:
        
        channel_num = model_utils.get_microphone_output_channel_num(
            recording, microphone_output_id, rm_infos)
        
        if channel_num is not None:
            
            # TODO: We assume in this function that a recording starts and
            # ends the same night. In the future, we may want to support
            # recordings that span multiple nights. That will look fairly
            # different from what we do here. This function will be replaced
            # by a `_get_clip_count` function that accepts the same arguments
            # as this function plus a `time_interval` argument. The function
            # will be called once for each night, and the `time_interval`
            # argument will specify the interval of the night.
            #
            # The time interval of an archive will not be determined from
            # counts for a particular annotation as it is now, but rather
            # from the intervals of the recordings that are in the archive
            # for a particular station and microphone output.
                        
            start_time = recording.start_time
            night = _get_night(start_time, time_zone)
            
            time_interval = (start_time, recording.end_time)
            clip_count = _get_clip_count(
                recording, channel_num, time_interval, detector,
                annotation_name, annotation_value)
            
            clip_counts[night] += clip_count
                
#     print('_get_clip_counts:')
#     nights = sorted(clip_counts.keys())
#     for night in nights:
#         print('   ', night, clip_counts[night])
        
    return clip_counts          


def _get_night(utc_time, time_zone):
    local_time = utc_time.astimezone(time_zone)
    night = local_time.date()
    if local_time.hour < 12:
        night -= _ONE_DAY
    return night


def _get_clip_count(
        recording, channel_num, time_interval, detector, annotation_name,
        annotation_value):
    
    if annotation_value == _IGNORE_ANNOTATION or \
            annotation_value == _NO_ANNOTATION:
        
        clips = _get_rc_pair_clips(
            recording, channel_num, time_interval, detector,
            annotation_name, annotation_value)
            
        return clips.count()
    
    else:
        
        annotations = _get_annotations(
            recording, channel_num, time_interval, detector,
            annotation_name, annotation_value)
        
        return annotations.count()
            

# TODO: Something along the lines of the following seems like it should
# be a more efficient way to query for unannotated clips, but I haven't
# been able to get it to work yet.
_UNANNOTATED_CLIPS_QUERY = '''
SELECT *
FROM vesper_clip
LEFT JOIN vesper_string_annotation
ON vesper_clip.id = vesper_string_annotation.clip_id
WHERE (
    vesper_clip.recording_id = %s AND
    vesper_clip.channel_num = %s AND
    vesper_clip.start_time < %s AND
    vesper_clip.end_time > %s AND
    vesper_clip.creating_processor_id = %s AND
    vesper_string_annotation.info_id = %s AND
    vesper_string_annotation.value IS NULL);
'''


def _get_rc_pair_clips(
        recording, channel_num, time_interval, detector, annotation_name,
        annotation_value):
    
    start_time, end_time = time_interval
    
    clips = Clip.objects.filter(
        recording=recording,
        channel_num=channel_num,
        start_time__lt=end_time,
        end_time__gt=start_time,
        creating_processor=detector)
    
    if annotation_value != _IGNORE_ANNOTATION:
        
        info = AnnotationInfo.objects.get(name=annotation_name)
        
        if annotation_value == _NO_ANNOTATION:
            clips = clips.exclude(string_annotation__info=info)
        
        elif annotation_value == _WILDCARD:
            # querying for any annotation value
            
            clips = clips.filter(string_annotation__info=info)
            
        elif annotation_value.endswith(_WILDCARD):
            # querying for annotation values with a particular prefix
            
            prefix = annotation_value[:-len(_WILDCARD)]
            clips = clips.filter(
                string_annotation__info=info,
                string_annotation__value__startswith=prefix)
            
        else:
            # querying for a single annotation value
            
            clips = clips.filter(
                string_annotation__info=info,
                string_annotation__value=annotation_value)
            
#     print(clips.query)
    
    return clips


def _get_annotations(
        recording, channel_num, time_interval, detector, annotation_name,
        annotation_value):
    
    # Filter annotation values first by clip attributes. This part of the
    # query is the same regardless of the annotation value.
    start_time, end_time = time_interval
    annotations = StringAnnotation.objects.filter(
        clip__recording=recording,
        clip__channel_num=channel_num,
        clip__start_time__lt=end_time,
        clip__end_time__gt=start_time,
        clip__creating_processor=detector)


    # Filter annotation values by annotation attributes. This part of the
    # query varies according to the annotation value.
    
    info = AnnotationInfo.objects.get(name=annotation_name)
    
    if annotation_value == _WILDCARD:
        # querying for any annotation value
        
        annotations = annotations.filter(info=info)
        
    elif annotation_value.endswith(_WILDCARD):
        # querying for annotation values with a particular prefix
        
        annotations = annotations.filter(
            info=info,
            value__startswith=annotation_value[:-1])
        
    else:
        # querying for a single annotation value
        
        annotations = annotations.filter(
            info=info,
            value=annotation_value)

#     print(annotations.query)
    
    return annotations


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
def import_archive_data(request):
    
    if request.method in _GET_AND_HEAD:
        form = ImportArchiveDataForm()
        
    elif request.method == 'POST':
        
        form = ImportArchiveDataForm(request.POST)
        
        if form.is_valid():
            command_spec = _create_import_archive_data_command_spec(form)
            return _start_job(command_spec, request.user)
            
    else:
        return HttpResponseNotAllowed(('GET', 'HEAD', 'POST'))
    
    context = _create_template_context(request, 'Import', form=form)
    
    return render(request, 'vesper/import-archive-data.html', context)
    
    
def _create_import_archive_data_command_spec(form):
    
    data = form.cleaned_data
    
    return {
        'name': 'import',
        'arguments': {
            'importer': {
                'name': 'Archive Data Importer',
                'arguments': {
                    'archive_data': data['archive_data']
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


def job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    command_spec = json.loads(job.command)
    context = _create_template_context(
        request, job=job, command_name=command_spec['name'])
    return render(request, 'vesper/job.html', context)
