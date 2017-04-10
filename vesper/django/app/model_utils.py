"""Utility functions pertaining to models."""


import itertools

from vesper.django.app.models import Processor, StationDevice


def get_station_mic_outputs():
    
    """
    Gets a list of all (station, microphone output) pairs.
    
    The pairs are sorted by the UI names returned for them by
    the `get_station_mic_output_ui_name` function.
    """
    
    station_mic_outputs = _get_station_mic_outputs()
    return sorted(station_mic_outputs, key=get_station_mic_output_ui_name)


def _get_station_mic_outputs():
    
    """Gets an unsorted list of all (station, microphone output) pairs."""
    
    station_mics = StationDevice.objects.filter(
        device__model__type='Microphone')
    
    return list(
        itertools.chain.from_iterable(
            _get_station_mic_outputs_aux(sm) for sm in station_mics))
    
    
def _get_station_mic_outputs_aux(sm):
    
    """
    Gets a list of all (station, microphone output) pairs for one
    station and microphone.
    """
    
    return [(sm.station, output) for output in sm.device.outputs.all()]


def get_station_mic_output_ui_name(station_mic_output):
    
    """Gets the UI name of one (station, microphone output) pair."""
    
    station, mic_output = station_mic_output
    mic_output_name = mic_output.name
    if mic_output_name.endswith(' Output'):
        mic_output_name = mic_output_name[:-len(' Output')]
    return station.name + ' / ' + mic_output_name


def get_station_mic_output_ui_names():
    
    """
    Gets a sorted list of all (station, microphone output) pair UI names.
    """
    
    station_mic_outputs = _get_station_mic_outputs()
    return sorted(
        get_station_mic_output_ui_name(sm) for sm in station_mic_outputs)
    
    
def get_processors(type):
    return Processor.objects.filter(type=type).order_by('name')


def get_processor(name, type):
    return Processor.objects.get(name=name, type=type)
