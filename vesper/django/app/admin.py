from django.contrib import admin

from .models import (
    Algorithm, Bot, Device, DeviceConnection, DeviceInput, DeviceModel,
    DeviceModelInput, DeviceModelOutput, DeviceOutput, Station, StationDevice)

classes = (
    Algorithm, Bot, Device, DeviceConnection, DeviceInput, DeviceModel,
    DeviceModelInput, DeviceModelOutput, DeviceOutput, Station, StationDevice)
                             
for cls in classes:
    admin.site.register(cls)
