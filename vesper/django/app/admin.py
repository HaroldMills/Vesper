from django.contrib import admin

from .models import (
    Algorithm, AlgorithmVersion, Annotation, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput, DeviceOutput,
    Processor, Recording, RecordingFile, RecordingJob, Station, StationDevice)

classes = (
    Algorithm, AlgorithmVersion, Annotation, Clip, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput, DeviceOutput,
    Processor, Recording, RecordingFile, RecordingJob, Station, StationDevice)
                             
for cls in classes:
    admin.site.register(cls)
