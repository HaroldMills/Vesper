import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.archive import Archive
from vesper.django.app.models import Processor
from vesper.singletons import preference_manager
from vesper.tests.test_case import TestCase


class ArchiveTests(TestCase):
    
    
    @classmethod
    def setUpClass(cls):
        
        preference_manager.instance._push_test_module_preferences(__file__)
        
        create = Processor.objects.create
        create(name='Tseep Detector', type='Detector')
        create(name='Thrush Detector', type='Detector')
        create(name='Coarse Classifier', type='Classifier')
        create(name='Species Classifier', type='Classifier')
        
        
    @classmethod
    def tearDownClass(cls):
        preference_manager.instance._pop_test_preferences()
        

    def setUp(self):
        self._archive = Archive()
        
        
    def test_get_processors(self):
        
        cases = [
            ('Detector', ['Thrush Detector', 'Tseep Detector']),
            ('Classifier', ['Coarse Classifier', 'Species Classifier']),
            ('Bobo', [])
        ]
        
        for processor_type, expected_names in cases:
            processors = self._archive.get_processors(processor_type)
            names = [p.name for p in processors]
            self.assertEqual(names, expected_names)
            
            
    def test_get_visible_processors(self):
        
        cases = [
            ('Detector', ['Thrush Detector', 'Tseep Detector']),
            ('Classifier', ['Coarse Classifier']),
            ('Bobo', [])
        ]
        
        for processor_type, expected_names in cases:
            processors = self._archive.get_visible_processors(processor_type)
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
