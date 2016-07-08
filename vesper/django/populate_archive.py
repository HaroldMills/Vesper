from collections import defaultdict
import datetime
import os

# Set up Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vesper.django.project.settings'
import django
django.setup()

from django.db import transaction
import pytz

from vesper.archive.archive import Archive
from vesper.django.app.models import (
    Annotation, Clip, Device, DeviceConnection, DeviceInput, DeviceModel,
    DeviceModelInput, DeviceModelOutput, DeviceOutput, Recording, Station,
    StationDevice)
import vesper.django.app.yaml_utils as yaml_utils
import vesper.util.os_utils as os_utils


_ARCHIVE_DATA = '''

device_models:

    - type: Audio Recorder
      manufacturer: Wildlife Acoustics
      model: Song Meter SM2
      short_name: SM2
      num_inputs: 2
      
    - type: Microphone
      manufacturer: Wildlife Acoustics
      model: SMX-NFC
      short_name: SMX-NFC
      
devices:

    - model: SM2
      serial_number: MPG_00
      description: >
          Recorder used at Baldy station.
          Serial number is a fake placeholder.
      
    - model: SM2
      serial_number: MPG_01
      description: >
          Recorder used at Floodplain station.
          Serial number is a fake placeholder.
      
      
    - model: SM2
      serial_number: MPG_02
      description: >
          Recorder used at Ridge station.
          Serial number is a fake placeholder.
      
    - model: SM2
      serial_number: MPG_03
      description: >
          Recorder used at Sheep Camp station.
          Serial number is a fake placeholder.
      
    - model: SMX-NFC
      serial_number: MPG_00
      description: >
          Microphone used at Baldy station.
          Serial number is a fake placeholder.
          
    - model: SMX-NFC
      serial_number: MPG_01
      description: >
          Microphone used at Floodplain station.
          Serial number is a fake placeholder.
          
    - model: SMX-NFC
      serial_number: MPG_02
      description: >
          Microphone used at Ridge station.
          Serial number is a fake placeholder.
          
    - model: SMX-NFC
      serial_number: MPG_03
      description: >
          Microphone used at Sheep Camp station.
          Serial number is a fake placeholder.
          
stations:

    - name: Baldy
      latitude: 46.70976
      longitude: -113.98103
      elevation: 1821.2
      time_zone: US/Mountain

    - name: Floodplain
      latitude: 46.69966
      longitude: -114.04250
      elevation: 990.6
      time_zone: US/Mountain
      
    - name: Ridge
      latitude: 46.70371
      longitude: -113.98831
      elevation: 1702.3
      time_zone: US/Mountain

    - name: Sheep Camp
      latitude: 46.69847
      longitude: -114.02032
      elevation: 1165.9
      time_zone: US/Mountain
      
excluded_stations:

    - name: Florence
      latitude: 46.641042
      longitude: -114.076499
      elevation: 995.4
      time_zone: US/Mountain
      
    - name: Darby
      latitude: 46.026778
      longitude: -114.178878
      elevation: 1188.7
      time_zone: US/Mountain

    - name: Medicine Wheel
      latitude: 45.22331
      longitude: -109.17268
      elevation: 1682.5
      time_zone: US/Mountain
      
station_devices:

    - station: Baldy
      start_time: 2012-01-01
      end_time: 2014-12-31
      devices:
          - SM2 MPG_00
          - SMX-NFC MPG_00
      connections:
          - output: SMX-NFC MPG_00 Audio Output
            input: SM2 MPG_00 Audio Input 0
            
    - station: Floodplain
      start_time: 2012-01-01
      end_time: 2014-12-31
      devices:
          - SM2 MPG_01
          - SMX-NFC MPG_01
      connections:
          - output: SMX-NFC MPG_01 Audio Output
            input: SM2 MPG_01 Audio Input 0
            
    - station: Ridge
      start_time: 2012-01-01
      end_time: 2014-12-31
      devices:
          - SM2 MPG_02
          - SMX-NFC MPG_02
      connections:
          - output: SMX-NFC MPG_02 Audio Output
            input: SM2 MPG_02 Audio Input 0
            
    - station: Sheep Camp
      start_time: 2012-01-01
      end_time: 2014-12-31
      devices:
          - SM2 MPG_03
          - SMX-NFC MPG_03
      connections:
          - output: SMX-NFC MPG_03 Audio Output
            input: SM2 MPG_03 Audio Input 0
            
'''


