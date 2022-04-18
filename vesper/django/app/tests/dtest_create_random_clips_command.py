from datetime import (
    date as Date, datetime as DateTime, time as Time, timedelta as TimeDelta)
from vesper.command.create_random_clips_command import ScheduleCache
from vesper.django.app.models import (
    DeviceOutput, Recording, RecordingChannel, Station, StationDevice)
from vesper.django.app.tests.dtest_case import TestCase
from vesper.util.date_range import DateRange
import vesper.command.create_random_clips_command as \
    create_random_clips_command
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils


_RECORDINGS = yaml_utils.load('''

recordings:

    - station: Station 0
      start_time: 2050-05-01 20:00:00
      end_time: 2050-05-02 05:00:00
      sample_rate: 24000

    - station: Station 0
      start_time: 2050-05-02 20:00:00
      end_time: 2050-05-03 05:00:00
      sample_rate: 24000

    - station: Station 0
      start_time: 2050-05-03 20:00:00
      end_time: 2050-05-04 05:00:00
      sample_rate: 24000

    - station: Station 1
      start_time: 2050-05-01 20:00:00
      end_time: 2050-05-02 05:00:00
      sample_rate: 24000

    - station: Station 1
      start_time: 2050-05-02 20:00:00
      end_time: 2050-05-03 05:00:00
      sample_rate: 24000

    - station: Station 1
      start_time: 2050-05-03 20:00:00
      end_time: 2050-05-04 05:00:00
      sample_rate: 24000

''')


_RECORDING_START_TIME = Time(20)
_RECORDING_END_TIME = Time(5)

_SCHEDULE_SPEC = yaml_utils.load('''

daily:
    start_date: 2050-05-01
    end_date: 2050-05-03
    start_time: 10 pm
    end_time: 12 am

''')

_ONE_DAY = TimeDelta(days=1)



class CreateRandomClipsCommandTests(TestCase):
    
    
    def setUp(self):
        self._create_shared_test_models()
        self._stations = dict((s.name, s) for s in Station.objects.all())
        self._sm_pairs = _get_sm_pairs()
        self._create_recordings()
        self._schedule_cache = ScheduleCache(_SCHEDULE_SPEC)


    def _create_recordings(self):

        creation_time = time_utils.get_utc_now()

        for r in _RECORDINGS['recordings']:

            station = self._stations[r['station']]

            recorder = _get_station_recorder(station)

            mics = _get_station_mics(station)
            channel_count = len(mics)

            start_time = station.local_to_utc(r['start_time'])

            end_time = station.local_to_utc(r['end_time'])

            sample_rate = r['sample_rate']

            length = _get_recording_length(start_time, end_time, sample_rate)

            recording = Recording.objects.create(
                station=station,
                recorder=recorder,
                num_channels=channel_count,
                length=length,
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time,
                creation_time=creation_time)

            for channel_num, mic in enumerate(mics):

                mic_output = _get_mic_output(mic)

                # Here we assume the identity mapping between recording
                # channel numbers and recorder channel numbers.
                RecordingChannel.objects.create(
                    recording=recording,
                    channel_num=channel_num,
                    recorder_channel_num=channel_num,
                    mic_output=mic_output)


    def test_get_processing_intervals(self):

        # TODO: When we implement sensors, add test case for which
        # one sensor is associated with different recording channels
        # on different dates.

        cases = (
            (('Station 0 21c 0',), 1, 1),
            (('Station 0 21c 0',), 1, 3),
            (('Station 1 21c 1', 'Station 1 21c 2'), 2, 2),
            (('Station 0 21c 0', 'Station 1 21c 2'), 2, 3),
        )

        for sm_pairs, start_day, end_day in cases:

            sm_pairs = [self._sm_pairs[p] for p in sm_pairs]
            start_date = _day_to_date(start_day)
            end_date = _day_to_date(end_day)

            for schedule_cache in (None, self._schedule_cache):

                expected_intervals = _get_expected_intervals(
                    sm_pairs, start_date, end_date, schedule_cache)

                actual_intervals = \
                    create_random_clips_command._get_processing_intervals(
                        sm_pairs, start_date, end_date, schedule_cache)

                actual_intervals = [
                    _diddle_actual_interval(i) for i in actual_intervals]

                # _show_intervals(actual_intervals, 'actual')
                # _show_intervals(expected_intervals, 'expected')

                self.assertEqual(
                    len(actual_intervals), len(expected_intervals))

                for actual, expected in \
                        zip(actual_intervals, expected_intervals):
                    self.assertEqual(actual, expected)


    def test_get_concatenated_time_bounds_aux(self):

        cases = (

            # no intervals
            (([], 10), ([], [0])),

            # one interval
            (([('01:00:00', 24000, '02:00:00', '02:01:00')], 10),
             ([0], [0, 50])),

            # two intervals
            (([('01:00:00', 24000, '02:00:00', '02:01:00'),
               ('01:00:00', 32000, '03:00:00', '03:00:50')], 10),
             ([0, 1], [0, 50, 90])),

            # three intervals, but middle one too short
            (([('01:00:00', 24000, '02:00:00', '02:01:00'),
               ('01:00:00', 32000, '03:00:00', '03:00:05'),
               ('10:00:00', 24000, '11:00:00', '11:00:50')], 10),
             ([0, 2], [0, 50, 90])),

        )

        for (intervals, clip_duration), expected in cases:

            intervals = [_parse_interval(i) for i in intervals]

            actual = \
                create_random_clips_command._get_concatenated_time_bounds_aux(
                    intervals, clip_duration)
            
            # Convert returned NumPy array of time bounds to list for
            # comparison to expected values.
            actual = (actual[0], actual[1].tolist())

            self.assertEqual(actual, expected)


