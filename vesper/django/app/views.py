import datetime
import json
import os.path

from django import forms
from django.conf import settings
from django.db.models import Max, Min
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
import pytz
import yaml

from vesper.django.app.import_archive_data_form import ImportArchiveDataForm
from vesper.django.app.import_recordings_form import ImportRecordingsForm
from vesper.django.app.models import Annotation, Clip, Job, Station
from vesper.util.bunch import Bunch
import vesper.django.app.clips_rug_plot as clips_rug_plot
import vesper.django.app.job_manager as job_manager
import vesper.util.calendar_utils as calendar_utils
import vesper.util.time_utils as time_utils


def _create_navbar_items(data, ancestors=()):
    return tuple(_create_navbar_item(d, ancestors) for d in data)


def _create_navbar_item(data, ancestors):
    if isinstance(data, str):
        return _create_navbar_link_item(data, ancestors)
    else:
        return _create_navbar_dropdown_item(data[0], data[1:], ancestors)
    

def _create_navbar_link_item(name, ancestors):
    href = _create_navbar_href(name, ancestors)
    return Bunch(type='link', name=name.title(), href=href)


def _create_navbar_dropdown_item(name, data, ancestors):
    subitems = _create_navbar_items(data, ancestors + (name,))
    return Bunch(type='dropdown', name=name.title(), subitems=subitems)


def _create_navbar_href(name, ancestors):
    parts = tuple(_create_navbar_href_aux(a) for a in ancestors) + \
        (_create_navbar_href_aux(name),)
    return '_'.join(parts)
    
    
def _create_navbar_href_aux(s):
    return '_'.join(s.split())


# Note that as of 2016-07-19, nested havbar dropdowns do not work.
# The generated HTML looks right to me so the problem may be a
# Bootstrap limitation.
_NAVBAR_ITEMS = _create_navbar_items((
    'calendar',
    ('import', 'archive data', 'recordings'),
    'detect',
    'classify',
    'export'
))

_CLASSIFICATIONS = ('Call', 'Call.WIWA', 'Call.CHSP', 'Unknown')
_ONE_DAY = datetime.timedelta(days=1)
_GET_AND_HEAD = ('GET', 'HEAD')


def index(request):
    return redirect(reverse('calendar'))


def detect(request):
    return _render_coming_soon(request, 'Detect', 'Detection is coming soon...')
    
    
def _render_coming_soon(request, action, message):
    context = {
        'navbar_items': _NAVBAR_ITEMS,
        'active_navbar_item': action,
        'message': message
    }
    return render(request, 'vesper/coming-soon.html', context)


def classify(request):
    return _render_coming_soon(
        request, 'Classify', 'Classification is coming soon...')
    
    
def import_(request):
    context = {
        'navbar_items': _NAVBAR_ITEMS,
        'active_navbar_item': 'Import'
    }
    return render(request, 'vesper/import.html', context)
    
    
def export(request):
    return _render_coming_soon(
        request, 'Export', 'Exports are coming soon...')
    
    
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
    clips = Clip.objects.filter(station__name=station.name)
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
    
    if request.method in _GET_AND_HEAD:
        content = _get_presets_json(preset_type_name)
        return HttpResponse(content, content_type='application/json')
    
    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)


