"""Module containing Django unit test test case superclass."""


from django.contrib.auth.models import User
import django

from vesper.tests.test_case_mixin import TestCaseMixin
import vesper.django.app.metadata_import_utils as metadata_import_utils
import vesper.util.yaml_utils as yaml_utils


_SHARED_TEST_MODEL_DATA = '''

stations:

    - name: Station 0
      description: First test station.
      time_zone: US/Eastern
      latitude: 42.5
      longitude: -76.5
      elevation: 100

    - name: Station 1
      description: Second test station.
      time_zone: US/Eastern
      latitude: 42.5
      longitude: -76.51
      elevation: 100

    - name: Station 2
      description: Third test station.
      time_zone: US/Pacific
      latitude: 38.2
      longitude: -122.9
      elevation: 200

device_models:

    - name: Swift
      type: Audio Recorder
      manufacturer: Center for Conservation Biology, Cornell Lab of Ornithology
      model: Swift
      description: Swift autonomous audio recorder.
      num_inputs: 1

    - name: AudioMoth
      type: Audio Recorder
      manufacturer: Open Acoustic Devices
      model: AudioMoth
      description: AudioMoth autonomous audio recorder.
      num_inputs: 1

    - name: PC
      type: Audio Recorder
      manufacturer: Various
      model: PC
      description: Personal computer as an audio recorder.
      num_inputs: 2

    - name: 21c
      type: Microphone
      manufacturer: Old Bird, Inc.
      model: 21c
      description: Old Bird bucket microphone.
      num_outputs: 1

devices:

    - name: Swift
      model: Swift
      serial_number: "0"
      description: Recorder used at Station 0.

    - name: AudioMoth
      model: AudioMoth
      serial_number: "0"
      description: Recorder used at Station 1.

    - name: PC
      model: PC
      serial_number: "0"
      description: Recorder used at Station 2.

    - name: 21c 0
      model: 21c
      serial_number: "0"
      description: Microphone used at Station 0.

    - name: 21c 1
      model: 21c
      serial_number: "1"
      description: Microphone used at Station 1.

    - name: 21c 2
      model: 21c
      serial_number: "2"
      description: Microphone used at Station 2.

    - name: 21c 3
      model: 21c
      serial_number: "3"
      description: Microphone used at Station 2.

station_devices:

    - station: Station 0
      start_time: 2050-01-01
      end_time: 2051-01-01
      devices:
          - Swift
          - 21c 0
      connections:
          - output: 21c 0 Output
            input: Swift Input

    - station: Station 1
      start_time: 2050-01-01
      end_time: 2051-01-01
      devices:
          - Swift
          - 21c 1
      connections:
          - output: 21c 1 Output
            input: Swift Input

    - station: Station 2
      start_time: 2050-01-01
      end_time: 2051-01-01
      devices:
          - PC
          - 21c 2
          - 21c 3
      connections:
          - output: 21c 2 Output
            input: PC Input 0
          - output: 21c 3 Output
            input: PC Input 1

detectors:

    - name: Old Bird Thrush Detector Redux 1.1
      description: Vesper reimplementation of Old Bird Thrush detector.

    - name: Old Bird Tseep Detector Redux 1.1
      description: Vesper reimplementation of Old Bird Tseep detector.

classifiers:

    - name: MPG Ranch NFC Coarse Classifier 3.0
      description: >
          Classifies an unclassified clip as a "Call" if it appears to be
          a nocturnal flight call, or as a "Noise" otherwise. Does not
          classify a clip that has already been classified, whether
          manually or automatically.

annotation_constraints:

    - name: Coarse Classification
      description: Coarse classifications only.
      type: Values
      values:
          - Call
          - Noise
          - Tone
          - Other
          - Unknown

    - name: Classification
      description: All classifications, including call subclassifications.
      type: Hierarchical Values
      extends: Coarse Classification
      values:
          - Call:
              - CHSP
              - COYE

annotations:

    - name: Detector Score
      description: Detector score, a number.
      type: String

    - name: Classification
      description: Classification, possibly hierarchical.
      type: String
      constraint: Classification

tags:
    - name: Review
      description: Indicates clip to be reviewed.

'''
"""Model data shared by various Django unit test modules."""


_TEST_USER_NAME = 'Test'
_TEST_USER_PASSWORD = 'test'


class TestCase(django.test.TestCase, TestCaseMixin):


    def _create_test_user(self):
        user = User.objects.create(username=_TEST_USER_NAME)
        user.set_password(_TEST_USER_PASSWORD)
        user.save()


    def _log_in_as_test_user(self):
        self.client.login(
            username=_TEST_USER_NAME, password=_TEST_USER_PASSWORD)


    def _get_shared_test_model_data(self):

        # This method returns a fresh model data dictionary each time
        # it is called. This leaves callers free to modify the returned
        # dictionary (if needed) without affecting the dictionaries that
        # other callers receive.
        return yaml_utils.load(_SHARED_TEST_MODEL_DATA)


    def _create_shared_test_models(self):
        
        # Create
        model_data = self._get_shared_test_model_data()
        metadata_import_utils.import_metadata(model_data)


    def _assert_model_attributes(
            self, model_class, expected_attributes,
            key_attribute_names=['name'],
            excluded_attribute_names=frozenset()):

        manager = getattr(model_class, 'objects')

        for attributes in expected_attributes:
            kwargs = dict((n, attributes[n]) for n in key_attribute_names)
            model = manager.get(**kwargs)
            self._assert_model_attributes_aux(
                model, attributes, excluded_attribute_names)


    def _assert_model_attributes_aux(
            self, model, expected_attributes,
            excluded_attribute_names=frozenset()):

        for name, value in expected_attributes.items():
            if name not in excluded_attribute_names:
                self.assertEqual(getattr(model, name), value)
