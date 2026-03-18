import json

from vesper.django.app.models import AnnotationInfo, Clip, Recording
from vesper.django.app.tests.dtest_case import TestCase


_URL = '/import-recordings-and-clips/'

_SAMPLE_RATE = 22050
_RECORDING_DURATION = 10
_RECORDING_LENGTH = int(round(_RECORDING_DURATION * 3600 * _SAMPLE_RATE))

_RECORDING_1 =  {
    'station': 'Station 1',
    'recorder': 'Swift',
    'mic_outputs': ['21c 1 Output'],
    'start_time': '2050-05-01 23:00:00 Z',
    'length': _RECORDING_LENGTH,
    'sample_rate': _SAMPLE_RATE
}

_RECORDING_2 =  {
    'station': 'Station 2',
    'recorder': 'PC',
    'mic_outputs': ['21c 2 Output', '21c 3 Output'],
    'start_time': '2050-05-02 23:00:00 Z',
    'length': _RECORDING_LENGTH,
    'sample_rate': _SAMPLE_RATE
}

_CLIP_1 = {
    'station': 'Station 1',
    'mic_output': '21c 1 Output',
    'detector': 'Old Bird Tseep Detector Redux 1.1',
    'start_time': '2050-05-01 23:00:02.000 Z',
    'length': 11025,
    'annotations': {
        'Classification': 'Tseep'
    }
}

_CLIP_2 = {
    'station': 'Station 1',
    'mic_output': '21c 1 Output',
    'detector': 'Old Bird Tseep Detector Redux 1.1',
    'start_time': '2050-05-01 23:00:04.000 Z',
    'length': 11025,
    'annotations': {
        'Classification': 'Thrush',
        'Bobo': 'Bobo',   # nonexistent annotation should be added to archive
    }
}

_RECORDING_START_TIME_FORMAT = '%Y-%m-%d %H:%M:%S Z'
_CLIP_START_TIME_FORMAT = '%Y-%m-%d %H:%M:%S.%f'