_ARCHIVE_DIR_PATH = \
    r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch\MPG Ranch 2012-2014'
_ARCHIVE_DATABASE_FILE_NAME = 'Archive Database.sqlite'
_ARCHIVE_DATABASE_FILE_PATH = os.path.join(
    _ARCHIVE_DIR_PATH, _ARCHIVE_DATABASE_FILE_NAME)


def _main():
    _delete_data()
    _add_data()
    
    
def _delete_data():
    for model in DeviceModel.objects.all():
        model.delete()
    for station in Station.objects.all():
        station.delete()
        
        
def _add_data():
    
    data = yaml_utils.load(_ARCHIVE_DATA)
    
    _add_device_models(data)
    _add_devices(data)
    _add_stations(data)
    _add_station_devices(data)
    
    _add_recordings()
    _add_clips()
    
    # _show_data()


def _add_stations(data):
    
    for d in data['stations']:
        
        name = d['name']
        latitude = d['latitude']
        longitude = d['longitude']
        elevation = d['elevation']
        time_zone = d['time_zone']
        
        station = Station(
            name=name, latitude=latitude, longitude=longitude,
            elevation=elevation, time_zone=time_zone)
        station.save()


def _add_station_devices(data):
    
    devices = _create_devices_dict()
    outputs = _create_io_port_dict(DeviceOutput)
    inputs = _create_io_port_dict(DeviceInput)
    
    for d in data['station_devices']:
        
        name = d['station']
        
        try:
            station = Station.objects.get(name=name)
        except Station.DoesNotExist:
            raise ValueError('Unrecognized station "{}".'.format(name))
        
        start_time = _get_utc_time(d['start_time'], station)
        end_time = _get_utc_time(d['end_time'], station)
        
        device_names = d['devices']
        
        for name in device_names:

            try:
                device = devices[name]
            except KeyError:
                raise ValueError('Unrecognized device "{}".'.format(name))
            
            station_device = StationDevice(
                station=station, device=device, start_time=start_time,
                end_time=end_time)
            station_device.save()
        
        connections = d['connections']
        
        for c in connections:
            
            name = c['output']
            try:
                output = outputs[name]
            except KeyError:
                raise ValueError(
                    'Unrecognized device output "{}".'.format(name))
        
            name = c['input']
            try:
                input_ = inputs[name]
            except KeyError:
                raise ValueError(
                    'Unrecognized device input "{}".'.format(name))
            
            connection = DeviceConnection(
                output=output, input=input_, start_time=start_time,
                end_time=end_time)
            connection.save()
        
    
def _create_devices_dict():
    
    devices = {}
    
    for d in Device.objects.all():
        
        m = d.model
        
        name = '{} {}'.format(str(m), d.serial_number)
        devices[name] = d
        
        name = '{} {}'.format(m.short_name, d.serial_number)
        devices[name] = d
        
        if d.name is not None:
            devices[d.name] = d
        
    return devices

        
def _create_io_port_dict(cls):
    
    ports = {}
    
    for port in cls.objects.all():
        
        d = port.device
        m = d.model
        
        name = '{} {} {}'.format(str(m), d.serial_number, str(port))
        ports[name] = port
        
        name = '{} {} {}'.format(m.short_name, d.serial_number, str(port))
        ports[name] = port
        
        if d.name is not None:
            name = '{} {}'.format(d.name, str(port))
            ports[name] = port
        
    return ports
        
        
# TODO: Move this to another module and make it public?
def _get_utc_time(dt, station):
    if dt.tzinfo is None:
        time_zone = pytz.timezone(station.time_zone)
        dt = time_zone.localize(dt)
        dt = dt.astimezone(pytz.utc)
    return dt


def _add_device_models(data):
    
    for d in data['device_models']:

        model = DeviceModel(
            type=d['type'], manufacturer=d['manufacturer'], model=d['model'],
            short_name=d.get('short_name'))
        model.save()
        
        _add_device_model_inputs(model, d)
        _add_device_model_outputs(model, d)
                
                
def _add_device_model_inputs(model, data):

        inputs = data.get('inputs')
        
        if inputs is not None:
            names = [i['name'] for i in inputs]
            _add_device_model_inputs_aux(model, names)
                
        elif model.type == 'Audio Recorder':
            
            num_inputs = data.get('num_inputs', 1)
            
            if num_inputs == 1:
                names = ['Audio Input']
            else:
                names = ['Audio Input ' + str(i) for i in range(num_inputs)]
                
            _add_device_model_inputs_aux(model, names)


