"""
Creates a Vesper web app archive data template from a Vesper desktop archive.
"""


from collections import defaultdict

from vesper.archive.archive import Archive
from vesper.util.bunch import Bunch


_ARCHIVE_DIR_PATH = r'E:\2015_NFC_Archive'
_STATION_DEVICE_START_TIME = '2015-01-01'
_STATION_DEVICE_END_TIME = '2016-01-01'
# _ARCHIVE_DIR_PATH = r'E:\2016_Archive'
# _STATION_DEVICE_START_TIME = '2016-01-01'
# _STATION_DEVICE_END_TIME = '2017-01-01'


# The name of a station's time zone is not available from a `Station`
# instance. We assume that all the stations of an archive are in the
# time zone specified here.
_STATION_TIME_ZONE_NAME = 'US/Mountain'

_DEVICE_MODELS = '''
device_models:

    - name: SM2+
      type: Audio Recorder
      manufacturer: Wildlife Acoustics
      model: Song Meter SM2+
      description: ""
      num_inputs: 2
      
    - name: PC Recorder
      type: Audio Recorder
      manufacturer: Various
      model: Various
      description: Personal computer as an audio recorder.
      num_inputs: 2
      
    - name: SMX-NFC
      type: Microphone
      manufacturer: Wildlife Acoustics
      model: SMX-NFC
      description: ""
      num_outputs: 1
      
    - name: SMX-II
      type: Microphone
      manufacturer: Wildlife Acoustics
      model: SMX-II
      description: ""
      num_outputs: 1
      
    - name: 21c
      type: Microphone
      manufacturer: Old Bird
      model: 21c
      description: ""
      num_outputs: 1
'''.strip('\n')

_DEFAULT_RECORDER_MODEL = 'SM2+'

_STATION_RECORDERS = {
    'Darby': 'PC Recorder',
    'Florence': 'PC Recorder',
}

_MIC_NAME_CORRECTIONS = {
    'NFC': 'SMX-NFC'
}

_DEVICE_TEMPLATE = '''
    - name: {}
      model: {}
      serial_number: {}
      description: >
          {} used at {} station.
          Serial number is a fake placeholder.
'''.strip('\n')
    
_MIC_CHANNEL_NUMS = {
    'SMX-NFC': 0,
    '21c': 1
}

# _PROCESSORS = '''
# algorithms:
# 
#     - name: Old Bird Tseep Detector
#       type: Detector
#       description: http://oldbird.org/analysis.htm
# 
#     - name: Old Bird Thrush Detector
#       type: Detector
#       description: http://oldbird.org/analysis.htm
# 
# algorithm_versions:
# 
#     - algorithm: Old Bird Tseep Detector
#       version: 1.0
# 
#     - algorithm: Old Bird Thrush Detector
#       version: 1.0
# 
# processors:
# 
#     - name: Old Bird Tseep
#       algorithm_version: Old Bird Tseep Detector 1.0
# 
#     - name: Old Bird Thrush
#       algorithm_version: Old Bird Thrush Detector 1.0
# '''.strip('\n')

_PROCESSORS = '''
detectors:

    - name: Old Bird Tseep
      description: http://oldbird.org/analysis.htm
      
    - name: Old Bird Thrush
      description: http://oldbird.org/analysis.htm

classifiers:

    - name: MPG Ranch Outside 1.0
      description: >
          Classifies a clip as "Outside" if and only if its start time is
          outside of the interval from one hour after sunset to one half
          hour before sunrise.

    - name: MPG Ranch Coarse 1.0
      description: >
          Classifies a clip as "Call" or "Noise" if and only if it is not
          yet classified. The classifier is an SVM trained on MPG Ranch
          clips from 2012-2014. Different SVMs are used for clips detected
          by the Old Bird Tseep and Old Bird Thrush detectors.

    - name: MPG Ranch Species 1.0
      description: >
          Classifies some "Call" clips to species (more documentation needed).
'''.STRIP('\n')

_ANNOTATIONS = '''
annotation_constraints:

    - name: Coarse Classification
      description: Coarse classifications only.
      type: Values
      values: {}
          
    - name: Classification
      description: All classifications, including call subclassifications.
      type: Hierarchical Values
      extends: Coarse Classification
      values:
          - Call: {}

annotations:

    - name: Classification
      type: String
      constraint: Classification
'''.strip('\n')


def _main():
    
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open()
    
    station_mics = _print_stations(archive)
    
    print()
    
    _print_device_models()
    
    print()
    
    devices = _create_devices(station_mics)
    
    _print_devices(devices)
    
    print()
    
    _print_station_devices(devices)
    
    print()
    
    _print_processors()
    
    print()
    
    _print_annotations(archive)
    
    archive.close()


def _print_stations(archive):
    
    stations = archive.stations
    
    print('stations:')
    
    station_names = set()
    station_mics = defaultdict(set)
    
    for station in stations:
        
#         night_counts = archive.get_clip_counts(station_name=station.name)
#         total_num_clips = sum(night_counts.values())

        # We assume here that the desktop archive contains a station for
        # each station/mic combo, and that the mic name is at the end of
        # the station name.
        station_name, mic_name = station.name.rsplit(maxsplit=1)
        
        mic_name = _MIC_NAME_CORRECTIONS.get(mic_name, mic_name)
        station_mics[station_name].add(mic_name)
            
        if station_name not in station_names:
            # haven't seen this station before
            
            if len(station.long_name) != 0:
                description = station.long_name
            else:
                description = '""'
    
            print()
            print('    - name: {}'.format(station_name))
            print('      description: {}'.format(description))
            print('      time_zone: {}'.format(_STATION_TIME_ZONE_NAME))
            print('      latitude: {:.5f}'.format(station.latitude))
            print('      longitude: {:.5f}'.format(station.longitude))
            print('      elevation: {:.1f}'.format(station.elevation))
            
            station_names.add(station_name)
        
    return station_mics


