from django.contrib import admin

from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput,
    DeviceOutput, Processor, Recording, RecordingFile, Station, StationDevice,
    StringAnnotation)

classes = (
    AnnotationConstraint, AnnotationInfo, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput,
    DeviceOutput, Processor, Recording, RecordingFile, Station, StationDevice,
    StringAnnotation)
                             
for cls in classes:
    admin.site.register(cls)