def _add_device_model_inputs_aux(model, names):
    for name in names:
        input_ = DeviceModelInput(model=model, name=name)
        input_.save()
        

def _add_device_model_outputs(model, data):
    
    outputs = data.get('outputs')
    
    if outputs is not None:
        names = [o['name'] for o in outputs]
        _add_device_model_outputs_aux(model, names)
            
    elif model.type == 'Microphone':
        _add_device_model_outputs_aux(model, ['Audio Output'])
        
        
def _add_device_model_outputs_aux(model, names):
    for name in names:
        output = DeviceModelOutput(model=model, name=name)
        output.save()
        
        
def _add_devices(data):
    
    models = DeviceModel.objects.all()
    models_by_full_name = dict((str(m), m) for m in models)
    models_by_short_name = dict((m.short_name, m) for m in models)
    
    for d in data['devices']:
        
        name = d['model']
        model = models_by_full_name.get(name)
        if model is None:
            model = models_by_short_name.get(name)
            if model is None:
                raise ValueError(
                    'Unrecognized device model name "{}".'.format(name))
                
        serial_number = d['serial_number']
        device = Device(model=model, serial_number=serial_number)
        device.save()
        
        for model_input in model.inputs.all():
            input_ = DeviceInput(model_input=model_input, device=device)
            input_.save()
            
        for model_output in model.outputs.all():
            output = DeviceOutput(model_output=model_output, device=device)
            output.save()
        
    
def _add_recordings():
    recordings = _get_recordings()
    for r in recordings:
        station = _get_recording_station(r)
        recorder = _get_recording_recorder(r)
        span = (r.length - 1) / r.sample_rate
        end_time = r.start_time + datetime.timedelta(seconds=span)
        recording = Recording(
            station=station, recorder=recorder, num_channels=1, length=r.length,
            sample_rate=r.sample_rate, start_time=r.start_time,
            end_time=end_time)
        recording.save()
        
    
def _get_recording_station(recording):
    return Station.objects.get(name=recording.station.name)


def _get_recording_recorder(recording):
    
    station = _get_recording_station(recording)
    start_time = recording.start_time
    end_time = recording.end_time
    
    # The following raised a django.core.exceptions.FieldError exception
    # with the message "Unsupported lookup 'le' for DateTimeField or join
    # on the field not permitted.". I'm not sure why Django would not
    # support le (or ge) lookups on date/time fields.
#     for sd in station.device_associations.filter(
#             start_time__le=start_time, end_time__ge=end_time):
#         return sd.device

    for sd in station.device_associations.all():
        if sd.device.model.type == 'Audio Recorder' and \
                sd.start_time <= start_time and \
                sd.end_time >= end_time:
            return sd.device
        
    raise ValueError(
        'Could not find recorder for station "{}".'.format(station.name))
        
        
def _get_recordings():
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    recordings = set()
    for station in stations:
        night = start_night
        while night <= end_night:
            for r in archive.get_recordings(station.name, night):
                recordings.add(r)
            night += one_night
    archive.close()
    recordings = list(recordings)
    recordings.sort(key=lambda r: (r.station.name, r.start_time))
    return recordings


def _add_clips():
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    stations = archive.stations
    start_night = archive.start_night
    end_night = archive.end_night
    one_night = datetime.timedelta(days=1)
    station_recordings = _get_station_recordings()
    num_added = 0
    num_rejected = 0
    for station in stations:
        night = start_night
        while night <= end_night:
            clips = archive.get_clips(station_name=station.name, night=night)
            (m, n) = _add_clips_aux(clips, station_recordings)
            num_added += m
            num_rejected += n
            night += one_night
    archive.close()
    print('added {} clips, rejected {}'.format(num_added, num_rejected))
    
    
def _get_station_recordings():
    recordings = defaultdict(list)
    for recording in Recording.objects.all():
        recordings[recording.station.name].append(recording)
    return recordings
        
        
