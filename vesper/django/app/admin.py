from django.contrib import admin

from .models import (
    Algorithm, Device, DeviceConnection, DeviceInput, DeviceModel,
    DeviceModelInput, DeviceModelOutput, DeviceOutput, Processor,
    Recording, Station, StationDevice)

classes = (
    Algorithm, Device, DeviceConnection, DeviceInput, DeviceModel,
    DeviceModelInput, DeviceModelOutput, DeviceOutput, Processor,
    Recording, Station, StationDevice)
                             
for cls in classes:
    admin.site.register(cls)
