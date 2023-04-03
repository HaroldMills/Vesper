from datetime import datetime as DateTime, timedelta as TimeDelta
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.views import View

from vesper.django.app.models import (
    Clip, Processor, Recording, RecordingChannel, StationDevice)
import vesper.django.app.model_utils as model_utils
import vesper.django.util.view_utils as view_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


# TODO: Consider moving all Old Bird Django code to this app.


_ONE_MICROSECOND = TimeDelta(microseconds=1)


# Note that `LoginRequiredMixin` must be first in base class list.
class CreateLrgvClipsView(LoginRequiredMixin, View):

    # Assumptions made by this view:
    #     * There is one recorder per station.
    #     * There is one microphone output per station.
    #     * All recordings are single-channel.
    #     * There is one recording per station per night.
    #     * Any clip to be created will be at least one microsecond long.


    def get(self, request):
        return HttpResponse('Ok')
    

    def post(self, request):
       return view_utils.handle_json_post(request, self._post, request.user)
    

    def _post(self, content, creating_user):

        self._station_mic_output_pairs = _get_station_mic_output_pairs()
        self._detectors = _get_detectors()
        self._station_recorders = _get_station_recorders()

        try:
            with transaction.atomic():
                for clip_info in content['clips']:
                    self._create_clip(clip_info)

        except Exception as e:
            error_message = _get_error_message(e, clip_info)
            return HttpResponseBadRequest(reason=error_message)
        
        return HttpResponse('Ok')
        

    def _create_clip(self, clip_info):

        station_name = clip_info['station']
        station, mic_output = self._get_station_mic_output_pair(station_name)

        start_time = clip_info['start_time']
        start_time = _parse_datetime(start_time, station)

        length = clip_info['length']

        detector_name = clip_info['detector']
        creating_processor = self._get_detector(detector_name)

        recording_info = clip_info.get('recording')
        recording_channel, sample_rate, end_time = self._get_recording_channel(
            station, mic_output, start_time, length, recording_info)

        # We set the start index to `None` since we do not know it
        # exactly. We will attempt to correct this later by locating
        # clips precisely in their recordings.
        start_index = None

        date = station.get_night(start_time)

        creation_time = time_utils.get_utc_now()

        Clip.objects.create(
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
            creating_processor=creating_processor
        )


    def _get_station_mic_output_pair(self, station_name):
        try:
            return self._station_mic_output_pairs[station_name]
        except KeyError:
            raise ValueError(
                f'Could not get station/mic output pair for station '
                f'"{station_name}".')


    def _get_detector(self, detector_name):
        try:
            return self._detectors[detector_name]
        except KeyError:
            raise ValueError(
                f'Unrecognized detector "{detector_name}".')


    def _get_recording_channel(
            self, station, mic_output, clip_start_time, clip_length,
            recording_info):
        
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
                    f'{clip_start_time}, and no recording information '
                    f'was provided from which to create one.')

            recording = \
                self._create_recording(station, mic_output, recording_info)
        
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

                if recording_info is not None:
                    _check_recording(recording, recording_info)

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
                f'Clip start time {clip_start_time} precedes '
                f'start time {recording.start_time} of only '
                f'intersecting recording.')
        
        # Get sample rate and real clip end time.
        sample_rate = recording.sample_rate
        clip_end_time = signal_utils.get_end_time(
            clip_start_time, clip_length, sample_rate)

        # Check that clip does not end after recording.
        if clip_end_time > recording.end_time:
            raise ValueError(
                f'Clip end time {clip_end_time} follows '
                f'end time {recording.end_time} of only '
                f'intersecting recording.')
                
        # If we get here, the existing recording has one channel.
        return channels.first(), sample_rate, clip_end_time


    def _create_recording(self, station, mic_output, recording_info):

        start_time = _parse_datetime(recording_info['start_time'], station)
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


def _get_error_message(exception, clip_info):

    station_name = clip_info['station']
    start_time = clip_info['start_time']
    detector_name = clip_info['detector']

    return (
        f'Could not create clip for station "{station_name}", start '
        f'time {start_time}, and detector "{detector_name}". Error '
        f'message was: {exception}. No clips or recordings will be '
        f'created for this request.')


_DATE_TIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S.%f',    # with fractional seconds
    '%Y-%m-%d %H:%M:%S'        # without fractional seconds
)


def _parse_datetime(text, station):

    for format in _DATE_TIME_FORMATS:

        # Try to parse `text` as local date and time.
        try:
            local_dt = DateTime.strptime(text, format)
        except Exception:
            continue

        # If we get here, the parse succeeded.
        return station.local_to_utc(local_dt)
    
    # If we get here, none of the parse attempts succeeded.
    raise ValueError(f'Could not parse date and time "{text}".')


def _check_recording(recording, recording_info):

    start_time = \
        _parse_datetime(recording_info['start_time'], recording.station)

    if start_time != recording.start_time:
        raise ValueError(
            f'Specified recording start time {start_time} does not match '
            f'start time {recording.start_time} of recording already in '
            f'archive.')
    
    length = recording_info['length']

    if length != recording.length:
        raise ValueError(
            f'Specified recording length {length} does not match length '
            f'{recording.length} of recording already in archive.')
        
    sample_rate = recording_info['sample_rate']

    if sample_rate != recording.sample_rate:
        raise ValueError(
            f'Specified sample rate {sample_rate} does not match sample '
            f'rate {recording.sample_rate} of recording already in archive.')
