import json

from vesper.django.app.tests.dtest_case import TestCase


# TODO: The tests in this file check responses to POST requests, but they
# don't check the database state after the requests. Add such checks.


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


# _POST_TEST_CASES = (
    
#     # One recording.
#     (
#         {
#             'recordings': [
#                 {
#                     'station': 'Station 0',
#                     'recorder': 'Swift',
#                     'mic_outputs': ['21c 0 Output'],
#                     'start_time': '2050-03-27 23:00:00 Z',
#                     'length': _RECORDING_LENGTH,
#                     'sample_rate': _SAMPLE_RATE
#                 }
#             ]
#             # 'clips': [
#             #     {
#             #         'recording': 'Station 0 2050-03-27 23:00:00 Z',
#             #         'sensor': 'Station 0 21c',
#             #         'detector': 'Old Bird Tseep Detector Redux 1.1',
#             #         'start_time': '2050-03-28 00:00:00.000 Z',
#             #         'length': 11025,
#             #     },
#             #     {
#             #         'recording': 'Station 0 2050-03-27 23:00:00 Z',
#             #         'sensor': 'Station 0 21c',
#             #         'detector': 'Old Bird Tseep Detector Redux 1.1',
#             #         'start_time': '2050-03-28 01:00:00.000 Z',
#             #         'length': 22050,
#             #     },
#             # ]
#         },
#         {
#             'recordings': [{'id': 1, 'created': True}],
#             'clips': []
#         }
#     ),

#     # One recording and
#     (
#         {
#             'recordings': [
#                 {
#                     'station': 'Station 0',
#                     'recorder': 'Swift',
#                     'mic_outputs': ['21c 0 Output'],
#                     'start_time': '2050-03-27 23:00:00 Z',
#                     'length': _RECORDING_LENGTH,
#                     'sample_rate': _SAMPLE_RATE
#                 },
#             ]
#         },
#         {
#             'recordings': [{'id': 1, 'created': False}],
#             'clips': []
#         }
#     ),

    # (
    #     {
    #         'recordings': {
    #             'Station 0 2050-03-27 23:00:00 Z': {
    #                 # 'sensors': 'Station 0',
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #             'Station 1 2050-03-28 23:00:00 Z': {
    #                 # 'sensors': 'Station 1',
    #                 'start_time': '2050-03-28 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             }
    #         },
    #         # 'recording_sensors': {
    #         #     'Station 0': [
    #         #         'Station 0 21c'
    #         #     ],
    #         #     'Station 1': [
    #         #         'Station 0 21c'
    #         #     ]
    #         # },
    #         'clips': [
    #             {
    #                 'recording': 'Station 1 2050-03-28 23:00:00 Z',
    #                 'sensor': 'Station 1 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-29 00:00:00.000 Z',
    #                 'length': 11025,
    #             },
    #             {
    #                 'recording': 'Station 1 2050-03-28 23:00:00 Z',
    #                 'sensor': 'Station 1 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-29 01:00:00.000 Z',
    #                 'length': 22050,
    #             },
    #             {
    #                 'recording': 'Station 0 2050-03-27 23:00:00 Z',
    #                 'sensor': 'Station 0 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-28 02:00:00.000 Z',
    #                 'length': 22050,
    #             },
    #         ]
    #     },
    #     {
    #         'clips': [
    #             {'clip_id': 3, 'recording_id': 2, 'recording_created': True},
    #             {'clip_id': 4, 'recording_id': 2, 'recording_created': False},
    #             {'clip_id': 5, 'recording_id': 1, 'recording_created': False}
    #         ]
    #     }
    # ),

# )

