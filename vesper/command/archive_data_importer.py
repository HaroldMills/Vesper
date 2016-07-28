import datetime

from django.db import transaction
import pytz

from vesper.command.command import CommandSyntaxError
from vesper.django.app.models import (
    Device, DeviceConnection, DeviceInput, DeviceModel, DeviceModelInput,
    DeviceModelOutput, DeviceOutput, Station, StationDevice)
import vesper.command.command_utils as command_utils


# TODO: Recover more gracefully when data are missing, e.g. raise a
# `CommandSyntaxError` rather than a `KeyError`.
# TODO: Make sure one can set any field from archive data.
# TODO: Make sure there are reasonable defaults for various archive data,
# e.g. descriptions.


class ArchiveDataImporter:
    
    
    name = 'Archive Data Importer'
    
    
    def __init__(self, args):
        self.archive_data = command_utils.get_required_arg('archive_data', args)
    
    
    def execute(self, context):
        
        self._logger = context.job.logger
        
        try:
            with transaction.atomic():
                self._add_stations()
                self._add_device_models()
                self._add_devices()
                self._add_station_devices()
                
        except Exception:
            self._logger.error(
                'Archive data import failed with an exception. Database '
                'has been restored to its state before the import. See '
                'below for exception traceback.')
            raise
        
        return True
            
            
    def _add_stations(self):
        
        stations_data = self.archive_data.get('stations')
        
        if stations_data is not None:
            
            for data in stations_data:
            
                self._logger.info(
                    'Adding station "{}"...'.format(data['name']))
                
                station = Station(
                    name=data['name'],
                    description=data['description'],
                    latitude=data['latitude'],
                    longitude=data['longitude'],
                    elevation=data['elevation'],
                    time_zone=data['time_zone'])
                
                station.save()


    def _add_device_models(self):
        
        device_models_data = self.archive_data.get('device_models')
        
        if device_models_data is not None:
            
            for data in device_models_data:
                model = self._add_device_model(data)
                self._add_device_model_inputs(model, data)
                self._add_device_model_outputs(model, data)
            
            
    def _add_device_model(self, data):
        
        self._logger.info(
            'Adding device model "{} {} {}"...'.format(
                data['manufacturer'], data['model'], data['type']))
        
        model = DeviceModel(
            type=data['type'],
            manufacturer=data['manufacturer'],
            model=data['model'],
            short_name=data['short_name'],
            description=data['description']
        )
        
        model.save()
        
        return model
            

    def _add_device_model_inputs(self, model, data):
        
        names = self._get_port_names(data, 'input')
        
        for name in names:
            
            self._logger.info(
                'Adding device model input "{} {}"...'.format(
                    model.long_name, name))
            
            input_ = DeviceModelInput(model=model, name=name)
            input_.save()
            
    
    def _get_port_names(self, data, port_type):

        names = data.get(port_type + 's')
        
        if names is None:
            
            key = 'num_{}s'.format(port_type)
            num_ports = data.get(key, 0)
            
            if num_ports == 0:
                return []
                
            elif num_ports == 1:
                return [port_type.capitalize()]
                
            else:
                return [
                    '{} {}'.format(port_type.capitalize(), i)
                    for i in range(num_ports)]
                
                
    def _add_device_model_outputs(self, model, data):
        
        names = self._get_port_names(data, 'output')
        
        for name in names:
            
            self._logger.info(
                'Adding device model output "{} {}"...'.format(
                    model.long_name, name))
            
            output = DeviceModelOutput(model=model, name=name)
            output.save()
            
            
    def _add_devices(self):
        
        devices_data = self.archive_data.get('devices')
        
        if devices_data is not None:
            
            models = _create_objects_dict(DeviceModel)
        
            for data in devices_data:
                model = self._get_device_model(data, models)
                device = self._add_device(data, model)
                self._add_device_inputs(device)
                self._add_device_outputs(device)
            
            
    def _get_device_model(self, data, models):
    
        name = data['model']
        try:
            return models[name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized device model name "{}".'.format(name))


    def _add_device(self, data, model):
        
        serial_number = data['serial_number']
        description = data.get('description', '')
        
        self._logger.info(
            'Adding device "{} {}"...'.format(
                model.long_name, serial_number))
        
        device = Device(
            model=model,
            serial_number=serial_number,
            description=description)
        
        device.save()
        
        return device


    def _add_device_inputs(self, device):
        
        for model_input in device.model.inputs.all():
            
            self._logger.info(
                'Adding device input "{} {}"...'.format(
                    device.long_name, model_input.name))
            
            input_ = DeviceInput(model_input=model_input, device=device)
            input_.save()
            
            
    def _add_device_outputs(self, device):
                
        for model_output in device.model.outputs.all():
            
            self._logger.info(
                'Adding device output "{} {}"...'.format(
                    device.long_name, model_output.name))
            
            output = DeviceOutput(model_output=model_output, device=device)
            output.save()


    def _add_station_devices(self):
        
        station_devices_data = self.archive_data.get('station_devices')
        
        if station_devices_data is not None:
            
            devices = _create_objects_dict(Device)
            inputs = _create_objects_dict(DeviceInput)
            outputs = _create_objects_dict(DeviceOutput)
        
            for data in station_devices_data:
                
                station = self._get_station(data)
                start_time = _get_utc_time(data['start_time'], station)
                end_time = _get_utc_time(data['end_time'], station)
                
                device_names = data['devices']
                for name in device_names:
                    device = self._get_device(name, devices)
                    self._add_station_device(
                        station, device, start_time, end_time)
                
                connections = data['connections']
                for connection in connections:
                    output = self._get_output(connection['output'], outputs)
                    input_ = self._get_input(connection['input'], inputs)
                    self._add_connection(output, input_, start_time, end_time)
                            
    
    def _get_station(self, data):
        name = data['station']
        try:
            return Station.objects.get(name=name)
        except Station.DoesNotExist:
            raise CommandSyntaxError(
                'Unrecognized station "{}".'.format(name))
            

    def _get_device(self, name, devices):
        try:
            return devices[name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized device "{}".'.format(name))
        

    def _add_station_device(self, station, device, start_time, end_time):
        
        self._logger.info(
            'Adding station device "{} at {} from {} to {}"...'.format(
                device.short_name, station.name,
                str(start_time), str(end_time)))
    
        station_device = StationDevice(
            station=station, device=device,
            start_time=start_time, end_time=end_time)
        
        station_device.save()
        

    def _get_output(self, name, outputs):
        try:
            return outputs[name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized device output "{}".'.format(name))


    def _get_input(self, name, inputs):
        try:
            return inputs[name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized device input "{}".'.format(name))


    def _add_connection(self, output, input_, start_time, end_time):
        
        self._logger.info((
            'Adding device connection "{} -> {} '
            'from {} to {}"...').format(
                output.short_name, input_.short_name,
                str(start_time), str(end_time)))
    
        connection = DeviceConnection(
            output=output, input=input_,
            start_time=start_time, end_time=end_time)
        
        connection.save()


def _create_objects_dict(cls):
    objects = {}
    for obj in cls.objects.all():
        objects[obj.long_name] = obj
        objects[obj.short_name] = obj
    return objects


# TODO: Move this to another module and make it public?
def _get_utc_time(dt, station):
    if isinstance(dt, datetime.date):
        dt = datetime.datetime(dt.year, dt.month, dt.day)
    if dt.tzinfo is None:
        time_zone = pytz.timezone(station.time_zone)
        dt = time_zone.localize(dt)
        dt = dt.astimezone(pytz.utc)
    return dt
