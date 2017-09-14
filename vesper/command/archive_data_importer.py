"""Module containing class `ArchiveDataImporter`."""


from collections import defaultdict
import datetime
import logging

from django.db import transaction
import yaml

from vesper.command.command import CommandSyntaxError
from vesper.django.app.models import (
    AnnotationConstraint, AnnotationInfo, Device, DeviceConnection,
    DeviceInput, DeviceModel, DeviceModelInput, DeviceModelOutput,
    DeviceOutput, Job, Processor, Station, StationDevice)
import vesper.command.command_utils as command_utils
import vesper.util.time_utils as time_utils


class ArchiveDataImporter:
    
    """
    Importer for archive data including stations, devices, etc.
    
    The data to be archived are in the `archive_data` command argument.
    The value of the argument is a mapping from string keys like `'stations'`
    and `'devices'` to collections of mappings, with each mapping in the
    collection describing the fields of one archive object.
    """
    
    
    extension_name = 'Archive Data Importer'
    
    
    def __init__(self, args):
        self.archive_data = \
            command_utils.get_required_arg('archive_data', args)
    
    
    def execute(self, job_info):
        
        self._logger = logging.getLogger()
        
        try:
            with transaction.atomic():
                self._add_stations()
                self._add_device_models()
                self._add_devices()
                self._add_station_devices()
                self._add_detectors()
                self._add_classifiers()
                self._add_annotation_constraints(job_info)
                self._add_annotations(job_info)
                
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
            
                name = _get_required(data, 'name', 'station')
                
                self._logger.info('Adding station "{}"...'.format(name))
                
                description = data.get('description', '')
                latitude = _get_required(data, 'latitude', 'station')
                longitude = _get_required(data, 'longitude', 'station')
                elevation = _get_required(data, 'elevation', 'station')
                time_zone = _get_required(data, 'time_zone', 'station')
                
                Station.objects.create(
                    name=name,
                    description=description,
                    latitude=latitude,
                    longitude=longitude,
                    elevation=elevation,
                    time_zone=time_zone)


    def _add_device_models(self):
        
        device_models_data = self.archive_data.get('device_models')
        
        if device_models_data is not None:
            
            for data in device_models_data:
                model = self._add_device_model(data)
                self._add_ports(model, data, 'input', DeviceModelInput)
                self._add_ports(model, data, 'output', DeviceModelOutput)
            
            
    def _add_device_model(self, data):
        
        name = _get_required(data, 'name', 'device model')
        
        self._logger.info('Adding device model "{}"...'.format(name))

        type_ = _get_required(data, 'type', 'device model')
        manufacturer = _get_required(data, 'manufacturer', 'device model')
        model = _get_required(data, 'model', 'device model')
        description = data.get('description', '')
        
        model = DeviceModel.objects.create(
            name=name,
            type=type_,
            manufacturer=manufacturer,
            model=model,
            description=description
        )
        
        return model
            

    def _add_ports(self, model, data, port_type, port_class):
        
        port_data = self._get_port_data(data, port_type)
        
        for local_name, channel_num in port_data:
            
            self._logger.info(
                'Adding device model "{}" {} "{}"...'.format(
                    model.name, port_type, local_name))
            
            port_class.objects.create(
                model=model,
                local_name=local_name,
                channel_num=channel_num)


    def _get_port_data(self, data, port_type):

        names = data.get(port_type + 's')
        
        if names is None:
            
            key = 'num_{}s'.format(port_type)
            num_ports = data.get(key, 0)
            
            if num_ports == 0:
                names = []
                
            elif num_ports == 1:
                names = [port_type.capitalize()]
                
            else:
                names = ['{} {}'.format(port_type.capitalize(), i)
                         for i in range(num_ports)]
                
        return [(name, i) for i, name in enumerate(names)]
                
                
    def _add_devices(self):
        
        devices_data = self.archive_data.get('devices')
        
        if devices_data is not None:
            
            models = _create_objects_dict(DeviceModel)
        
            for data in devices_data:
                device = self._add_device(data, models)
                self._add_device_inputs(device)
                self._add_device_outputs(device)
            
            
    def _add_device(self, data, models):
        
        name = _get_required(data, 'name', 'device')
        
        self._logger.info('Adding device "{}"...'.format(name))
        
        model = self._get_device_model(data, models)
        serial_number = _get_required(data, 'serial_number', 'device')
        description = data.get('description', '')
        
        return Device.objects.create(
            name=name,
            model=model,
            serial_number=serial_number,
            description=description)


    def _get_device_model(self, data, models):

        name = _get_required(data, 'model', 'device')
        
        try:
            return models[name]
        except KeyError:
            raise CommandSyntaxError(
                'Unrecognized device model name "{}".'.format(name))


    def _add_device_inputs(self, device):
        
        for model_input in device.model.inputs.all():
            
            self._logger.info(
                'Adding device "{}" input "{}"...'.format(
                    device.name, model_input.local_name))
            
            DeviceInput.objects.create(
                device=device,
                model_input=model_input)
            
            
    def _add_device_outputs(self, device):
                
        for model_output in device.model.outputs.all():
            
            self._logger.info(
                'Adding device "{}" output "{}"...'.format(
                    device.name, model_output.local_name))
            
            DeviceOutput.objects.create(
                device=device,
                model_output=model_output)


    def _add_station_devices(self):
        
        station_devices_data = self.archive_data.get('station_devices')
        
        if station_devices_data is not None:
            
            devices = _create_objects_dict(Device)
            inputs = _create_objects_dict(DeviceInput)
            outputs = _create_objects_dict(DeviceOutput)
        
            for data in station_devices_data:
                
                station = self._get_station(data)
                
                data_name = 'station devices array'
                
                start_time = self._get_time(
                    data, 'start_time', station, data_name)
                end_time = self._get_time(
                    data, 'end_time', station, data_name)
                
                device_names = _get_required(data, 'devices', data_name)
                station_devices = []
                for name in device_names:
                    device = self._get_device(name, devices)
                    self._add_station_device(
                        station, device, start_time, end_time)
                    station_devices.append(device)
                    
                shorthand_inputs, shorthand_outputs = \
                    _get_shorthand_ports(station_devices)
                    
                connections = _get_required(data, 'connections', data_name)
                for connection in connections:
                    output = self._get_port(
                        connection, 'output', shorthand_outputs, outputs)
                    input_ = self._get_port(
                        connection, 'input', shorthand_inputs, inputs)
                    self._add_connection(
                        station, output, input_, start_time, end_time)
                            
    
    def _get_station(self, data):
        name = _get_required(data, 'station', 'station devices item')
        try:
            return Station.objects.get(name=name)
        except Station.DoesNotExist:
            raise CommandSyntaxError('Unrecognized station "{}".'.format(name))
            

    def _get_time(self, data, key, station, data_name):
        dt = _get_required(data, key, data_name)
        if isinstance(dt, datetime.date):
            dt = datetime.datetime(dt.year, dt.month, dt.day)
        return station.local_to_utc(dt)

    
    def _get_device(self, name, devices):
        try:
            return devices[name]
        except KeyError:
            raise CommandSyntaxError('Unrecognized device "{}".'.format(name))
        

    def _add_station_device(self, station, device, start_time, end_time):
        
        self._logger.info(
            'Adding station "{}" device "{}" from {} to {}"...'.format(
                station.name, device.name, str(start_time), str(end_time)))
    
        StationDevice.objects.create(
            station=station,
            device=device,
            start_time=start_time,
            end_time=end_time)
        

    def _get_port(self, connection, port_type, shorthand_ports, ports):
        
        name = _get_required(connection, port_type, 'device connection')
        
        port = shorthand_ports.get(name)
        
        if port is None:
            port = ports.get(name)
            
        if port is None:
            raise CommandSyntaxError(
                'Unrecognized device {} "{}".'.format(port_type, name))
        
        else:
            return port
            
            
    def _add_connection(self, station, output, input_, start_time, end_time):
        
        self._logger.info((
            'Adding station "{}" device connection "{} -> {} '
            'from {} to {}"...').format(
                station.name, output.name, input_.name,
                str(start_time), str(end_time)))
    
        DeviceConnection.objects.create(
            output=output,
            input=input_,
            start_time=start_time,
            end_time=end_time)


    def _add_detectors(self):
        self._add_processors('detectors', 'detector', 'Detector')
        
        
    def _add_processors(self, data_key, log_type_name, db_type_name):
        
        processors_data = self.archive_data.get(data_key)
        
        if processors_data is not None:
            
            for data in processors_data:
            
                name = _get_required(data, 'name', log_type_name)

                self._logger.info(
                    'Adding {} "{}"...'.format(log_type_name, name))
                
                description = data.get('description', '')
                
                Processor.objects.create(
                    name=name,
                    type=db_type_name,
                    description=description)

        
    def _add_classifiers(self):
        self._add_processors('classifiers', 'classifier', 'Classifier')
        
        
    def _add_annotation_constraints(self, job_info):
        
        constraints_data = self.archive_data.get('annotation_constraints')
        
        if constraints_data is not None:
            
            for data in constraints_data:
                
                name = _get_required(data, 'name', 'annotation constraint')
                
                self._logger.info(
                    'Adding annotation constraint "{}"...'.format(name))
                
                description = data.get('description', '')
                text = yaml.dump(data)
                creation_time = time_utils.get_utc_now()
                creating_user = None
                creating_job = Job.objects.get(id=job_info.job_id)
                
                AnnotationConstraint.objects.create(
                    name=name,
                    description=description,
                    text=text,
                    creation_time=creation_time,
                    creating_user=creating_user,
                    creating_job=creating_job)
                
                
    def _add_annotations(self, job_info):
        
        annotations_data = self.archive_data.get('annotations')
        
        if annotations_data is not None:
            
            for data in annotations_data:
                
                name = _get_required(data, 'name', 'annotation')
                
                self._logger.info('Adding annotation "{}"...'.format(name))
                
                description = data.get('description', '')
                type_ = data.get('type', 'String')
                constraint = self._get_annotation_constraint(data)
                creation_time = time_utils.get_utc_now()
                creating_user = None
                creating_job = Job.objects.get(id=job_info.job_id)
                
                AnnotationInfo.objects.create(
                    name=name,
                    description=description,
                    type=type_,
                    constraint=constraint,
                    creation_time=creation_time,
                    creating_user=creating_user,
                    creating_job=creating_job)
    
    
    def _get_annotation_constraint(self, data):
        try:
            name = data['constraint']
        except KeyError:
            return None
        else:
            return AnnotationConstraint.objects.get(name=name)
    
        
