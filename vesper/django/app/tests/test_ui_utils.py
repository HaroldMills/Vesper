import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from vesper.django.app.models import Processor
from vesper.singletons import preference_manager
from vesper.tests.test_case import TestCase
import vesper.django.app.ui_utils as ui_utils


class UiUtilsTests(TestCase):
    
    
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
        
        
    def test_get_processor_ui_choices(self):
        
        cases = [
            ('Detector', [
                ('Thrush Detector', 'Thrush Detector'),
                ('Tseep Detector', 'Tseep')]),
            ('Classifier', [('Coarse Classifier', 'Coarse Classifier')]),
            ('Bobo', [])
        ]
        
        for processor_type, expected_choices in cases:
            choices = ui_utils.get_processor_choices(processor_type)
            self.assertEqual(choices, expected_choices)
        
        
    def test_get_processor_ui_name(self):
        
        cases = [
            ('Thrush Detector', 'Thrush Detector'),
            ('Tseep Detector', 'Tseep'),
            ('Tseep', 'Tseep'),
            ('Coarse Classifier', 'Coarse Classifier'),
            ('Species Classifier', 'Species Classifier')
        ]
        
        for name, expected_ui_name in cases:
            ui_name = ui_utils.get_processor_ui_name(name)
            self.assertEqual(ui_name, expected_ui_name)
        
        
    def test_get_processor_archive_name(self):
         
        cases = [
            ('Thrush Detector', 'Thrush Detector'),
            ('Tseep Detector', 'Tseep Detector'),
            ('Tseep', 'Tseep Detector'),
            ('Coarse Classifier', 'Coarse Classifier'),
            ('Species Classifier', 'Species Classifier')
        ]
         
        for name, expected_archive_name in cases:
            archive_name = ui_utils.get_processor_archive_name(name)
            self.assertEqual(archive_name, expected_archive_name)
            
            
    def test_get_processor_ui_name_errors(self):
        self._assert_raises(
            ValueError, ui_utils.get_processor_ui_name,
            'Nonexistent Processor')
        
        
    def test_get_processor_archive_name_errors(self):
        self._assert_raises(
            ValueError, ui_utils.get_processor_archive_name,
            'Nonexistent Processor')
