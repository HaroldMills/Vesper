from datetime import datetime as DateTime, timedelta as TimeDelta
import logging
from zoneinfo import ZoneInfo

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views import View

from vesper.django.app.models import (
    AnnotationInfo, Clip, Processor, Recording, RecordingChannel,
    StationDevice)
import vesper.django.app.model_utils as model_utils
import vesper.django.util.view_utils as view_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


# TODO: Review code that adds recordings and clips to archive. Improve
# if needed and make sure unit tests for it are up to date.

# TODO: Consider adding recordings to archive if they are not already there,
# without regard to whether they are associated with clips.

# TODO: Consider moving all Old Bird Django code to this app.


_ONE_MICROSECOND = TimeDelta(microseconds=1)

_START_TIME_UNIQUENESS_OFFSET_ANNOTATION_NAME = 'Start Time Uniqueness Offset'


class _ViewError(Exception):
    pass


class CreateLrgvClipsView(View):

    # TODO: Make this view non-LRGV-specific.

    # Assumptions made by this view:
    #     * There is one recorder per station.
    #     * There is one microphone output per station.
    #     * All recordings are single-channel.
    #     * There is one recording per station per night.
    #     * Any clip to be created will be at least one microsecond long.

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

        self._station_mic_output_pairs = _get_station_mic_output_pairs()
        self._detectors = _get_detectors()
        self._station_recorders = _get_station_recorders()
        self._annotation_info_cache = {}

        try:

            with transaction.atomic():

                recording_infos = content.get('recordings', {})

                for recording_name, recording_info in recording_infos.items():
                    self._check_recording_info(recording_name, recording_info)
                    
                clip_infos = content.get('clips', [])
                
                clips = []

                for clip_info in clip_infos:

                    clip_id, recording_id, recording_created = \
                        self._create_clip(clip_info, recording_infos)
                                        
                    clips.append({
                        'clip_id': clip_id,
                        'recording_id': recording_id,
                        'recording_created': recording_created
                    })
                    
        except Exception as e:
            error_message = (
                f'{e} No recordings or clips will be created for this '
                f'request.')
            print(f'CreateLrgvClipsView._post error "{error_message}"')
            return HttpResponseBadRequest(
                content=error_message, content_type='text/plain')
        
        data = {'clips': clips}

        return JsonResponse(data)
        

    def _check_recording_info(self, recording_name, recording_info):

        try:

            _check_for_items(
                recording_info,
                ('start_time', 'length', 'sample_rate'),
                f'recording data')
    
        except Exception as e:
            raise _ViewError(
                f'Could not parse recording "{recording_name}" data '
                f'{recording_info}. Error message was: {e}')
    

    def _create_clip(self, clip_info, recording_infos):

        try:

            _check_for_items(
                clip_info,
                ['recording', 'sensor', 'detector', 'start_time', 'length'],
                f'clip data')

            recording_name = clip_info['recording']
            recording_info = \
                self._get_recording_info(recording_infos, recording_name)

            sensor_name = clip_info['sensor']
            station_name = self._get_station_name(sensor_name)
            station, mic_output = \
                self._get_station_mic_output_pair(station_name)

            start_time = clip_info['start_time']
            start_time = _parse_datetime(start_time, 'clip start')

            serial_num = clip_info.get('serial_num', 0)

            # Offset start time if needed to ensure uniqueness. Vesper
            # currently requires that each clip's recording channel,
            # creating processor, and start time be unique. We use clip
            # serial numbers in the LRGV project to distinguish between
            # clips that have the same start time, and we convert those
            # to start time offsets here. At some point I hope to remove
            # Vesper's uniqueness requirement, at which point we can
            # eliminate the serial numbers and offsets.
            if serial_num != 0:
                offset = TimeDelta(microseconds=serial_num)
                start_time += offset

            detector_name = clip_info['detector']
            detector_model = self._get_detector(detector_name)

            length = clip_info['length']
            (recording_channel, sample_rate, recording_start_time, end_time,
            recording_id, recording_created) = \
                self._get_recording_channel(
                    station, mic_output, start_time, length, recording_info,
                    detector_name)

            # We set the start indices of Old Bird detector clips to `None`
            # since we do not know them exactly (we know only the clips'
            # start times to the nearest second). We will attempt to find
            # the start indices later by locating the clips' samples in
            # their recordings.
            if detector_name.startswith('Old Bird'):
                start_index = None
            else:
                td = start_time - recording_start_time
                start_index = int(round(td.total_seconds() * sample_rate))

            date = station.get_night(start_time)

            creation_time = time_utils.get_utc_now()

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
                creating_processor=detector_model
            )

            annotations = clip_info.get('annotations', {})

            # If clip start time was offset, include an annotation indicating
            # by how many seconds. This will make it possible to remove the
            # offset later if needed.
            if serial_num != 0:
                offset = serial_num / 1000000
                annotations[_START_TIME_UNIQUENESS_OFFSET_ANNOTATION_NAME] = \
                    f'{offset:f}'

            for name, value in annotations.items():
                
                annotation_info = \
                    self._get_annotation_info(name, detector_model)
                
                model_utils.annotate_clip(
                    clip, annotation_info, str(value),
                    creation_time=creation_time,
                    creating_user=None,
                    creating_job=None,
                    creating_processor=detector_model)
                
        except Exception as e:
            raise _ViewError(
                f'Could not create clip from clip data {clip_info}. '
                f'Error message was: {e}')
                
        return clip.id, recording_id, recording_created


    def _get_recording_info(self, recording_infos, recording_name):
        try:
            return recording_infos[recording_name]
        except KeyError:
            raise _ViewError(
                f'Unrecognized recording "{recording_name}".')
        

    def _get_station_name(self, sensor_name):

        # TODO: Involve `recording_sensors` in getting station name.
        # First get recording info from the clip info, then get a
        # sensor list from the recording info, and then get the station
        # from one of the sensors.

        # For now, we extract the station name from the sensor name,
        # assuming that the station name is the part of the sensor
        # name from the beginning to the last space. This will change
        # when we replace devices with sensors.
        station_name = sensor_name.rsplit(sep=' ', maxsplit=1)[0]

        return station_name


    def _get_station_mic_output_pair(self, station_name):
        try:
            return self._station_mic_output_pairs[station_name]
        except KeyError:
            raise _ViewError(
                f'Could not get station/mic output pair for station '
                f'"{station_name}".')


    def _get_detector(self, detector_name):
        try:
            return self._detectors[detector_name]
        except KeyError:
            raise _ViewError(f'Unrecognized detector "{detector_name}".')


    def _get_recording_channel(
            self, station, mic_output, clip_start_time, clip_length,
            recording_info, detector_name):
        
        def format_dt(dt):
            return dt.strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # We use a placeholder clip end time to try to locate the
        # clip's recording. We don't know the real clip end time yet
        # because while we have the clip's length we don't have its
        # sample rate.
        placeholder_end_time = clip_start_time + _ONE_MICROSECOND
        clip_interval = (clip_start_time, placeholder_end_time)

        # Get recordings for the specified station and mic output whose
        # time intervals intersect clip time interval.
        recordings = \
            model_utils.get_recordings(station, mic_output, clip_interval)
        
        recording_count = len(recordings)

        if recording_count == 0:
            # found no recordings

            if recording_info is None:
                raise ValueError(
                    f'Could not find existing recording for station '
                    f'"{station.name}" for clip with start time '
                    f'{clip_start_time}, and no recording data was'
                    f'provided from which to create one.')

            recording = \
                self._create_recording(station, mic_output, recording_info)
            
            recording_created = True
        
        else:
            # found at least one recording

            if recording_count > 1:
                raise ValueError(
                    f'Found more than one recording for station '
                    f'"{station.name}" for clip with start time '
                    f'{clip_start_time}.')
            
            else:
                # found exactly one recording
            
                recording = recordings[0]
                recording_created = False

                if recording_info is not None:
                    _check_recording(
                        recording, recording_info, station, detector_name)

        channels = recording.channels.all()
        channel_count = channels.count()

        if channel_count > 1:
            raise ValueError(
                f'Recording for station "{station.name}" that includes '
                f'clip start time {clip_start_time} has '
                f'{recording.num_channels} channels instead of just one.')
        
        # Check that clip does not start before recording.
        if clip_start_time < recording.start_time:
            raise ValueError(
                f'Clip start time {format_dt(clip_start_time)} '
                f'precedes recording start time '
                f'{format_dt(recording.start_time)}.')
        
        # Get sample rate and real clip end time.
        sample_rate = recording.sample_rate
        clip_end_time = signal_utils.get_end_time(
            clip_start_time, clip_length, sample_rate)

        # Check that clip does not end after recording.
        if clip_end_time > recording.end_time:
            raise ValueError(
                f'Clip end time {format_dt(clip_end_time)} follows '
                f'recording end time {format_dt(recording.end_time)}.')
                
        return (
            channels.first(), sample_rate, recording.start_time,
            clip_end_time, recording.id, recording_created)


    def _create_recording(self, station, mic_output, recording_info):

        start_time = _parse_datetime(
            recording_info['start_time'], 'recording start')
        length = recording_info['length']
        sample_rate = recording_info['sample_rate']

        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
        recorder = self._get_station_recorder(station)
        num_channels = 1
        creation_time = time_utils.get_utc_now()
 
        recording = Recording.objects.create(
            station=station,
            recorder=recorder,
            num_channels=num_channels,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            creation_time=creation_time,
            creating_job=None)
        
        RecordingChannel.objects.create(
            recording=recording,
            channel_num=0,
            recorder_channel_num=0,
            mic_output=mic_output)
        
        return recording


    def _get_station_recorder(self, station):
        try:
            return self._station_recorders[station.name]
        except KeyError:
            raise ValueError(
                f'Could not get recorder for station "{station.name}".')

            
    def _get_annotation_info(self, name, detector_model):
        
        try:
            return self._annotation_info_cache[name]
        
        except KeyError:
            # cache miss
            
            try:
                info = AnnotationInfo.objects.get(name=name)
            
            except AnnotationInfo.DoesNotExist:
                
                detector_name = detector_model.name
                
                logging.info(
                    f'        Adding annotation "{name}" to archive for '
                    f'detector "{detector_name}"...')
                
                description = (
                    f'Created automatically for detector "{detector_name}".')
                
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
            raise _ViewError(
                f'Required {name} item "{key}" is missing.')