def _get_required(data, key, data_name):
    
    try:
        return data[key]
    
    except KeyError:
        raise CommandSyntaxError(
            '{} missing required item "{}".'.format(
                data_name.capitalize(), key))
        
        
def _create_objects_dict(cls):
    objects = {}
    for obj in cls.objects.all():
        objects[obj.name] = obj
        objects[obj.long_name] = obj
    return objects


def _get_shorthand_ports(devices):
    
    # Create mapping from model names to sets of devices.
    model_devices = defaultdict(set)
    for device in devices:
        model_devices[device.model.name].add(device)
        
    # Create mappings from shorthand port names to ports. A shorthand
    # port name is like a regular port name except that it includes
    # only a model name rather than a device name. We include an item
    # in this mapping for each port of each device that is the only one
    # of its model in `devices`.
    shorthand_inputs = {}
    shorthand_outputs = {}
    for model_name, devices in model_devices.items():
        if len(devices) == 1:
            for device in devices:
                _add_shorthand_ports(
                    shorthand_inputs, device.inputs.all(), model_name)
                _add_shorthand_ports(
                    shorthand_outputs, device.outputs.all(), model_name)
                
    return shorthand_inputs, shorthand_outputs
                    
                    
def _add_shorthand_ports(shorthand_ports, ports, model_name):
    for port in ports:
        name = '{} {}'.format(model_name, port.local_name)
        shorthand_ports[name] = port