def _get_presets_json(preset_type_name):
    
    # Gets all presets of the specified type as JSON.
    #
    # The presets are read from the preset directory whose name is
    # `preset_type_name`. If the directory does not exist, this function
    # returns the same JSON as it would if the directory did exist but
    # was empty.
    #
    # The returned JSON is a hierarchical list whose structure mirrors
    # the directory structure within the `preset_type_name` directory,
    # and which contains JSON preset representations. The top-level list
    # is of the form:
    #
    #     [<preset_dir_name>, <preset_subdirs>, <presets>]
    #
    # where <preset_dir_name> is `preset_type_name` (i.e. the name of
    # the top-level preset directory), <preset_subdirs> is a list of lists,
    # each of which has the same form as the top-level list and recursively
    # represents a subdirectory of the top-level preset directory, and
    # <presets> is a list of lists of the form:
    #
    #    [<preset_name>, <preset>]
    #
    # Where <preset_name> is the name of a preset in the directory
    # <preset_dir_name> and <preset> is a JSON representation of that
    # preset. The preset name is obtained from the name of the file
    # containing the preset by removing its file name extension.
    #
    # For example, for the preset directory with this structure:
    #
    #     Annotation Commands/
    #         Bob/
    #             2015/
    #                 Coarse.yaml
    #                 Calls.yaml
    #             2016/
    #                 Coarse.yaml
    #                 Calls.yaml
    #         Sue/
    #             Coarse.yaml
    #             Calls.yaml
    #
    # This function will return the following JSON (less the formatting
    # and comments):
    #
    #     ["Annotation Commands",
    #         [
    #             ["Bob",
    #                 [
    #                     ["2015",
    #                         [],    # no subdirectories of directory "2015"
    #                         [
    #                             ["Coarse", ...],
    #                             ["Calls", ...]
    #                         ]
    #                     ],
    #                     ["2016",
    #                         [],    # no subdirectories of directory "2016"
    #                         [
    #                             ["Coarse", ...],
    #                             ["Calls", ...]
    #                         ]
    #                     ]
    #                 ],
    #                 []    # no preset files in directory "Bob"
    #             ],
    #             ["Sue",
    #                 [],   # no subdirectories of directory "Sue"
    #                 [
    #                     ["Coarse", ...],
    #                     ["Calls", ...]
    #                 ]
    #             ]
    #         ],
    #         []    # no preset files in directory "Annotation Commands"
    #     ]
        
    dir_path = os.path.join(
        settings.VESPER_DATA_DIR, 'Presets', preset_type_name)
    
    if not os.path.exists(dir_path):
        presets = [preset_type_name, [], []]
    else:
        presets = _read_dir_presets(dir_path)
        
    return json.dumps(presets)
            

def _read_dir_presets(dir_path):
    
    dir_name = os.path.basename(dir_path)
    
    for _, dir_names, file_names in os.walk(dir_path):
        
        dir_names.sort()
        dirs_list = [_read_dir_presets(os.path.join(dir_path, name))
                     for name in dir_names]
        
        file_names.sort()
        files_list = [_read_file_preset(dir_path, name) for name in file_names]
        files_list = [item for item in files_list if item is not None]
        
        # Stop walk from descending into subdirectories.
        del dir_names[:]
        
    return [dir_name, dirs_list, files_list]
        
        
def _read_file_preset(dir_path, file_name):
    
    # Get preset name from file name.
    preset_name = _get_preset_name(file_name)
    if preset_name is None:
        return None
    
    # Read file contents.
    file_path = os.path.join(dir_path, file_name)
    try:
        with open(file_path) as file_:
            text = file_.read()
    except Exception:
        # TODO: Log error.
        return None
    
    # Parse file contents.
    try:
        preset = yaml.load(text)
    except Exception:
        # TODO: Log error.
        return None
    
    return [preset_name, preset]

    
_PRESET_FILE_NAME_EXTENSIONS = ('.yaml', '.yml')


def _get_preset_name(file_name):
    for extension in _PRESET_FILE_NAME_EXTENSIONS:
        if file_name.endswith(extension):
            return file_name[:-len(extension)]


