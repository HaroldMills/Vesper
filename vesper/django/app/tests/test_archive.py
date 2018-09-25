import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.archive import Archive
from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Processor)
from vesper.singletons import preference_manager
from vesper.tests.test_case import TestCase
import vesper.util.time_utils as time_utils


_CLASSIFICATION_CONSTRAINT_TEXT = '''
name: Classification
type: Hierarchical Values
values:
    - Call:
        - CSWA
        - BTBW
        - AMRE
    - Noise
'''.lstrip()

_CONFIDENCE_CONSTRAINT_TEXT = '''
name: Confidence
type: Values
values: ['1', '2', '3']
'''.lstrip()


class ArchiveTests(TestCase):
    
    
    @classmethod
    def setUpClass(cls):
        
        preference_manager.instance._push_test_module_preferences(__file__)
        
        create = Processor.objects.create
        create(name='Tseep Detector', type='Detector')
        create(name='Thrush Detector', type='Detector')
        create(name='Coarse Classifier', type='Classifier')
        create(name='Species Classifier', type='Classifier')
        
        creation_time = time_utils.get_utc_now()
        
        constraint = AnnotationConstraint.objects.create(
            name='Classification',
            text=_CLASSIFICATION_CONSTRAINT_TEXT,
            creation_time=creation_time)
        
        AnnotationInfo.objects.create(
            name='Classification',
            type='String',
            constraint=constraint,
            creation_time=creation_time)
        
        constraint = AnnotationConstraint.objects.create(
            name='Confidence',
            text=_CONFIDENCE_CONSTRAINT_TEXT,
            creation_time=creation_time)
        
        AnnotationInfo.objects.create(
            name='Confidence',
            type='String',
            constraint=constraint,
            creation_time=creation_time)
        
        
    @classmethod
    def tearDownClass(cls):
        preference_manager.instance._pop_test_preferences()
        

    def setUp(self):
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
        self._assert_raises(ValueError, self._archive.get_processor, 'Bobo')

            
    def test_get_processor_ui_name(self):
         
        cases = [
            ('Thrush Detector', 'Thrush Detector'),
            ('Tseep Detector', 'Tseep')
        ]
         
        for name, expected_ui_name in cases:
            processor = self._archive.get_processor(name)
            ui_name = self._archive.get_processor_ui_name(processor)
            self.assertEqual(ui_name, expected_ui_name)
            
            
    def test_get_processor_ui_name_errors(self):
        self._archive.refresh_processor_cache()
        processor = Processor.objects.create(name='Bobo', type='Detector')
        self._assert_raises(
            ValueError, self._archive.get_processor_ui_name, processor)
        processor.delete()
        
        
    def test_string_annotation_value_constants(self):
        a = self._archive
        self.assertEqual(a.STRING_ANNOTATION_VALUE_COMPONENT_SEPARATOR, '.')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_WILDCARD, '*')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_ANY, '*')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_NONE, '-None-')
        self.assertEqual(a.STRING_ANNOTATION_VALUE_ANY_OR_NONE, '* | -None-')
        
        
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
        self._assert_raises(
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
        self._assert_raises(
            ValueError, self._archive.get_string_annotation_archive_value,
            'Bobo', 'Value')


    def test_get_string_annotation_ui_value_errors(self):
        self._assert_raises(
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
        self._assert_raises(
            ValueError, self._archive.get_visible_string_annotation_ui_values,
            'Bobo')

        
    def test_get_visible_string_annotation_ui_value_specs(self):
        
        cases = [
            
            ('Classification', (
                '-None-',
                '* | -None-',
                '*',
                'Call',
                'Call*',
                'Call.*',
                'American Redstart',
                'Noise')),
            
            ('Confidence', (
                'None',
                'Any | None',
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
        
        self._assert_raises(
            ValueError,
            self._archive.get_visible_string_annotation_ui_value_specs,
            'Bobo')
