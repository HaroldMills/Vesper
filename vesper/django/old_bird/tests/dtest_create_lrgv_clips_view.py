import json

from vesper.django.app.tests.dtest_case import TestCase


_URL = '/create-lrgv-clips/'

_SAMPLE_RATE = 22050
_RECORDING_DURATION = 10
_RECORDING_LENGTH = int(round(_RECORDING_DURATION * 3600 * _SAMPLE_RATE))

_POST_TEST_CASES = (
    
    (
        {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 21:00:00.000',
                    'length': 22050,
                    'detector': 'Old Bird Tseep Detector Redux 1.1'
                },
            ]
        },
        {
            'clips': [
                {'clip_id': 1, 'recording_id': 1, 'recording_created': True},
                {'clip_id': 2, 'recording_id': 1, 'recording_created': False}
            ]
        }
    ),

    (
        {
            'clips': [
                {
                    'station': 'Station 1',
                    'start_time': '2050-03-28 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-28 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 1',
                    'start_time': '2050-03-28 21:00:00.000',
                    'length': 22050,
                    'detector': 'Old Bird Tseep Detector Redux 1.1'
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 22:00:00.000',
                    'length': 22050,
                    'detector': 'Old Bird Tseep Detector Redux 1.1'
                },
            ]
        },
        {
            'clips': [
                {'clip_id': 3, 'recording_id': 2, 'recording_created': True},
                {'clip_id': 4, 'recording_id': 2, 'recording_created': False},
                {'clip_id': 5, 'recording_id': 1, 'recording_created': False}
            ]
        }
    ),

)

class CreateClipsViewSimpleTests(TestCase):


    def setUp(self):
        self.maxDiff = None    # show entire string differences
        self._create_test_user()
        self._create_shared_test_models()


    def test_post(self):
        self._log_in_as_test_user()
        for post_data, expected_response_data in _POST_TEST_CASES:
            response = self.client.post(_URL, post_data, 'application/json')
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertEqual(response_data, expected_response_data)


    def test_nonexistent_recording_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-27 20:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Could not find '
            'existing recording for station "Station 0" for clip with '
            'start time 2050-03-27 20:00:00, and no recording information '
            'was provided from which to create one. No clips or recordings '
            'will be created for this request.')
        
        self._test_error(request_data, expected_error_message)
        

    def _test_error(self, request_data, expected_error_message):
        self._log_in_as_test_user()
        response = self.client.post(_URL, request_data, 'application/json')
        self.assertEqual(response.status_code, 400)
        error_message = response.content.decode(response.charset)
        self.assertEqual(error_message, expected_error_message)


    def test_nonexistent_station_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Bobo',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Bobo", start time '
            '"2050-03-27 20:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Could not get '
            'station/mic output pair for station "Bobo". No clips or '
            'recordings will be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_nonexistent_detector_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Bobo',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-27 20:00:00.000", and detector "Bobo". Error message '
            'was: Unrecognized detector "Bobo". No clips or recordings '
            'will be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_bad_clip_start_time_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': 'bobo',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"bobo", and detector "Old Bird Tseep Detector Redux 1.1". '
            'Error message was: Could not parse clip start time "bobo". '
            'No clips or recordings will be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_preceding_clip_error(self):

        # Error condition in which clip start time precedes recording
        # start time.

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 18:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start '
            'time "2050-03-27 18:00:00.000", and detector "Old Bird '
            'Tseep Detector Redux 1.1". Error message was: Clip start '
            'time 2050-03-27 18:00:00 precedes recording start time '
            '2050-03-27 19:00:00. No clips or recordings will be '
            'created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_following_clip_error(self):

        # Error condition in which clip end time follows recording end time.

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-28 19:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-28 19:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Clip end time '
            '2050-03-28 19:00:00.499955 follows recording end time '
            '2050-03-28 04:59:59.999955. No clips or recordings will '
            'be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_bad_recording_start_time_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': 'bobo',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-27 20:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Could not parse '
            'recording start time "bobo". No clips or recordings will '
            'be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_more_than_one_recording_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 18:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 18:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 19:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                },
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-27 19:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Found more than '
            'one recording for station "Station 0" for clip with start '
            'time 2050-03-27 19:00:00. No clips or recordings will be '
            'created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_recording_start_time_mismatch_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 21:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 20:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start time '
            '"2050-03-27 21:00:00.000", and detector "Old Bird Tseep '
            'Detector Redux 1.1". Error message was: Specified recording '
            'start time 2050-03-27 20:00:00 does not match start time '
            '2050-03-27 19:00:00 of recording already in archive. No '
            'clips or recordings will be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_recording_length_mismatch_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 21:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH + 1,
                        'sample_rate': _SAMPLE_RATE
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start '
            'time "2050-03-27 21:00:00.000", and detector "Old Bird '
            'Tseep Detector Redux 1.1". Error message was: Specified '
            'recording length 793800001 does not match length 793800000 '
            'of recording already in archive. No clips or recordings '
            'will be created for this request.')
        
        self._test_error(request_data, expected_error_message)


    def test_recording_sample_rate_mismatch_error(self):

        request_data = {
            'clips': [
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 20:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE
                    }
                },
                {
                    'station': 'Station 0',
                    'start_time': '2050-03-27 21:00:00.000',
                    'length': 11025,
                    'detector': 'Old Bird Tseep Detector Redux 1.1',
                    'recording': {
                        'start_time': '2050-03-27 19:00:00',
                        'length': _RECORDING_LENGTH,
                        'sample_rate': _SAMPLE_RATE + 1
                    }
                }
            ]
        }

        expected_error_message = (
            'Could not create clip for station "Station 0", start '
            'time "2050-03-27 21:00:00.000", and detector "Old Bird '
            'Tseep Detector Redux 1.1". Error message was: Specified '
            'sample rate 22051 does not match sample rate 22050.0 '
            'of recording already in archive. No clips or recordings '
            'will be created for this request.')
        
        self._test_error(request_data, expected_error_message)