@csrf_exempt
def annotation(request, clip_id, annotation_name):
    
    name = annotation_name
    
    if request.method in _GET_AND_HEAD:
        annotation = get_object_or_404(Annotation, name=name, clip__id=clip_id)
        response = HttpResponse()
        response.write(annotation.value)
        return response
    
    elif request.method == 'PUT':
        value = _get_request_body_as_text(request).strip()
        try:
            annotation = Annotation.objects.get(clip__id=clip_id, name=name)
        except Annotation.DoesNotExist:
            clip = get_object_or_404(Clip, id=clip_id)
            annotation = Annotation(clip=clip, name=name, value=value)
        else:
            annotation.value = value
        annotation.save()
        return HttpResponse()

    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)
    

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
    
    context = {
        'navbar_items': _NAVBAR_ITEMS,
        'active_navbar_item': 'Calendar',
    }
    
    stations = Station.objects.order_by('name')
    
    if len(stations) != 0:
        # have at least one station
        
        classifications = _add_wildcard_classifications(_CLASSIFICATIONS)
        
        params = request.GET
        station_name = params.get('station', stations[0].name)
        classification = params.get('classification', classifications[0])
        
        station = Station.objects.get(name=station_name)
        
        clip_counts = _get_clip_counts(
            station, 'Classification', classification)
        
        dates = sorted(list(clip_counts.keys()))
        periods = calendar_utils.get_calendar_periods(dates)
        periods_json = \
            calendar_utils.get_calendar_periods_json(periods, clip_counts)
        
        context.update(
            stations=stations,
            station_name=station_name,
            classifications=classifications,
            classification=classification,
            periods_json=periods_json
        )
            
    return render(request, 'vesper/calendar.html', context)

    
def night(request):
    
    stations = Station.objects.order_by('name')
    
    if len(stations) == 0:
        # no stations (or recordings or clips)
        
        context = {}
        
    else:
        # have at least one station
        
        classifications = _add_wildcard_classifications(_CLASSIFICATIONS)
        
        # TODO: Type check and range check query items.
        params = request.GET
        station_name = params.get('station', stations[0].name)
        classification = params.get('classification', classifications[0])
        date = params.get('date')
        page_start_index = int(params.get('start')) - 1
        page_size = int(params.get('size'))
        selected_index = int(params.get('selected', '0')) - 1
        if selected_index == -1:
            selected_index = 'null';
        
        station = Station.objects.get(name=station_name)
        
        time_zone = pytz.timezone(station.time_zone)
        night = time_utils.parse_date(*date.split('-'))
        time_interval = _get_night_interval(night, time_zone)

        annotations = _get_annotations(
            station, 'Classification', classification, time_interval)
        
        num_clips = len(annotations)
        page_start_index = _limit_index(page_start_index, 0, num_clips - 1)
        page_end_index = min(page_start_index + page_size, num_clips)
        
        utc_times = [a.clip.start_time for a in annotations]
        start_times = [t.astimezone(time_zone) for t in utc_times]
        
        rug_plot_script, rug_plot_div = \
            clips_rug_plot.create_rug_plot(station, night, start_times)
        
        clips_json = _get_clips_json(
            annotations, start_times, page_start_index, page_end_index)
        
        annotation_schemes_presets_json = \
            _get_presets_json('Annotation Scheme')
            
        annotation_commands_presets_json = \
            _get_presets_json('Annotation Commands')

        context = {
            'navbar_items': _NAVBAR_ITEMS,
            'active_navbar_item': '',
            'station_name': station_name,
            'classification': classification,
            'date': date,
            'rug_plot_script': rug_plot_script,
            'rug_plot_div': rug_plot_div,
            'num_clips': len(annotations),
            'page_start_index': page_start_index,
            'page_size': page_size,
            'selected_index': selected_index,
            'clips_json': clips_json,
            'annotation_scheme_presets_json': annotation_schemes_presets_json,
            'annotation_commands_presets_json': annotation_commands_presets_json
        }
        
    return render(request, 'vesper/night.html', context)
    
        
def _get_clips_json(annotations, start_times, start_index, end_index):
    all_pairs = list(zip(annotations, start_times))
    page_pairs = all_pairs[start_index:end_index]
    clip_dicts = [_get_clip_dict(*p) for p in page_pairs]
    return json.dumps(clip_dicts)
    
    
def _get_clip_dict(annotation, start_time):
    clip = annotation.clip
    return {
        'id': clip.id,
        'url': clip.wav_file_url,
        'length': clip.length,
        'sampleRate': clip.sample_rate,
        'startTime': _format_start_time(start_time),
        'classification': annotation.value
    }

    
