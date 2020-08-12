from django.contrib import admin

from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput,
    DeviceOutput, Job, Processor, Recording, RecordingChannel, RecordingFile,
    Station, StationDevice, StringAnnotation, StringAnnotationEdit, Tag,
    TagEdit, TagInfo)

classes = (
    AnnotationConstraint, AnnotationInfo, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput,
    DeviceOutput, Job, Processor, Recording, RecordingChannel, RecordingFile,
    Station, StationDevice, StringAnnotation, StringAnnotationEdit, Tag,
    TagEdit, TagInfo)
                             
for cls in classes:
    admin.site.register(cls)