def _print_device_models():
    print(_DEVICE_MODELS)
    
    
def _create_devices(station_mics):
    station_names = sorted(station_mics.keys())
    recorders = _create_recorders(station_names)
    mics = _create_mics(station_mics)
    return recorders + mics


def _create_recorders(station_names):
    
    # Get mapping from station names to recorder model names.
    station_models = _get_station_recorder_models(station_names)
    
    # Get mapping from recorder model names to sets of station names.
    model_stations = defaultdict(set)
    for station_name, model_name in station_models.items():
        model_stations[model_name].add(station_name)
        
    return _create_station_devices(model_stations, 'Recorder')
    
    
def _get_station_recorder_models(station_names):
    return dict(
        (name, _get_station_recorder_model(name))
        for name in station_names)


def _get_station_recorder_model(station_name):
    return _STATION_RECORDERS.get(station_name, _DEFAULT_RECORDER_MODEL)


def _create_station_devices(model_stations, device_type):
    
    devices = []
    
    model_names = sorted(model_stations.keys())
    
    for model_name in model_names:
        
        station_names = sorted(model_stations[model_name])
        
        for serial_num, station_name in enumerate(station_names):
            
            name = '{} {}'.format(model_name, serial_num)
            
            device = Bunch(
                name=name,
                model_name=model_name,
                serial_num=serial_num,
                station_name=station_name,
                type=device_type)
            
            devices.append(device)
            
    return devices
            

def _create_mics(station_mics):
    
    # Get mapping from microphone model names to sets of station names.
    model_stations = defaultdict(set)
    for station_name, model_names in station_mics.items():
        for model_name in model_names:
            model_stations[model_name].add(station_name)
            
    return _create_station_devices(model_stations, 'Microphone')


def _print_devices(devices):
    
    print('devices:')
    
    for device in devices:
        _print_device(device)
    
    
def _print_device(d):
    
    print()
    
    print(
        _DEVICE_TEMPLATE.format(
            d.name, d.model_name, d.serial_num, d.type, d.station_name))
    
    
def _print_station_devices(devices):
    
    print('station_devices:')
    
    # Get mapping from station names to lists of devices.
    station_devices = defaultdict(list)
    for device in devices:
        station_devices[device.station_name].append(device)
        
    station_names = sorted(station_devices.keys())
    
    for station_name in station_names:
        
        devices = station_devices[station_name]
        
        print()
        _print_station_devices_aux(station_name, devices)

        
# Device assumptions:
#
#     * Each station has the same devices connected in the same way
#       throughout the period of the archive.
#
#     * Each station has only one recorder.
#
#     * If a station has only one microphone, it is connected to
#       recorder channel zero.
#
#     * If a station has more than one microphone, the microphones are
#       connected to the recorder channel numbers indicated by
#       _MIC_CHANNEL_NUMS.
#
#     * Each microphone has one output.

def _print_station_devices_aux(station_name, devices):
    
    print('    - station: ' + station_name)
    print('      start_time: ' + _STATION_DEVICE_START_TIME)
    print('      end_time: ' + _STATION_DEVICE_END_TIME)
    
    print('      devices:')
    for device in devices:
        print('          - ' + device.name)
        
    recorder = _get_recorder(devices)
    mics = _get_mics(devices)
    
    print('      connections:')
    for mic, channel_num in mics:
        print('          - output: {} Output'.format(mic.name))
        print(
            '            input: {} Input {}'.format(recorder.name, channel_num))
    
    
def _get_recorder(devices):
    for device in devices:
        if device.type == 'Recorder':
            return device
    raise ValueError('Could not find recorder.')


def _get_mics(devices):
    mics = [d for d in devices if d.type == 'Microphone']
    num_mics = len(mics)
    pairs = [(m, _get_mic_channel_num(m, num_mics)) for m in mics]
    pairs.sort(key=lambda pair: pair[1])
    return pairs


def _get_mic_channel_num(mic, num_mics):
    if num_mics == 1:
        return 0
    elif num_mics == 2:
        return _MIC_CHANNEL_NUMS[mic.model_name]
    else:
        raise ValueError(
            'Unexpected number of microphones {}.'.format(num_mics))
    
    
def _print_processors():
    print(_PROCESSORS)
    
    
# Annotation assumptions:
#
# * Only annotation is a string annotation named "Classification".
#
# * Classification hierarchy has only two levels.
#
# * Only coarse class with internal structure is the "Call" class.


def _print_annotations(archive):
    
    classes = archive.clip_classes
    
    coarse_classes = [c for c in classes if '.' not in c.name]
    coarse_classes.sort(key=lambda c: c.name)
    coarse_classes_yaml = _get_list_yaml(coarse_classes, _get_coarse_class_yaml)
    
    call_classes = [c for c in classes if '.' in c.name]
    call_classes.sort(key=lambda c: c.name)
    call_classes_yaml = _get_list_yaml(call_classes, _get_call_class_yaml)
    
    print(_ANNOTATIONS.format(coarse_classes_yaml, call_classes_yaml))
    
    
def _get_list_yaml(classes, get_item_yaml):
    lines = [get_item_yaml(c) for c in classes]
    return ''.join(lines)


def _get_coarse_class_yaml(c):
    return '\n          - ' + c.name


def _get_call_class_yaml(c):
    return '\n              - ' + c.name[5:]


if __name__ == '__main__':
    _main()
    