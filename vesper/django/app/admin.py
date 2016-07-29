from django.contrib import admin

from .models import (
    Algorithm, Annotation, Clip, Device, DeviceConnection, DeviceInput,
    DeviceModel, DeviceModelInput, DeviceModelOutput, DeviceOutput, Processor,
    Recording, RecordingFile, RecordingJob, Station, StationDevice)

classes = (
    Algorithm, Annotation, Clip, Device, DeviceConnection, DeviceInput,
    DeviceModel, DeviceModelInput, DeviceModelOutput, DeviceOutput, Processor,
    Recording, RecordingFile, RecordingJob, Station, StationDevice)
                             
for cls in classes:
    admin.site.register(cls)
