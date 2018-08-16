"""Creates an archive data YAML file from a stations CSV file."""


from collections import Counter, defaultdict
from pathlib import Path
import textwrap

from vesper.util.bunch import Bunch


WORKING_DIR_PATH = Path(
    '/Users/Harold/Desktop/NFC/Data/MPG Ranch/2018 MPG Ranch Archive/'
    'Archive Data YAML')

CSV_FILE_PATH = WORKING_DIR_PATH / 'Stations 2018.csv'
ARCHIVE_DATA_FILE_PATH = WORKING_DIR_PATH / 'Archive Data.yaml'
ALIASES_FILE_PATH = WORKING_DIR_PATH / 'Station Name Aliases.yaml'


sn_counts = Counter()
"""Counts of generated serial numbers by device model name."""
    

def main():
    create_archive_data_yaml()
    create_station_name_aliases_preset()
    
    
def create_archive_data_yaml():
    
    lines = parse_csv_file()
    
    text = '\n'.join([
        create_stations_section(lines),
        create_device_models_section(),
        create_devices_section(lines),
        create_station_devices_section(lines),
        create_processor_sections(),
        create_annotation_sections()
    ])
    
    with open(ARCHIVE_DATA_FILE_PATH, 'wt') as yaml_file:
        yaml_file.write(text)
    
    
def parse_csv_file():
    
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as csv_file:
        lines = csv_file.read().strip().split('\n')[1:]
    
    return [parse_csv_file_line(l) for l in lines]
    
    
def parse_csv_file_line(line):
    
    (station_name, _, recorder_model, recorder_sn, microphone_sn, latitude,
     longitude, elevation, station_name_alias) = line.split(',')
    
    if recorder_model == 'SM2':
        recorder_model = 'SM2+'
        
    if recorder_sn == '':
        recorder_sn = create_sn(recorder_model)
        
    microphone_model = '21c'
    
    if microphone_sn == '':
        microphone_sn = create_sn(microphone_model)
        
    return Bunch(
        station_name=station_name,
        station_name_alias=station_name_alias,
        description='',
        time_zone='US/Mountain',
        latitude=latitude,
        longitude=longitude,
        elevation=elevation,
        recorder_model=recorder_model,
        recorder_sn=recorder_sn,
        microphone_model=microphone_model,
        microphone_sn=microphone_sn)
    
    
def create_sn(device_model):
    sn = 'PH{:02d}'.format(sn_counts[device_model])
    sn_counts[device_model] += 1
    return sn
    
    
def create_stations_section(lines):
    items = create_station_items(lines)
    return create_section('stations', items)


def create_station_items(lines):
    
    # Eliminate station duplicates and sort by name.
    stations_dict = dict((l.station_name, l) for l in lines)
    names = sorted(stations_dict.keys())
    stations = [stations_dict[n] for n in names]
    
    return [create_station_item(s) for s in stations]
        
        
def create_station_item(s):
    
    f = '''
- name: {}
  description: {}
  time_zone: {}
  latitude: {}
  longitude: {}
  elevation: {}
'''.lstrip()

    return f.format(
        s.station_name, q(s.description), s.time_zone, s.latitude,
        s.longitude, s.elevation)
    
    
def q(s):
    return s if len(s) != 0 else '""'
                          

def create_section(title, items):
    return title + ':\n\n' + indent('\n'.join(items))
     

def indent(text, num_spaces=4):
    prefix = ' ' * num_spaces
    return textwrap.indent(text, prefix)
    
    
def create_device_models_section():
    
    return '''
device_models:

    - name: SM2+
      type: Audio Recorder
      manufacturer: Wildlife Acoustics
      model: Song Meter SM2+
      description: ""
      num_inputs: 2
      
    - name: SM3
      type: Audio Recorder
      manufacturer: Wildlife Acoustics
      model: Song Meter SM3
      description: ""
      num_inputs: 2

    - name: Swift
      type: Audio Recorder
      manufacturer: Cornell Lab of Ornithology
      model: Swift
      description: ""
      num_inputs: 1

    - name: PC
      type: Audio Recorder
      manufacturer: Various
      model: PC
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
'''.lstrip()


def create_devices_section(lines):
    recorder_items = create_recorder_items(lines)
    microphone_items = create_microphone_items(lines)
    return create_section('devices', recorder_items + microphone_items)


def create_recorder_items(lines):
    
    recorders = sorted(set(
        [(l.recorder_model, l.recorder_sn) for l in lines]))
    
    return [create_device_item(*r) for r in recorders]


def create_device_item(model, sn):
    
    name = '{} {}'.format(model, sn)
    
    return '''
- name: {}
  model: {}
  serial_number: {}
  description: ""
'''.lstrip().format(name, model, sn)
    
    
def create_microphone_items(lines):
    
    microphones = sorted(set(
        [(l.microphone_model, l.microphone_sn) for l in lines]))
    
    return [create_device_item(*m) for m in microphones]
    
    