def _get_sm_pairs():

    sm_pairs = {}

    for station in Station.objects.all():

        sds = StationDevice.objects.filter(
            station=station, device__model__type='Microphone')
        mics = [sd.device for sd in sds]
        mics.sort(key=lambda mic: mic.name)

        for mic in mics:
            key = f'{station.name} {mic.name}'
            mic_output = _get_mic_output(mic)
            sm_pairs[key] = (station, mic_output)

    return sm_pairs


def _get_mic_output(mic):

    # Here we assume that each mic has exactly one output.
    return DeviceOutput.objects.get(device=mic)


def _get_station_recorder(station):

    # Here we assume that each station has exactly one recorder.
    sd = StationDevice.objects.get(
        station=station, device__model__type='Audio Recorder')

    return sd.device


def _get_station_mics(station):
    sds = StationDevice.objects.filter(
        station=station, device__model__type='Microphone')
    mics = [sd.device for sd in sds]
    mics.sort(key=lambda mic: mic.name)
    return mics


def _get_recording_length(start_time, end_time, sample_rate):
    duration = (end_time - start_time).total_seconds()
    return signal_utils.seconds_to_frames(duration, sample_rate)


def _day_to_date(day):
    return Date(2050, 5, day)


def _get_expected_intervals(sm_pairs, start_date, end_date, schedule_cache):

    intervals = []

    for station, mic_output in sm_pairs:

        for date in DateRange(start_date, end_date + _ONE_DAY):

            start_time = _get_recording_start_time(station, date)
            end_time = _get_recording_end_time(station, date)

            if schedule_cache is None:
                intervals.append((station, mic_output, start_time, end_time))

            else:
                
                schedule = schedule_cache.get_schedule(station)

                # Get intersection of recording interval and schedule.
                intersection_intervals = \
                    schedule.get_intervals(start_time, end_time)

                for i in intersection_intervals:

                    if i.start > start_time:
                        start_time = i.start

                    if i.end < end_time:
                        end_time = i.end

                    intervals.append(
                        (station, mic_output, start_time, end_time))

    return intervals


def _get_recording_start_time(station, date):
    start_time = DateTime.combine(date, _RECORDING_START_TIME)
    return station.local_to_utc(start_time)


def _get_recording_end_time(station, date):
    date = date + TimeDelta(days=1)
    end_time = DateTime.combine(date, _RECORDING_END_TIME)
    return station.local_to_utc(end_time)
                

def _diddle_actual_interval(interval):
    station, channel, start_time, end_time = interval
    return station, channel.mic_output, start_time, end_time


def _show_intervals(intervals, name):
    print(f'{name} intervals')
    for interval in intervals:
        print(interval)


def _parse_interval(i):
    t = _parse_time
    return t(i[0]), i[1], t(i[2]), t(i[3])


def _parse_time(s):
    hour, minute, second = s.split(':')
    hour = int(hour)
    minute = int(minute)
    second = int(second)
    return time_utils.create_utc_datetime(2050, 5, 1, hour, minute, second)