def _format_start_time(time):
    
    prefix = time.strftime('%Y-%m-%d %H:%M:%S')
    millis = int(round(time.microsecond / 1000.))
    millis = '{:03d}'.format(millis)
    while len(millis) != 0 and millis[-1] == '0':
        millis = millis[:-1]
    time_zone = time.strftime('%Z')
    
    if len(millis) == 0:
        return prefix + ' ' + time_zone
    else:
        return prefix + '.' + millis + ' ' + time_zone


def _limit_index(index, min_index, max_index):
    if index < min_index:
        return min_index
    elif index > max_index:
        return max_index
    else:
        return index
    
    
def _add_wildcard_classifications(classifications):
    prefixes = set('*')
    for c in classifications:
        prefixes.add(c)
        prefixes |= _add_wildcard_classifications_aux(c)
    prefixes = list(prefixes)
    prefixes.sort()
    return prefixes
        
        
def _add_wildcard_classifications_aux(classification):
    parts = classification.split('.')
    prefixes = []
    for i in range(1, len(parts)):
        prefix = '.'.join(parts[:i])
        prefixes.append(prefix)
        prefixes.append(prefix + '*')
        prefixes.append(prefix + '.*')
    return frozenset(prefixes)
        
        
def _get_clip_counts(station, annotation_name, annotation_value):
    
    time_zone = pytz.timezone(station.time_zone)
    
    start_night, end_night = \
        _get_night_range(station, time_zone, annotation_name, annotation_value)
    
    counts = {}
    
    if start_night is not None:
        
        night = start_night
        
        while night <= end_night:
            
            time_interval = _get_night_interval(night, time_zone)
            
            annotations = _get_annotations(
                station, annotation_name, annotation_value, time_interval)
            
            count = len(annotations)
            
            if count != 0:
                counts[night] = count
                
            night += _ONE_DAY
        
    return counts


def _get_night_range(station, time_zone, annotation_name, annotation_value):
    first_time, last_time = _get_clip_start_time_extrema_for_annotation(
        station, annotation_name, annotation_value)
    if first_time is None:
        return (None, None)
    else:
        start_night = _get_night(first_time, time_zone)
        end_night = _get_night(last_time, time_zone)
        return (start_night, end_night)


def _get_clip_start_time_extrema_for_annotation(
        station, annotation_name, annotation_value):
    
    if annotation_value.endswith('*'):
        
        annotations = Annotation.objects.filter(
            clip__station__name=station.name,
            name=annotation_name,
            value__startswith=annotation_value[:-1])
        
    else:
        
        annotations = Annotation.objects.filter(
            clip__station__name=station.name,
            name=annotation_name,
            value=annotation_value)
        
    times = annotations.aggregate(
        first_time=Min('clip__start_time'),
        last_time=Max('clip__start_time'))
    
    return (times['first_time'], times['last_time'])
    
    
def _get_night(utc_time, time_zone):
    local_time = utc_time.astimezone(time_zone)
    night = local_time.date()
    if local_time.hour < 12:
        night -= _ONE_DAY
    return night


def _get_night_interval(night, time_zone):
    start_time = _get_local_noon_as_utc_time(night, time_zone)
    end_time = _get_local_noon_as_utc_time(night + _ONE_DAY, time_zone)
    return (start_time, end_time)
    
    
def _get_local_noon_as_utc_time(date, time_zone):
    noon = datetime.time(12)
    dt = datetime.datetime.combine(date, noon)
    dt = time_zone.localize(dt)
    return dt.astimezone(pytz.utc)


def _get_annotations(station, annotation_name, annotation_value, time_interval):
    
    if annotation_value.endswith('*'):
        
        return Annotation.objects.filter(
            clip__station=station,
            clip__start_time__range=time_interval,
            name=annotation_name,
            value__startswith=annotation_value[:-1])
        
    else:
        
        return Annotation.objects.filter(
            clip__station=station,
            clip__start_time__range=time_interval,
            name=annotation_name,
            value=annotation_value)


@csrf_exempt
def test_command(request):
    
    if request.method in _GET_AND_HEAD:
        form = forms.Form()
        
    elif request.method == 'POST':
        form = forms.Form(request.POST)
        if form.is_valid():
            print('form valid')
            command_spec = {'name': 'test'}
            job_id = job_manager.start_job(command_spec)
            return HttpResponseRedirect('/vesper/jobs/{}'.format(job_id))
        else:
            print('form invalid')
            
    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)
    
    return render(request, 'vesper/test-command.html', {'form': form})

    
