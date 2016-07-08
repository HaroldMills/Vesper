from django.contrib import admin

from .models import (
    Device, DeviceConnection, DeviceInput, DeviceModel, DeviceModelInput,
    DeviceModelOutput, DeviceOutput, Station, StationDevice)

classes = (
    Device, DeviceConnection, DeviceInput, DeviceModel, DeviceModelInput,
    DeviceModelOutput, DeviceOutput, Station, StationDevice)
                             
for cls in classes:
    admin.site.register(cls)
