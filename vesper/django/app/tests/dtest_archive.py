from vesper.django.app.archive import Archive
from vesper.django.app.models import Processor
from vesper.django.app.tests.dtest_case import TestCase
from vesper.singleton.preference_manager import preference_manager
import vesper.django.app.metadata_import_utils as metadata_import_utils
import vesper.util.yaml_utils as yaml_utils


_TEST_PREFERENCES = '''

ui_names:

    processors:
        Tseep Detector: Tseep

    annotation_values:

        Classification:
            Call.AMRE: American Redstart
            Call.BTBW: Black-throated Blue Warbler
            Call.CSWA: Chestnut-sided Warbler

        Confidence:
            "-None-": None
            "* | -None-": "Any | None"
            "*": "Any"

hidden_objects:

    processors:
        - Species Classifier

    annotation_values:

        Classification:
            - Black-throated Blue Warbler
            - Call.CSWA

'''


_TEST_MODEL_DATA = '''

detectors:
    - name: Tseep Detector
    - name: Thrush Detector

classifiers:
    - name: Coarse Classifier
    - name: Species Classifier

annotation_constraints:

    - name: Classification
      type: Hierarchical Values
      values:
          - Call:
              - CSWA
              - BTBW
              - AMRE
          - Noise

    - name: Confidence
      type: Values
      values: ['1', '2', '3']

annotations:

    - name: Classification
      type: String
      constraint: Classification

    - name: Confidence
      type: String
      constraint: Confidence

'''


class ArchiveTests(TestCase):
    
    
    def setUp(self):
        preference_manager.load_preferences_from_yaml(_TEST_PREFERENCES)
        model_data = yaml_utils.load(_TEST_MODEL_DATA)
        metadata_import_utils.import_metadata(model_data)
        self._archive = Archive()
        
        
    def test_get_processors_of_type(self):
        
        cases = [
            ('Detector', ['Thrush Detector', 'Tseep Detector']),
            ('Classifier', ['Coarse Classifier', 'Species Classifier']),
            ('Bobo', [])
        ]
        
        for processor_type, expected_names in cases:
            processors = self._archive.get_processors_of_type(processor_type)
            names = [p.name for p in processors]
            self.assertEqual(names, expected_names)


    def test_get_visible_processors_of_type(self):
        
        cases = [
            ('Detector', ['Thrush Detector', 'Tseep Detector']),
            ('Classifier', ['Coarse Classifier']),
            (['Detector', 'Classifier'],
             ['Coarse Classifier', 'Thrush Detector', 'Tseep Detector']),
            ('Bobo', [])
        ]
        
        for processor_type, expected_names in cases:
            processors = \
                self._archive.get_visible_processors_of_type(processor_type)
            names = [p.name for p in processors]
            self.assertEqual(names, expected_names)
            
            
    def test_get_processor(self):
        
        cases = [
            ('Thrush Detector', 'Thrush Detector'),
            ('Tseep Detector', 'Tseep Detector'),
            ('Tseep', 'Tseep Detector')
        ]
        
        for name, expected_name in cases:
            processor = self._archive.get_processor(name)
            self.assertEqual(processor.name, expected_name)
            
            
    def test_get_processor_errors(self):
        self.assert_raises(ValueError, self._archive.get_processor, 'Bobo')

            
    def test_get_processor_ui_name(self):
         
        cases = [
            ('Thrush Detector', 'Thrush Detector'),
            ('Tseep Detector', 'Tseep')
        ]
         
        for name, expected_ui_name in cases:
            processor = self._archive.get_processor(name)
            ui_name = self._archive.get_processor_ui_name(processor)
            self.assertEqual(ui_name, expected_ui_name)
            
            
    # Commented this out after recent workaround to processor caching
    # problem effectively disabled caching.
    # def test_get_processor_ui_name_errors(self):
    #     self._archive.refresh_processor_cache()
    #     processor = Processor.objects.create(name='Bobo', type='Detector')
    #     self.assert_raises(
    #         ValueError, self._archive.get_processor_ui_name, processor)
    #     processor.delete()
        
        
    def test_string_annotation_value_constants(self):
        a = self._archive
        self.assertEqual(a.STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR, '.')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_WILDCARD, '*')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_ANY, '*')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_NONE, '-None-')


    def test_get_string_annotation_values(self):
        
        cases = [
            ('Classification', (
                'Call.AMRE', 'Call.BTBW', 'Call.CSWA', 'Noise')),
            ('Confidence', ('1', '2', '3'))
        ]
        
        for name, expected_values in cases:
            values = self._archive.get_string_annotation_values(name)
            self.assertEqual(values, expected_values)
            
            
    def test_get_string_annotation_values_errors(self):
        self.assert_raises(
            ValueError, self._archive.get_string_annotation_values, 'Bobo')
        
        
    def test_get_string_annotation_value(self):
        
        cases = [
            
            ('Classification', [
                ('Call.AMRE', 'American Redstart'),
                ('Call.BTBW', 'Black-throated Blue Warbler'),
                ('Call.CSWA', 'Chestnut-sided Warbler'),
                ('Noise', 'Noise'),
                ('Bobo', 'Bobo')]),
                
            ('Confidence', [
                ('1', '1'),
                ('2', '2'),
                ('3', '3'),
                ('Bobo', 'Bobo')])
            
        ]
        
        get_archive_value = self._archive.get_string_annotation_archive_value
        get_ui_value = self._archive.get_string_annotation_ui_value
        
        for name, pairs in cases:
            
            for archive_value, ui_value in pairs:
                
                value = get_archive_value(name, archive_value)
                self.assertEqual(value, archive_value)
                
                value = get_archive_value(name, ui_value)
                self.assertEqual(value, archive_value)
                
                value = get_ui_value(name, archive_value)
                self.assertEqual(value, ui_value)
                
                value = get_ui_value(name, ui_value)
                self.assertEqual(value, ui_value)


    def test_get_string_annotation_archive_value_errors(self):
        self.assert_raises(
            ValueError, self._archive.get_string_annotation_archive_value,
            'Bobo', 'Value')


    def test_get_string_annotation_ui_value_errors(self):
        self.assert_raises(
            ValueError, self._archive.get_string_annotation_ui_value,
            'Bobo', 'Value')
        
        
    def test_get_visible_string_annotation_ui_values(self):
        
        cases = [
            ('Classification', ('American Redstart', 'Noise'))
        ]
        
        for annotation_name, expected_values in cases:
            values = self._archive.get_visible_string_annotation_ui_values(
                annotation_name)
            self.assertEqual(values, expected_values)
            
            
    def test_get_visible_string_annotation_ui_values_errors(self):
        self.assert_raises(
            ValueError, self._archive.get_visible_string_annotation_ui_values,
            'Bobo')

        
    def test_get_visible_string_annotation_ui_value_specs(self):
        
        cases = [
            
            ('Classification', (
                '-----',
                '-None-',
                '*',
                'Call',
                'Call*',
                'Call.*',
                'American Redstart',
                'Noise')),
            
            ('Confidence', (
                '-----',
                'None',
                'Any',
                '1',
                '2',
                '3'))

        ]
        
        for annotation_name, expected_choices in cases:
            archive = self._archive
            choices = archive.get_visible_string_annotation_ui_value_specs(
                annotation_name)
            self.assertEqual(choices, expected_choices)


    def test_get_visible_string_annotation_ui_value_specs_errors(
            self):
        
        self.assert_raises(
            ValueError,
            self._archive.get_visible_string_annotation_ui_value_specs,
            'Bobo')
