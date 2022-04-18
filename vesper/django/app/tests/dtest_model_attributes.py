from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Device, DeviceModel, Processor,
    Station, TagInfo)
from vesper.django.app.tests.dtest_case import TestCase


class ModelAttributeTests(TestCase):
    
    
    def setUp(self):
        self._create_shared_test_models()
        self.test_model_data = self._get_shared_test_model_data()
       
        
    def test_station_attributes(self):
        expected_attributes = self.test_model_data['stations']
        self._assert_model_attributes(Station, expected_attributes)


    def test_device_model_attributes(self):
        expected_attributes = self.test_model_data['device_models']
        key_attribute_names = frozenset(('manufacturer', 'model'))
        excluded_attribute_names = frozenset(('num_inputs', 'num_outputs'))
        self._assert_model_attributes(
            DeviceModel, expected_attributes, key_attribute_names,
            excluded_attribute_names)


    def test_device_attributes(self):
        expected_attributes = self.test_model_data['devices']
        excluded_attribute_names = frozenset(('model',))
        self._assert_model_attributes(
            Device, expected_attributes,
            excluded_attribute_names=excluded_attribute_names)


    def test_processor_attributes(self):
        expected_attributes = self._get_processor_expected_attributes()
        key_attribute_names = frozenset(('name', 'type'))
        self._assert_model_attributes(
            Processor, expected_attributes, key_attribute_names)


    def _get_processor_expected_attributes(self):
        aux = self._get_processor_expected_attributes_aux
        detectors = aux('Detector')
        classifiers = aux('Classifier')
        return detectors + classifiers


    def _get_processor_expected_attributes_aux(self, processor_type):
        key = processor_type.lower() + 's'
        model_data = self.test_model_data[key]
        for data in model_data:
            data['type'] = processor_type
        return model_data


    def test_annotation_constraint_attributes(self):
        expected_attributes = self.test_model_data['annotation_constraints']
        excluded_attribute_names = frozenset(('type', 'extends', 'values'))
        self._assert_model_attributes(
            AnnotationConstraint, expected_attributes,
            excluded_attribute_names=excluded_attribute_names)


    def test_annotation_attributes(self):
        expected_attributes = self.test_model_data['annotations']
        excluded_attribute_names = frozenset(('constraint',))
        self._assert_model_attributes(
            AnnotationInfo, expected_attributes,
            excluded_attribute_names=excluded_attribute_names)


    def test_tag_attributes(self):
        expected_attributes = self.test_model_data['tags']
        excluded_attribute_names = frozenset(('constraint',))
        self._assert_model_attributes(
            TagInfo, expected_attributes,
            excluded_attribute_names=excluded_attribute_names)