@csrf_exempt
def import_archive_data(request):
    
    if request.method in _GET_AND_HEAD:
        form = ImportArchiveDataForm()
        
    elif request.method == 'POST':
        form = ImportArchiveDataForm(request.POST)
        if form.is_valid():
            print('form valid')
            command_spec = {
                'name': 'import',
                'arguments': {
                    'importer': {
                        'name': 'Archive Data Importer',
                        'arguments': {
                            'archive_data': form.cleaned_data['archive_data']
                        }
                    }
                }
            }
            job_id = job_manager.start_job(command_spec)
            return HttpResponseRedirect('/vesper/jobs/{}'.format(job_id))
        else:
            print('form invalid')
            
    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)
    
    context = {
        'navbar_items': _NAVBAR_ITEMS,
        'active_navbar_item': 'Import',
        'form': form
    }
    
    return render(request, 'vesper/import-archive-data.html', context)
    
    
@csrf_exempt
def import_recordings(request):
    
    if request.method in _GET_AND_HEAD:
        form = ImportRecordingsForm()
        
    elif request.method == 'POST':
        form = ImportRecordingsForm(request.POST)
        if form.is_valid():
            print('form valid')
#             command_spec = {'name': 'test'}
#             job_id = job_manager.start_job(command_spec)
#             return HttpResponseRedirect('/vesper/jobs/{}'.format(job_id))
        else:
            print('form invalid')
            
    else:
        return HttpResponseNotAllowed(_GET_AND_HEAD)
    
    context = {
        'navbar_items': _NAVBAR_ITEMS,
        'active_navbar_item': 'Import',
        'form': form
    }
    
    return render(request, 'vesper/import-recordings.html', context)
    
    
'''
commands needed:

import archive data:
    stations
    device models
    devices
    station devices (does this take care of device connections?)

import recordings

run detectors

run classifiers
'''


def job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    command_spec = json.loads(job.command)
    context = {
        'job': job,
        'command_name': command_spec['name']
    }
    return render(request, 'vesper/job.html', context)
      
          
'''
Some important queries:

* Recordings by station/night/recorder/microphone

    Select on what you can, then use Python, for example for time
    interval intersection.
    
    recordings = Recording.objects.filter(
        station__name=station_name,
        recorder=recorder)
        
    recordings = [
        r for r in recordings
        if _filter_by_time(r, time_interval) and _filter_by_mic(r, microphone)]
        
* Clips (annotations, actually, each of which has a unique clip) for a
  particular recording and annotation:

    recording = ...
    annotation_name = 'Classification'
    annotation_value = 'Call.WIWA'
    annotations = Annotation.objects.filter(
        clip__recording=recording,
        name=annotation_name,
        value=annotation_value)

* Clips (annotations, actually, each of which has a unique clip) for a
  particular station, night, and annotation:

    station_name = 'Baldy'
    time_interval = ...
    annotation_name = 'Classification'
    annotation_value = 'Call.WIWA'
    annotations = Annotation.objects.filter(
        clip__station__name=station_name,
        clip__start_time__range=time_interval,
        name=annotation_name,
        value=annotation_value)

* Clips with combinations of annotations:

    For example, one might want to find the clips that were classified
    differently by two different classifiers.
    
    I don't see a way to do this with a single query. I think we must
    execute a separate query for each separate annotation name and then
    process the query results further in Python.
'''