class ImportRecordingsAndClipsViewTests(TestCase):


    def setUp(self):
        self.maxDiff = None    # show entire string differences
        self._create_test_user()
        self._create_shared_test_models()


    def test_one_recording(self):

        self._test_post(
            [
                ({
                    'recordings': [_RECORDING_1],
                    'clips': []
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': []
                })
            ], {
                'recordings': [(1, _RECORDING_1)],
                'clips': []
            })


    def _test_post(self, requests, expected_db):
        self._log_in_as_test_user()
        self._do_post_requests(requests)
        self._check_db_recordings(expected_db['recordings'])
        self._check_db_clips(expected_db['clips'])


    def _do_post_requests(self, requests):
        for request_data, expected_response_data in requests:
            response = self.client.post(_URL, request_data, 'application/json')
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertEqual(response_data, expected_response_data)


    def _check_db_recordings(self, expected_recordings):

        # Check database recording count.
        self.assertEqual(Recording.objects.count(), len(expected_recordings))

        # Check database recording data.
        for id, r in expected_recordings:

            recording = Recording.objects.get(id=id)

            # Check station and recorder names.
            self.assertEqual(recording.station.name, r['station'])
            self.assertEqual(recording.recorder.name, r['recorder'])

            # Check channel mic output names.
            channels = recording.channels.all().order_by('channel_num')
            mic_outputs = [c.mic_output.name for c in channels]
            self.assertEqual(mic_outputs, r['mic_outputs'])

            # Check start time.
            start_time = self._format_recording_start_time(recording)
            self.assertEqual(start_time, r['start_time'])

            # Check length and sample rate.
            self.assertEqual(recording.length, r['length'])
            self.assertEqual(recording.sample_rate, r['sample_rate'])


    def _check_db_clips(self, expected_clips):

        # Check database clip count.
        self.assertEqual(Clip.objects.count(), len(expected_clips))

        # Check database clip data.
        for id, c in expected_clips:

            clip = Clip.objects.get(id=id)

            # Check station, mic output, and detector names.
            self.assertEqual(clip.station.name, c['station'])
            self.assertEqual(clip.mic_output.name, c['mic_output'])
            self.assertEqual(clip.creating_processor.name, c['detector'])

            # Check start time.
            start_time = self._format_clip_start_time(clip)
            self.assertEqual(start_time, c['start_time'])

            # Check length.
            self.assertEqual(clip.length, c['length'])

            # Check annotations.
            for name, value in c['annotations'].items():
                info = AnnotationInfo.objects.get(name=name)
                annotation = clip.string_annotations.get(info=info)
                self.assertEqual(annotation.value, value)


    def _format_recording_start_time(self, recording):
         return recording.start_time.strftime(_RECORDING_START_TIME_FORMAT)
    

    def _format_clip_start_time(self, clip):
        start_time = clip.start_time.strftime(_CLIP_START_TIME_FORMAT)
        return start_time[:-3] + ' Z'


    def test_one_recording_with_duplicate(self):

        self._test_post(
        
            [

                # recording
                ({
                    'recordings': [_RECORDING_1],
                    'clips': []
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': []
                }),

                # duplicate recording
                ({
                    'recordings': [_RECORDING_1],
                    'clips': []
                }, {
                    'recordings': [{'id': 1, 'created': False}],
                    'clips': []
                })

            ], {
                'recordings': [(1, _RECORDING_1)],
                'clips': []
            })


    def test_two_recordings_in_one_request(self):

        self._test_post(
            [
                ({
                    'recordings': [_RECORDING_1, _RECORDING_2],
                    'clips': []
                }, {
                    'recordings': [{'id': 1, 'created': True},
                                {'id': 2, 'created': True}],
                    'clips': []
                })
            ], {
                'recordings': [(1, _RECORDING_1), (2, _RECORDING_2)],
                'clips': []
            })


    def test_two_recordings_in_two_requests(self):

        self._test_post(
            
            [

                # recording 1
                ({
                    'recordings': [_RECORDING_1],
                    'clips': []
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': []
                }),

                # recording 2
                ({
                    'recordings': [_RECORDING_2],
                    'clips': []
                }, {
                    'recordings': [{'id': 2, 'created': True}],
                    'clips': []
                })
                
            ], {
                'recordings': [(1, _RECORDING_1), (2, _RECORDING_2)],
                'clips': []
            })


    def test_one_clip(self):

        self._test_post(
            [
                ({
                    'recordings': [_RECORDING_1],
                    'clips': [_CLIP_1]
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': [{'id': 1, 'created': True}]
                })
            ], {
                'recordings': [(1, _RECORDING_1)],
                'clips': [(1, _CLIP_1)]
            })


    def test_one_clip_with_duplicate(self):

        self._test_post(
            [
                ({
                    'recordings': [_RECORDING_1],
                    'clips': [_CLIP_1, _CLIP_1]
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': [
                        {'id': 1, 'created': True},
                        {'id': 1, 'created': False}
                    ]
                })
            ], {
                'recordings': [(1, _RECORDING_1)],
                'clips': [(1, _CLIP_1)]
            })


    def test_two_clips_in_one_request(self):

        self._test_post(
            [
                ({
                    'recordings': [_RECORDING_1],
                    'clips': [_CLIP_1, _CLIP_2]
                }, {
                    'recordings': [{'id': 1, 'created': True}],
                    'clips': [
                        {'id': 1, 'created': True},
                        {'id': 2, 'created': True}
                    ]
                })
            ], {
                'recordings': [(1, _RECORDING_1)],
                'clips': [(1, _CLIP_1), (2, _CLIP_2)]
            })
       

    def test_missing_recording_item_error(self):

        for item_name in (
                'station', 'recorder', 'mic_outputs', 'start_time', 'length',
                'sample_rate'):

            # Start with recording info that includes all required items.
            recording_info = _RECORDING_1.copy()

            # Delete one required recording item.
            del recording_info[item_name]
            
            request_data = {'recordings': [recording_info]}

            expected_error_message = \
                f'Required recording data item "{item_name}" is missing.'
            
            self._test_recording_info_error(
                request_data, expected_error_message)


    def _test_recording_info_error(
            self, request_data, expected_error_message):
        
        recording_info = request_data['recordings'][0]

        expected_error_message = (
            f'Could not create recording from recording data '
            f'{recording_info}. Error message was: {expected_error_message} '
            f'No recordings or clips will be created for this request.')
            
        self._test_error(request_data, expected_error_message)


    def _test_error(self, request_data, expected_error_message):
        self._log_in_as_test_user()
        response = self.client.post(_URL, request_data, 'application/json')
        self.assertEqual(response.status_code, 400)
        error_message = response.content.decode(response.charset)
        self.assertEqual(error_message, expected_error_message)
        

    def test_bad_clip_start_time_error(self):

        expected_error_message = 'Could not parse recording start time "Bobo".'

        self._test_bad_recording_item_value_error(
            'start_time', 'Bobo', expected_error_message)
        

    def _test_bad_recording_item_value_error(
            self, item_name, bad_item_value, expected_error_message):
        
        # Start with good recording info.
        recording_info = _RECORDING_1.copy()

        # Make one item value bad.
        recording_info[item_name] = bad_item_value

        request_data = {'recordings': [recording_info]}

        self._test_recording_info_error(
            request_data, expected_error_message)
        
        
    def test_missing_clip_item_error(self):

        for item_name in (
                'station', 'mic_output', 'detector', 'start_time', 'length'):

            # Start with clip info that includes all required items.
            clip_info = _CLIP_1.copy()

            # Delete one required clip item.
            del clip_info[item_name]

            request_data = {
                'recordings': [_RECORDING_1],
                'clips': [clip_info]
            }

            expected_error_message = (
                f'Required clip data item "{item_name}" is missing.')
            
            self._test_clip_creation_error(
                request_data, clip_info, expected_error_message)
            

    def _test_clip_creation_error(
            self, request_data, clip_info, expected_error_message):
        
        expected_error_message = (
            f'Could not create clip from clip data {clip_info}. '
            f'Error message was: {expected_error_message} '
            f'No recordings or clips will be created for this request.')
            
        self._test_error(request_data, expected_error_message)


    def test_unrecognized_station_error(self):

        expected_error_message = 'Unknown station "Bobo".'
        
        self._test_bad_clip_item_value_error(
            'station', 'Bobo', expected_error_message)


    def _test_bad_clip_item_value_error(
            self, item_name, bad_item_value, expected_error_message):
        
        # Start with good clip info.
        clip_info = _CLIP_1.copy()

        # Make one item value bad.
        clip_info[item_name] = bad_item_value

        request_data = {
            'recordings': [_RECORDING_1],
            'clips': [clip_info]
        }

        self._test_clip_creation_error(
            request_data, clip_info, expected_error_message)


    def test_unrecognized_mic_output_error(self):

        expected_error_message = 'Unknown device output "Bobo".'
        
        self._test_bad_clip_item_value_error(
            'mic_output', 'Bobo', expected_error_message)


    def test_unrecognized_detector_error(self):

        expected_error_message = 'Unknown detector "Bobo".'

        self._test_bad_clip_item_value_error(
            'detector', 'Bobo', expected_error_message)


    def test_bad_clip_start_time_error(self):

        expected_error_message = 'Could not parse clip start time "Bobo".'

        self._test_bad_clip_item_value_error(
            'start_time', 'Bobo', expected_error_message)
        
        
    def test_no_recording_for_clip_error(self):

        # Get clip info with start time that precedes recording start time.
        clip_info = _CLIP_1.copy()
        clip_info['start_time'] = '2050-05-01 22:00:00 Z'

        request_data = {
            'recordings': [_RECORDING_1],
            'clips': [clip_info]
        }

        expected_error_message = (
            f'Could not find recording for station "Station 1", '
            f'mic output "21c 1 Output", and clip start time '
            f'2050-05-01 22:00:00+00:00.')
        
        self._test_clip_creation_error(
            request_data, clip_info, expected_error_message)


    def test_multiple_recordings_for_clip_error(self):

        # Get info for recording that overlaps recording 1.
        recording_info = _RECORDING_1.copy()
        recording_info['start_time'] = '2050-05-01 21:00:00 Z'

        request_data = {
            'recordings': [recording_info, _RECORDING_1],
            'clips': [_CLIP_1]
        }

        expected_error_message = (
            'Found more than one recording for station "Station 1", mic '
            'output "21c 1 Output", and clip start time '
            '2050-05-01 23:00:02+00:00.')
        
        self._test_clip_creation_error(
            request_data, _CLIP_1, expected_error_message)


    def test_clip_ends_after_recording_error(self):

        # Get info for clip that ends after recording.
        clip_info = _CLIP_1.copy()
        clip_info['length'] = _RECORDING_LENGTH

        request_data = {
            'recordings': [_RECORDING_1],
            'clips': [clip_info]
        }

        expected_error_message = (
            'Clip end time 2050-05-02 09:00:01.999955 follows recording '
            'end time 2050-05-02 08:59:59.999955.')
        
        self._test_clip_creation_error(
            request_data, clip_info, expected_error_message)