# TODO: Log a warning when there's more than one mic output for a station.
def _get_station_mic_output_pairs():
    station_mics = model_utils.get_station_mic_output_pairs_list()
    return {s.name: (s, m) for s, m in station_mics}


def _get_detectors():
    detectors = Processor.objects.filter(type='Detector')
    return {d.name: d for d in detectors}


# TODO: Log a warning if there's more than one recorder for a station.
def _get_station_recorders():
    station_recorders = \
        StationDevice.objects.filter(device__model__type='Audio Recorder')
    return {sr.station.name: sr.device for sr in station_recorders}


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


def _check_recording(recording, recording_info, station, detector_name):

    start_time = _parse_datetime(
        recording_info['start_time'], 'recording start')

    if start_time != recording.start_time:
        raise ValueError(
            f'Specified recording start time {start_time} does not '
            f'match start time {recording.start_time} of recording '
            f'already in archive.')
    
    sample_rate = recording_info['sample_rate']

    if sample_rate != recording.sample_rate:
        raise ValueError(
            f'Specified sample rate {sample_rate} does not match sample '
            f'rate {recording.sample_rate} of recording already in archive.')

    length = recording_info['length']

    if length != recording.length and detector_name.startswith('Nighthawk'):
        # Recording length in archive differs from recording length
        # indicated with Nighthawk clip. This can happen since the
        # recording length indicated with Old Bird detector clips is
        # just an estimate of the saved recording length (the Old Bird
        # detector runs on a real-time audio stream rather than on a
        # saved recording, but the exact length of a recording saved
        # by the i-Sound audio recorder is not known until after the
        # recording is complete), while the recording length indicated
        # with a Nighthawk clip is precise.

        # Update recording length and end time in archive with precise
        # values.

        logging.info(
            f'Updating length of recording "{recording}" from '
            f'{recording.length} to {length}...')

        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
        
        recording.length = length
        recording.end_time = end_time
        recording.save()
