from datetime import datetime as DateTime, timedelta as TimeDelta
import logging
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views import View

from vesper.django.app.models import (
    AnnotationInfo, Clip, Device, DeviceOutput, Processor, Recording,
    RecordingChannel, Station)
import vesper.django.app.model_utils as model_utils
import vesper.django.util.view_utils as view_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


# TODO: Consider the relationship between this view and the Vesper view
#       that imports metadata. The Vesper view uses a form while this view
#       uses JSON. The sets of object types supported by the two views are
#       disjoint except for `AnnotationInfo` objects.

# TODO: Reconsider supporting automatic `AnnotationInfo` creation. Perhaps
#       it should either not be supported or not allowed by default?

# TODO: Support creating clips with tags. As part of that, consider
#       supporting `TagInfo` creation. 

# TODO: Consider moving all Old Bird Django code to this app.


_ONE_MICROSECOND = TimeDelta(microseconds=1)

_START_TIME_UNIQUENESS_OFFSET_ANNOTATION_NAME = 'Start Time Uniqueness Offset'


class _ViewError(Exception):
    pass


class ImportRecordingsAndClipsView(View):


    # Assumptions made by this view:
    #     * The mic outputs of a recording's channels are unique. That is,
    #       no recording is ever made with one mic output connected to
    #       more than one recorder input.
    #     * The data of channel i of a recording are always from input i
    #       of the recorder.
    #     * Every clip to be created will be at least one microsecond long.

    # This class is not a subclass of Django's `LoginRequiredMixin`
    # since that would cause the `post` method to redirect to the
    # login URL if the user is not logged in. We want to simply
    # reject the request as unauthenticated rather than redirecting.


    def post(self, request):
       
        if not request.user.is_authenticated:
           # user not logged in

           
           return HttpResponse(
               'Unauthenticated', status=401, reason='Unauthenticated')
       
        else:
            # user logged in

            return view_utils.handle_json_post(request, self._post)
    

    def _post(self, content):

        self._stations = _get_stations()
        self._devices = _get_devices()
        self._device_outputs = _get_device_outputs()
        self._detectors = _get_detectors()
        self._annotation_info_cache = {}

        try:

            with transaction.atomic():
                recordings = self._create_recordings(content)
                clips = self._create_clips(content)
               
        except Exception as e:
            error_message = (
                f'{e} No recordings or clips will be created for this '
                f'request.')
            return HttpResponseBadRequest(
                content=error_message, content_type='text/plain')
        
        data = {
            'recordings': recordings,
            'clips': clips
        }

        return JsonResponse(data)
        

    def _create_recordings(self, content):
        infos = content.get('recordings', [])
        return [self._create_recording(i) for i in infos]                  


    def _create_recording(self, info):

        try:

            _check_for_items(
                info,
                ('station', 'recorder', 'mic_outputs', 'start_time', 'length',
                 'sample_rate'),
                f'recording data')

            station_name = info['station']
            station = self._get_station(station_name)

            recorder_name = info['recorder']
            recorder = self._get_device(recorder_name)

            mic_output_names = info['mic_outputs']
            mic_outputs = \
                [self._get_device_output(n) for n in mic_output_names]
            channel_count = len(mic_outputs)

            start_time = _parse_datetime(info['start_time'], 'recording start')

            length = info['length']

            sample_rate = info['sample_rate']

            end_time = \
                signal_utils.get_end_time(start_time, length, sample_rate)
            
            creation_time = time_utils.get_utc_now()

            try:

                # It's important to create the recording within a nested
                # transaction that can be rolled back if the recording
                # already exists. Without the nested transaction and the
                # rollback the `Recording.objects.get` call below would
                # raise a `TransactionManagementError` exception.
                with transaction.atomic():
                    recording = Recording.objects.create(
                        station=station,
                        recorder=recorder,
                        num_channels=channel_count,
                        length=length,
                        sample_rate=sample_rate,
                        start_time=start_time,
                        end_time=end_time,
                        creation_time=creation_time,
                        creating_job=None)
                    
            except IntegrityError:
                # recording exists

                created = False
                
                recording = Recording.objects.get(
                    station=station,
                    recorder=recorder,
                    start_time=start_time)
                
            else:
                # recording did not already exist

                created = True

                # Create recording channels.
                for i, mic_output in enumerate(mic_outputs):
                    RecordingChannel.objects.create(
                        recording=recording,
                        channel_num=i,
                        recorder_channel_num=i,
                        mic_output=mic_output)
                    
        except Exception as e:
            raise _ViewError(
                f'Could not create recording from recording data {info}. '
                f'Error message was: {e}')

        return {
            'id': recording.id,
            'created': created
        }


    def _create_clips(self, content):
        infos = content.get('clips', [])
        return [self._create_clip(i) for i in infos]  


    def _create_clip(self, info):

        try:

            _check_for_items(
                info,
                ('station', 'mic_output', 'detector', 'start_time', 'length'),
                f'clip data')

            station_name = info['station']
            station = self._get_station(station_name)

            mic_output_name = info['mic_output']
            mic_output = self._get_device_output(mic_output_name)

            detector_name = info['detector']
            detector_model = self._get_detector(detector_name)

            start_time = info['start_time']
            start_time = _parse_datetime(start_time, 'clip start')

            serial_num = info.get('serial_num', 0)

            # Offset start time if needed to ensure uniqueness. Vesper
            # currently requires that each clip's recording channel,
            # creating processor, and start time be unique. We use clip
            # serial numbers in some projects to distinguish between
            # clips that have the same start time, and we convert those
            # to start time offsets here. At some point I hope to remove
            # Vesper's uniqueness requirement, at which point we can
            # eliminate the serial numbers and offsets.
            if serial_num != 0:
                offset = TimeDelta(microseconds=serial_num)
                start_time += offset

            length = info['length']

            recording = self._get_clip_recording(
                station, mic_output, start_time)
            
            sample_rate = recording.sample_rate

            end_time = signal_utils.get_end_time(
                start_time, length, sample_rate)
            
            self._check_clip_extent(start_time, end_time, recording)
                
            recording_channel = self._get_clip_recording_channel(
                    recording, station, mic_output, start_time)

            # We set the start indices of Old Bird detector clips to `None`
            # since we do not know them exactly (we know only the clips'
            # start times to the nearest second). We can attempt to find
            # the start indices later by locating the clips' samples in
            # their recordings.
            if detector_name.startswith('Old Bird'):
                start_index = None
            else:
                td = start_time - recording.start_time
                start_index = int(round(td.total_seconds() * sample_rate))

            date = station.get_night(start_time)

            creation_time = time_utils.get_utc_now()

            try:

                # It's important to create the clip within a nested
                # transaction that can be rolled back if the clip already
                # exists. Without the nested transaction and the rollback,
                # subsequent attempts to access the database within the
                # outer transaction would raise a `TransactionManagementError`
                # exception.
                with transaction.atomic():
                    clip = Clip.objects.create(
                        station=station,
                        mic_output=mic_output,
                        recording_channel=recording_channel,
                        start_index=start_index,
                        length=length,
                        sample_rate=sample_rate,
                        start_time=start_time,
                        end_time=end_time,
                        date=date,
                        creation_time=creation_time,
                        creating_user=None,
                        creating_job=None,
                        creating_processor=detector_model)

            except IntegrityError:
                # clip exists

                created = False
                
                clip = Clip.objects.get(
                    recording_channel=recording_channel,
                    start_time=start_time,
                    creating_processor=detector_model)
                
            else:
                # clip did not already exist

                created = True
                
                annotations = info.get('annotations', {})

                # If clip start time was offset, include an annotation
                # indicating by how many seconds. This will make it
                # possible to remove the offset later if needed.
                if serial_num != 0:
                    name = _START_TIME_UNIQUENESS_OFFSET_ANNOTATION_NAME
                    offset = serial_num / 1000000
                    annotations[name] = f'{offset:f}'

                for name, value in annotations.items():
                    
                    annotation_info = self._get_annotation_info(name)
                    
                    model_utils.annotate_clip(
                        clip, annotation_info, str(value),
                        creation_time=creation_time,
                        creating_user=None,
                        creating_job=None,
                        creating_processor=detector_model)
                
        except Exception as e:
            raise _ViewError(
                f'Could not create clip from clip data {info}. '
                f'Error message was: {e}')
                
        return {
            'id': clip.id,
            'created': created
        }


    def _get_clip_recording(self, station, mic_output, clip_start_time):

        # We use a placeholder clip end time to try to locate the
        # clip's recording. We don't know the real clip end time yet
        # because while we have the clip's length we don't have its
        # sample rate.
        # TODO: The use of a placeholder end time here is kludgy.
        # Consider either including sample rate in clip data or
        # including duration instead of length.
        placeholder_end_time = clip_start_time + _ONE_MICROSECOND
        clip_interval = (clip_start_time, placeholder_end_time)

        # Get recordings for the specified station and mic output whose
        # time intervals intersect clip time interval.
        recordings = \
            model_utils.get_recordings(station, mic_output, clip_interval)
        
        recording_count = len(recordings)

        if recording_count == 0:
            # found no recording for clip

            raise ValueError(
                f'Could not find recording for station "{station.name}", '
                f'mic output "{mic_output.name}", and clip start time '
                f'{clip_start_time}.')

        elif recording_count > 1:
            # found more than one recording for clip

            raise ValueError(
                f'Found more than one recording for station "{station.name}", '
                f'mic output "{mic_output.name}", and clip start time '
                f'{clip_start_time}.')
            
        else:
            # found exactly one recording for clip
            
            return recordings[0]


    def _check_clip_extent(self, start_time, end_time, recording):
        
        def format_dt(dt):
            return dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Check that clip does not start before recording.
        if start_time < recording.start_time:
            raise ValueError(
                f'Clip start time {format_dt(start_time)} precedes'
                f'recording start time {format_dt(recording.start_time)}.')
        
        # Check that clip does not end after recording.
        if end_time > recording.end_time:
            raise ValueError(
                f'Clip end time {format_dt(end_time)} follows '
                f'recording end time {format_dt(recording.end_time)}.')
            

    def _get_clip_recording_channel(
            self, recording, station, mic_output, start_time):
        
        channels = recording.channels.filter(mic_output=mic_output)
        channel_count = channels.count()

        if channel_count == 0:
            # found no recording channel for clip

            raise ValueError(
                f'Could not find recording channel for station '
                f'"{station.name}", mic output "{mic_output.name}" '
                f'and clip start time {start_time}.')

        elif channel_count > 1:
            # found more than one recording channel for clip

            raise ValueError(
                f'Found more than one recording channel for station '
                f'"{station.name}", mic output "{mic_output.name}" '
                f'and clip start time {start_time}.')
        
        else:
            # found exactly one recording channel for clip

            return channels.first()
        

    def _get_station(self, name):
        try:
            return self._stations[name]
        except KeyError:
            raise _ViewError(f'Unrecognized station "{name}".')
        

    def _get_device(self, name):
        try:
            return self._devices[name]
        except KeyError:
            raise _ViewError(f'Unrecognized device "{name}".')


    def _get_device_output(self, output_name):
        try:
            return self._device_outputs[output_name]
        except KeyError:
            raise _ViewError(f'Unrecognized device output "{output_name}".')


    def _get_detector(self, detector_name):
        try:
            return self._detectors[detector_name]
        except KeyError:
            raise _ViewError(f'Unrecognized detector "{detector_name}".')


    def _get_annotation_info(self, name):
        
        try:
            return self._annotation_info_cache[name]
        
        except KeyError:
            # cache miss
            
            try:
                info = AnnotationInfo.objects.get(name=name)
            
            except AnnotationInfo.DoesNotExist:
                
                logging.info(
                    f'        Adding annotation "{name}" to archive...')
                
                description = (
                    f'Created automatically for a clip that referenced it.')
                
                type_ = 'String'
                creation_time = time_utils.get_utc_now()
                creating_user = None
                creating_job = None
                
                info = AnnotationInfo.objects.create(
                    name=name,
                    description=description,
                    type=type_,
                    creation_time=creation_time,
                    creating_user=creating_user,
                    creating_job=creating_job)
            
            self._annotation_info_cache[name] = info
            return info
        

def _check_for_items(data, keys, name):
    for key in keys:
        if key not in data:
            raise ValueError(
                f'Required {name} item "{key}" is missing.')


def _get_stations():
    stations = Station.objects.all()
    return {s.name: s for s in stations}


def _get_devices():
    devices = Device.objects.all()
    return {d.name: d for d in devices}


def _get_device_outputs():
    outputs = DeviceOutput.objects.all()
    return {o.name: o for o in outputs}


def _get_detectors():
    detectors = Processor.objects.filter(type='Detector')
    return {d.name: d for d in detectors}


_DATE_TIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S.%f Z',    # with fractional seconds
    '%Y-%m-%d %H:%M:%S Z'        # without fractional seconds
)

_UTC = ZoneInfo('UTC')


def _parse_datetime(text, name):

    for format in _DATE_TIME_FORMATS:

        # Try to parse `text` as local date and time.
        try:
            dt = DateTime.strptime(text, format)
        except Exception:
            continue

        # If we get here, the parse succeeded.

        return dt.replace(tzinfo=_UTC)
    
    # If we get here, none of the parse attempts succeeded.
    raise ValueError(f'Could not parse {name} time "{text}".')