# The initial implementation of this view generated all of the calendar
# as HTML on the server. See below for the Django template that generated
# the HTML. I switched to sending calendar data as JSON to the client and
# creating DOM elements from Javascript on the client. The JSON approach
# requires that less data be sent to the client. Does it really matter?
# I'm not sure.
#
# def _format_calendar(periods, clip_counts):
#     return [_format_calendar_period(p, clip_counts) for p in periods]
# 
# 
# def _format_calendar_period(period, clip_counts):
#     
#     num_months = period.end - period.start + 1
#     months = list(period.start + i for i in range(num_months))
#     
#     if num_months > 3:
#         
#         num_initial_empty_months = (period.start.month - 1) % 3
#         initial_months = [None] * num_initial_empty_months
#         
#         m = (num_initial_empty_months + num_months) % 3
#         num_final_empty_months = 0 if m == 0 else 3 - m
#         final_months = [None] * num_final_empty_months
#         
#     else:
#         # three or fewer months
#         
#         initial_months = []
#         final_months = [None] * (3 - num_months)
#         
#     months = initial_months + months + final_months
#     
#     rows = []
#     i = 0
#     while i != len(months):
#         row_months = months[i:i + 3]
#         month_infos = [_get_month_info(m, clip_counts) for m in row_months]
#         rows.append(month_infos)
#         i += 3
#         
#     if num_months == 1:
#         # only one month in this period
#         
#         # suppress display of month name since it's same as period name
#         rows[0][0].name = None
#         
#     return Bunch(name=period.name, rows=rows)
#     
#     
# def _get_month_info(month, clip_counts):
#     if month is None:
#         return None
#     else:
#         name = calendar.month_name[month.month]
#         name = '{} {}'.format(name, month.year)
#         days = _get_days_info(month, clip_counts)
#         return Bunch(name=name, days=days)
# 
# 
# def _get_days_info(month, clip_counts):
#     calendar.setfirstweekday(calendar.SUNDAY)
#     days = calendar.monthcalendar(month.year, month.month)
#     days = itertools.chain.from_iterable(days)
#     return [_get_day_info(d, month, clip_counts) for d in days]
# 
# 
# def _get_day_info(day, month, clip_counts):
#     if day == 0:
#         return None
#     else:
#         date = datetime.date(year=month.year, month=month.month, day=day)
#         count = clip_counts.get(date, 0)
#         radius = _get_radius(count)
#         return Bunch(num=day, count=count, radius=radius)
# 
#     
# def _get_radius(count):
#     if count == 0:
#         return 0
#     else:
#         return 25 + 15 * math.log10(count)
#
#
# The following is part of a Django HTML template that was used to construct
# the clip calendar on the server before I switched to constructing the
# calendar on the client using Javascript. I'm not sure which approach is
# better, and each may have different advantages over the other. The template
# is shorter than the Javascript, for example, but using the template requires
# transferring a lot more data from server to client. I wonder if some
# sort of client-side templating facility would be best. My initial
# impression is that the more declarative style of templates makes
# them easier to read than Javascript. A blog post that I came across
# that relates to this is
# www.onebigfluke.com/2015/01/experimentally-verified-why-client-side.html.
# 
#       <div>
#       
#       {% if periods %}
#       
#       {% for period in periods %}
#       
#         <div class="period">
#       
#         <h2 class="period-name">{{period.name}}</h2>
#       
#           {% for row in period.rows %}
#         
#             <div class="row">
#             
#             {% for month in row %}
#            
#               {% if month == None %}
#                 <div class="col-sm-4 month"></div>
#               {% else %}
#                 <div class="col-sm-4 month">
#                   {% if month.name != None %}
#                     <h3 class="month-name">{{month.name}}</h3>
#                   {% endif %}
#                   <div class="month-days">
#                     {% for day in month.days %}
#                       <div class="day">
#                         {% if day == None %}
#                           <div></div>
#                         {% else %}
#                           <div class="circle" data-radius="{{day.radius}}" style="width:{{day.radius}}px;height:{{day.radius}}px"></div>
#                           <a class="day-num" href="#">{{day.num}}</a>
#                         {% endif %}
#                       </div>
#                     {% endfor %}
#                   </div>
#                 </div>
#               {% endif %}
#             
#             {% endfor %}
#             
#             </div>
#           
#           {% endfor %}
#         
#         </div>
#         
#       {% endfor %}
#       
#       {% else %}
#       
#         There are no such clips in the archive.
#         
#       {% endif %}
#       
#       </div>
#       
#     </div>