def _add_clips_aux(clips, station_recordings):
    
    num_added = 0
    num_rejected = 0
    
    for c in clips:
        
        try:
            recording = _get_clip_recording(c, station_recordings)
        except ValueError as e:
            print(str(e))
            num_rejected += 1
            continue
        
        with transaction.atomic():
            
            sound = c.sound
            length = len(sound.samples)
            start_time = c.start_time
            span = (length - 1) / sound.sample_rate
            end_time = start_time + datetime.timedelta(seconds=span)
            imported_file_path = c.file_path
            
            clip = Clip(
                station=recording.station, recorder=recording.recorder,
                recording=recording, channel_num=0, start_index=None,
                length=length, sample_rate=sound.sample_rate,
                start_time=start_time, end_time=end_time,
                imported_file_path=imported_file_path)
            clip.save()
            
            _copy_clip_sound_file(clip)
            
            a = Annotation(clip=clip, name='Detector', value=c.detector_name)
            a.save()
            
            s = c.selection
            if s is not None:
                a = Annotation(clip=clip, name='Selection Start Index', value=s[0])
                a.save()
                a = Annotation(clip=clip, name='Selection Length', value=s[1])
                a.save()
            
            a = Annotation(
                clip=clip, name='Classification', value=c.clip_class_name)
            a.save()
            
            num_added += 1
        
    return (num_added, num_rejected)
    

def _copy_clip_sound_file(clip):
    
    with open(clip.imported_file_path, 'rb') as file_:
        contents = file_.read()
         
    # Create clip directory if needed.
    dir_path = os.path.dirname(clip.wav_file_path)
    os_utils.create_directory(dir_path)
    
    with open(clip.wav_file_path, 'wb') as file_:
        file_.write(contents)

    print('Wrote file "{}" for clip {}.'.format(clip.wav_file_path, clip.id))

    
def _get_clip_recording(clip, station_recordings):
    
    time = clip.start_time
    
    # Django doesn't seem to support this. Not sure why.
#     try:
#         return station.recordings.get(start_time__le=time, end_time__ge=time)
#     except Recording.DoesNotExist:
#         raise ValueError(
#             'Could not find recording for clip "{}".'.format(clip.file_path))

    # TODO: Sort recordings by start time and use binary search to
    # find the recording that contains a clip.
    for r in station_recordings[clip.station.name]:
        start_time = r.start_time
        end_time = r.end_time
        if start_time <= time and time <= end_time:
            return r
    raise ValueError(
        'Could not find recording for clip "{}".'.format(clip.file_path))
    
    
def _get_floor_noon(time, station):
    time_zone = pytz.timezone(station.time_zone)
    dt = time.astimezone(time_zone)
    d = dt.date()
    if dt.hour < 12:
        d -= datetime.timedelta(days=1)
    noon = datetime.datetime(d.year, d.month, d.day, 12)
    noon = time_zone.localize(noon)
    noon = noon.astimezone(pytz.utc)
    return noon


def _show_data():
    _show_device_models()
    print()
    _show_devices()
    print()
    _show_stations()
    print()
    _show_recordings()
    print()
    _show_clips()
    
    
def _show_device_models():
    for model in DeviceModel.objects.all():
        print(model)
        for input_ in model.inputs.all():
            print('    ' + str(input_))
        for output in model.outputs.all():
            print('    ' + str(output))
            
            
def _show_devices():
    for device in Device.objects.all():
        print(device)
        for input_ in device.inputs.all():
            print('    ' + str(input_))
        for output in device.outputs.all():
            print('    ' + str(output))
            
            
def _show_stations():
    for station in Station.objects.all():
        print(station)
        for sd in station.device_associations.all():
            print('    ', sd)
            for output in sd.device.outputs.all():
                for connection in output.connections.filter(
                        start_time__range=(sd.start_time, sd.end_time)):
                    print('        ', connection)
    

def _show_recordings():
    for recording in Recording.objects.all():
        print(recording)
        
        
def _show_clips():
    for clip in Clip.objects.all():
        annotations = Annotation.objects.filter(clip=clip)
        detector = annotations.get(name='Detector').value
        try:
            selection_start_index = \
                annotations.get(name='Selection Start Index').value
        except Annotation.DoesNotExist:
            selection_start_index = None
            selection_length = None
        else:
            selection_length = annotations.get(name='Selection Length').value
        classification = annotations.get(name='Classification').value
        print('{} {} {} {} {}'.format(
            str(clip), detector, selection_start_index, selection_length,
            classification))
        
        
if __name__ == '__main__':
    _main()
    