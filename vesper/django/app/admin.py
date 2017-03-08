from django.contrib import admin

from .models import (
    Algorithm, AlgorithmVersion, Annotation, AnnotationValueConstraint, Clip,
    Device, DeviceConnection, DeviceInput, DeviceModel, DeviceModelInput,
    DeviceModelOutput, DeviceOutput, Processor, Recording, RecordingFile,
    RecordingJob, Station, StationDevice, StringAnnotationValue,
    StringAnnotationValueHistory)

classes = (
    Algorithm, AlgorithmVersion, Annotation, AnnotationValueConstraint, Clip,
    Device, DeviceConnection, DeviceInput, DeviceModel, DeviceModelInput,
    DeviceModelOutput, DeviceOutput, Processor, Recording, RecordingFile,
    RecordingJob, Station, StationDevice, StringAnnotationValue,
    StringAnnotationValueHistory)
                             
for cls in classes:
    admin.site.register(cls)