class ImportRecordingsAndClipsViewTests(TestCase):


    def setUp(self):
        self.maxDiff = None    # show entire string differences
        self._create_test_user()
        self._create_shared_test_models()


    def test_one_recording(self):

        self._test_post([
            ({
                'recordings': [_RECORDING_1],
                'clips': []
            }, {
                'recordings': [{'id': 1, 'created': True}],
                'clips': []
            })
        ])


    def _test_post(self, test_data):
        self._log_in_as_test_user()
        for request_data, expected_response_data in test_data:
            response = self.client.post(_URL, request_data, 'application/json')
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertEqual(response_data, expected_response_data)


    def test_one_recording_with_duplicate(self):

        self._test_post([

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

        ])


    def test_two_recordings_in_one_request(self):

        self._test_post([
            ({
                'recordings': [_RECORDING_1, _RECORDING_2],
                'clips': []
            }, {
                'recordings': [{'id': 1, 'created': True},
                               {'id': 2, 'created': True}],
                'clips': []
            })
        ])


    def test_two_recordings_in_two_requests(self):

        self._test_post([

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
            
        ])


    def test_one_clip(self):

        self._test_post([
            ({
                'recordings': [_RECORDING_1],
                'clips': [_CLIP_1]
            }, {
                'recordings': [{'id': 1, 'created': True}],
                'clips': [{'id': 1, 'created': True}]
            })
        ])


    def test_one_clip_with_duplicate(self):

        self._test_post([
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
        ])


    def test_two_clips_in_one_request(self):

        self._test_post([
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
        ])
       

    # def test_missing_recording_item_error(self):

    #     recording_name = 'Station 0 2050-03-27 23:00:00 Z'

    #     for item_name in ('start_time', 'length', 'sample_rate'):

    #         # Start with request data that includes all required items.
    #         request_data = {
    #             'recordings': {
    #                 recording_name: {
    #                     'start_time': '2050-03-27 23:00:00 Z',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 },
    #             }
    #         }

    #         recording_info = request_data['recordings'][recording_name]

    #         # Delete one required recording item.
    #         del recording_info[item_name]

    #         expected_error_message = \
    #             f'Required recording data item "{item_name}" is missing.'
            
    #         self._test_recording_info_error(
    #             request_data, recording_name, expected_error_message)


    # def _test_recording_info_error(
    #         self, request_data, recording_name, expected_error_message):
        
    #     recording_info = request_data['recordings'][recording_name]

    #     expected_error_message = (
    #         f'Could not parse recording "{recording_name}" data '
    #         f'{recording_info}. Error message was: {expected_error_message} '
    #         f'No recordings or clips will be created for this request.')
            
    #     self._test_error(request_data, expected_error_message)


    # def _test_error(self, request_data, expected_error_message):
    #     self._log_in_as_test_user()
    #     response = self.client.post(_URL, request_data, 'application/json')
    #     self.assertEqual(response.status_code, 400)
    #     error_message = response.content.decode(response.charset)
    #     self.assertEqual(error_message, expected_error_message)
        

    # def _test_bad_recording_item_value_error(
    #         self, item_name, bad_item_value, expected_error_message):
        
    #     recording_name = 'Station 0 2050-03-27 23:00:00 Z'

    #     # Start with good request data.
    #     request_data = {
    #         'recordings': {
    #             recording_name: {
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #         },
    #     }

    #     recording_info = request_data['recordings'][recording_name]

    #     # Make one item value bad.
    #     recording_info[item_name] = bad_item_value

    #     self._test_recording_info_error(
    #         request_data, recording_name, expected_error_message)
        
        
    # def test_bad_clip_start_time_error(self):

    #     expected_error_message = 'Could not parse recording start time "Bobo".'

    #     self._test_bad_recording_item_value_error(
    #         'start_time', 'Bobo', expected_error_message)
        

    # def test_missing_clip_item_error(self):

    #     for item_name in (
    #             'recording', 'sensor', 'detector', 'start_time', 'length'):

    #         # Start with request data that includes all required items.
    #         request_data = {
    #             'recordings': {
    #                 'Station 0 2050-03-27 23:00:00 Z': {
    #                     'start_time': '2050-03-27 23:00:00 Z',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 },
    #             },
    #             'clips': [
    #                 {
    #                     'recording': 'Station 0 2050-03-27 23:00:00 Z',
    #                     'sensor': 'Station 0 21c',
    #                     'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                     'start_time': '2050-03-28 02:00:00.000 Z',
    #                     'length': 22050,
    #                 },
    #             ]
    #         }

    #         clip_info = request_data['clips'][0]

    #         # Delete one required recording item.
    #         del clip_info[item_name]

    #         expected_error_message = (
    #             f'Required clip data item "{item_name}" is missing.')
            
    #         self._test_clip_creation_error(
    #             request_data, clip_info, expected_error_message)
            

    # def _test_bad_clip_item_value_error(
    #         self, item_name, bad_item_value, expected_error_message):
        
    #     # Start with good request data.
    #     request_data = {
    #         'recordings': {
    #             'Station 0 2050-03-27 23:00:00 Z': {
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #         },
    #         'clips': [
    #             {
    #                 'recording': 'Station 0 2050-03-27 23:00:00 Z',
    #                 'sensor': 'Station 0 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-28 02:00:00.000 Z',
    #                 'length': 22050,
    #             }
    #         ]
    #     }

    #     clip_info = request_data['clips'][0]

    #     # Make one item value bad.
    #     clip_info[item_name] = bad_item_value

    #     self._test_clip_creation_error(
    #         request_data, clip_info, expected_error_message)


    # def _test_clip_creation_error(
    #         self, request_data, clip_info, expected_error_message):
        
    #     expected_error_message = (
    #         f'Could not create clip from clip data {clip_info}. '
    #         f'Error message was: {expected_error_message} '
    #         f'No recordings or clips will be created for this request.')
            
    #     self._test_error(request_data, expected_error_message)


    # def test_nonexistent_station_error(self):

    #     expected_error_message = \
    #         'Could not get station/mic output pair for station "Bobo".'
        
    #     self._test_bad_clip_item_value_error(
    #         'sensor', 'Bobo', expected_error_message)


    # def test_nonexistent_detector_error(self):

    #     expected_error_message = 'Unrecognized detector "Bobo".'

    #     self._test_bad_clip_item_value_error(
    #         'detector', 'Bobo', expected_error_message)


    # def test_bad_clip_start_time_error(self):

    #     expected_error_message = 'Could not parse clip start time "Bobo".'

    #     self._test_bad_clip_item_value_error(
    #         'start_time', 'Bobo', expected_error_message)
        
        
    # def test_preceding_clip_error(self):

    #     # Error condition in which clip start time precedes recording
    #     # start time.

    #     request_data = {
    #         'recordings': {
    #             'Station 0 2050-03-27 23:00:00 Z': {
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #         },
    #         'clips': [
    #             {
    #                 'recording': 'Station 0 2050-03-27 23:00:00 Z',
    #                 'sensor': 'Station 0 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-27 22:00:00.000 Z',
    #                 'length': 22050,
    #             }
    #         ]
    #     }

    #     clip_info = request_data['clips'][0]

    #     expected_error_message = (
    #         f'Clip start time 2050-03-27 22:00:00.000000 precedes '
    #         f'recording start time 2050-03-27 23:00:00.000000.')
        
    #     self._test_clip_creation_error(
    #         request_data, clip_info, expected_error_message)


    # def test_following_clip_error(self):

    #     # Error condition in which clip end time follows recording end time.

    #     request_data = {
    #         'recordings': {
    #             'Station 0 2050-03-27 23:00:00 Z': {
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #         },
    #         'clips': [
    #             {
    #                 'recording': 'Station 0 2050-03-27 23:00:00 Z',
    #                 'sensor': 'Station 0 21c',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-28 23:00:00.000 Z',
    #                 'length': 22050,
    #             }
    #         ]
    #     }

    #     clip_info = request_data['clips'][0]

    #     expected_error_message = (
    #         f'Clip end time 2050-03-28 23:00:00.999955 follows recording '
    #         f'end time 2050-03-28 08:59:59.999955.')
        
    #     self._test_clip_creation_error(
    #         request_data, clip_info, expected_error_message)


    # def test_more_than_one_recording_error(self):

    #     request_data = {
    #         'recordings': {
    #             'Station 0 2050-03-27 23:00:00 Z': {
    #                 'start_time': '2050-03-27 23:00:00 Z',
    #                 'length': _RECORDING_LENGTH,
    #                 'sample_rate': _SAMPLE_RATE
    #             },
    #         },
    #         'clips': [
    #             {
    #                 ''
    #                 'station': 'Station 0',
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'start_time': '2050-03-28 00:00:00.000',
    #                 'length': 11025,
    #            },
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 18:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 18:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             },
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 19:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #             },
    #         ]
    #     }

    #     expected_error_message = (
    #         'Could not create clip for station "Station 0", start time '
    #         '"2050-03-27 19:00:00.000", and detector "Old Bird Tseep '
    #         'Detector Redux 1.1". Error message was: Found more than '
    #         'one recording for station "Station 0" for clip with start '
    #         'time 2050-03-27 19:00:00. No recordings or clips will be '
    #         'created for this request.')
        
    #     self._test_error(request_data, expected_error_message)


    # def test_recording_start_time_mismatch_error(self):

    #     request_data = {
    #         'clips': [
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 20:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 19:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             },
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 21:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 20:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             }
    #         ]
    #     }

    #     expected_error_message = (
    #         'Could not create clip for station "Station 0", start time '
    #         '"2050-03-27 21:00:00.000", and detector "Old Bird Tseep '
    #         'Detector Redux 1.1". Error message was: Specified recording '
    #         'start time 2050-03-27 20:00:00 does not match start time '
    #         '2050-03-27 19:00:00 of recording already in archive. No '
    #         'recordings or clips will be created for this request.')
        
    #     self._test_error(request_data, expected_error_message)


    # def test_recording_length_mismatch_error(self):

    #     request_data = {
    #         'clips': [
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 20:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 19:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             },
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 21:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 19:00:00',
    #                     'length': _RECORDING_LENGTH + 1,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             }
    #         ]
    #     }

    #     expected_error_message = (
    #         'Could not create clip for station "Station 0", start '
    #         'time "2050-03-27 21:00:00.000", and detector "Old Bird '
    #         'Tseep Detector Redux 1.1". Error message was: Specified '
    #         'recording length 793800001 does not match length 793800000 '
    #         'of recording already in archive. No recordings or clips '
    #         'will be created for this request.')
        
    #     self._test_error(request_data, expected_error_message)


    # def test_recording_sample_rate_mismatch_error(self):

    #     request_data = {
    #         'clips': [
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 20:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 19:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE
    #                 }
    #             },
    #             {
    #                 'station': 'Station 0',
    #                 'start_time': '2050-03-27 21:00:00.000',
    #                 'length': 11025,
    #                 'detector': 'Old Bird Tseep Detector Redux 1.1',
    #                 'recording': {
    #                     'start_time': '2050-03-27 19:00:00',
    #                     'length': _RECORDING_LENGTH,
    #                     'sample_rate': _SAMPLE_RATE + 1
    #                 }
    #             }
    #         ]
    #     }

    #     expected_error_message = (
    #         'Could not create clip for station "Station 0", start '
    #         'time "2050-03-27 21:00:00.000", and detector "Old Bird '
    #         'Tseep Detector Redux 1.1". Error message was: Specified '
    #         'sample rate 22051 does not match sample rate 22050.0 '
    #         'of recording already in archive. No recordings or clips '
    #         'will be created for this request.')
        
    #     self._test_error(request_data, expected_error_message)