def create_station_devices_section(lines):
    
    # Collect device connections by station.
    connections = defaultdict(set)
    for l in lines:
        recorder_name = create_device_name(l.recorder_model, l.recorder_sn)
        microphone_name = create_device_name(
            l.microphone_model, l.microphone_sn)
        connections[l.station_name].add((recorder_name, microphone_name))
    
    # Create station devices items, one for each station.
    station_names = sorted(connections.keys())
    items = [
        create_station_devices_item(station_name, connections[station_name])
        for station_name in station_names]
        
    return create_section('station_devices', items)
    
        
def create_device_name(model, sn):
    return '{} {}'.format(model, sn)


def create_station_devices_item(station_name, connections):
    
    header = '''
- station: {}
  start_time: 2018-01-01
  end_time: 2019-01-01
'''.lstrip().format(station_name)

    connections = sorted(connections)
    device_list = create_device_list(connections)
    connection_list = create_connection_list(connections)
    
    return header + indent(device_list, 2) + indent(connection_list, 2)
  
    
def create_device_list(connections):
    recorder_names = sorted(set([c[0] for c in connections]))
    microphone_names = sorted(set([c[1] for c in connections]))
    device_names = recorder_names + microphone_names
    device_items = ['- ' + n + '\n' for n in device_names]
    return create_list('devices', device_items)


def create_list(name, items):
    return name + ':\n' + indent(''.join(items))


def create_connection_list(connections):
    connection_items = [create_connection_item(*c) for c in connections]
    return create_list('connections', connection_items)


def create_connection_item(recorder_name, microphone_name):
    
    output_name = microphone_name + ' Output'
    
    # Get channel number text for recorder input name.
    if recorder_name.startswith('Swift'):
        channel_num = ''
    elif recorder_name.startswith('SM3'):
        channel_num = ' 1'
    else:
        channel_num = ' 0'

    input_name = recorder_name + ' Input' + channel_num
    
    return '''
- output: {}
  input: {}
'''.lstrip().format(output_name, input_name)


def create_processor_sections():
    
    return '''
detectors:

    - name: Old Bird Thrush Detector Redux 1.1
      description: Vesper reimplementation of Old Bird Thrush detector.

    - name: Old Bird Tseep Detector Redux 1.1
      description: Vesper reimplementation of Old Bird Tseep detector.

classifiers:

    - name: MPG Ranch Outside Classifier 1.0
      description: >
          Classifies a clip as "Outside" if and only if its start time is
          outside of the interval from one hour after sunset to one half
          hour before sunrise.

    - name: MPG Ranch NFC Coarse Classifier 2.0
      description: >
          Classifies an unclassified clip as a "Call" if it appears to be
          a nocturnal flight call, or as a "Noise" otherwise. Does not
          classify a clip that has already been classified, whether
          manually or automatically.
'''.lstrip()


def create_annotation_sections():
    
    return '''
annotation_constraints:

    - name: Coarse Classification
      description: Coarse classifications only.
      type: Values
      values: 
          - CHSP_DEJU
          - Call
          - Noise
          - Other
          - Outside
          - Thrush
          - Tone
          - Tseep
          - Unknown
          
    - name: Classification
      description: All classifications, including call subclassifications.
      type: Hierarchical Values
      extends: Coarse Classification
      values:
          - Call: 
              - AMPI
              - AMRE
              - AMRO
              - ATSP
              - BAIS
              - CAWA
              - CCSP_BRSP
              - CHSP
              - COYE
              - CSWA
              - DBUP
              - DEJU
              - GCKI
              - GCTH
              - GRSP
              - GRYE
              - HETH
              - LALO
              - LAZB
              - LCSP
              - LESA
              - LISP
              - MGWA
              - NOWA
              - OCWA
              - OVEN
              - PESA
              - SAVS
              - SNBU
              - SORA
              - SOSP
              - SPSA_SOSA
              - SWSP
              - SWTH
              - UPSA
              - Unknown
              - VEER
              - VESP
              - VIRA
              - WCSP
              - WIWA
              - WTSP
              - Weak
              - YRWA
              - YEWA
              - Zeep
annotations:

    - name: Classification
      type: String
      constraint: Classification
'''.lstrip()


def create_station_name_aliases_preset():
    
    comment = '''
# A station name aliases preset is a mapping from station names as they appear
# in an archive to lists of aliases for them that appear in recording and clip
# file names. The archive station names should be capitalized exactly they are
# in the archive. The capitalization of aliases is irrelevant since they and
# station names that appear in file names are converted to lower case before
# comparison.
'''.lstrip()

    lines = parse_csv_file()
    lines.sort(key=lambda l: l.station_name)
    
    aliases = []
    for line in lines:
        name = line.station_name
        alias = line.station_name_alias.lower()
        if alias != '' and name.lower() != alias:
            aliases.append('{}: [{}]\n'.format(name, alias))
            
    text = comment + '\n' + ''.join(aliases)
            
    with open(ALIASES_FILE_PATH, 'wt') as aliases_file:
        aliases_file.write(text)


if __name__ == '__main__':
    main()
