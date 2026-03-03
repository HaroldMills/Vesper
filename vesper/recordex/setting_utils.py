from zoneinfo import ZoneInfo

from vesper.recorder.settings import Settings
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule


_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_STATION_LATITUDE = None
_DEFAULT_STATION_LONGITUDE = None
_DEFAULT_STATION_TIME_ZONE = 'UTC'
_DEFAULT_SCHEDULE = {}
_DEFAULT_SERVER_PORT_NUM = 8001
_DEFAULT_STOP_TIMEOUT = 5

_LOGGING_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

_PROCESSOR_CLASSES = ()
_SIDECAR_CLASSES = ()


def parse_settings_file(settings_file_path):

    # Check that settings file exists.
    if not settings_file_path.exists():
        raise Exception(
            f'Recorder settings file "{settings_file_path}" does not exist.')
        
    # Parse settings file.
    try:
        return _parse_settings_file_aux(settings_file_path)
    except Exception as e:
        raise Exception(
            f'Could not parse recorder settings file '
            f'"{settings_file_path}". Error message was: {e}')
    

def _parse_settings_file_aux(settings_file_path):
    
    settings = Settings.create_from_yaml_file(settings_file_path)

    logging_level = _parse_logging_level_setting(settings)
    station = _parse_station_settings(settings)
    schedule = _parse_schedule_settings(settings, station)
    run_duration = _parse_run_duration_settings(settings)
    input = _parse_input_settings(settings)
    processors = _parse_processor_settings(settings)
    sidecars = _parse_sidecar_settings(settings)

    server_port_num = int(settings.get(
        'server_port_num', _DEFAULT_SERVER_PORT_NUM))

    stop_timeout = float(settings.get(
        'stop_timeout', _DEFAULT_STOP_TIMEOUT))

    return Bunch(
        logging_level=logging_level,
        station=station,
        schedule=schedule,
        run_duration=run_duration,
        input=input,
        processors=processors,
        sidecars=sidecars,
        server_port_num=server_port_num,
        stop_timeout=stop_timeout)


def _parse_logging_level_setting(settings):
    value = settings.get('logging_level')
    if value is not None:
        Settings.check_enum_value(
            value, _LOGGING_LEVELS, 'recorder logging level')
    return value


def _parse_station_settings(settings):

    name = settings.get('station.name', _DEFAULT_STATION_NAME)
    lat = settings.get('station.latitude', _DEFAULT_STATION_LATITUDE)
    lon = settings.get('station.longitude', _DEFAULT_STATION_LONGITUDE)
    time_zone = ZoneInfo(
        settings.get('station.time_zone', _DEFAULT_STATION_TIME_ZONE))
    
    return Bunch(
        name=name,
        lat=lat,
        lon=lon,
        time_zone=time_zone)
        

def _parse_schedule_settings(settings, station):

    schedule_dict = settings.get('schedule', _DEFAULT_SCHEDULE)

    return Schedule.compile_dict(
        schedule_dict, latitude=station.lat, longitude=station.lon,
        time_zone=station.time_zone)
    

def _parse_run_duration_settings(settings):

    value = settings.get('run_duration', None)

    if value is None:
        return value

    def handle_bad_value():
        raise ValueError(
            f'Bad value "{value}" for "run_duration" setting. Value '
            f'must be of the form "<number> <units>" where <number> '
            f'is a nonnegative number and <units> is "days", "hours", '
            f'"minutes", "seconds", or the singular of one of those.')

    if not isinstance(value, str):
        handle_bad_value()

    parts = value.split()

    if len(parts) != 2:
        handle_bad_value()
    
    number, units = parts

    try:
        number = float(number)
    except ValueError:
        handle_bad_value()

    if number < 0:
        handle_bad_value()

    match units:
        case 'days':
            unit_size = 24 * 3600
        case 'day':
            unit_size = 24 * 3600
        case 'hours':
            unit_size = 3600
        case 'hour':
            unit_size = 3600
        case 'minutes':
            unit_size = 60
        case 'minute':
            unit_size = 60
        case 'seconds':
            unit_size = 1
        case 'second':
            unit_size = 1
        case _:
            handle_bad_value()

    return number * unit_size


def _parse_input_settings(settings):
    return Bunch()
    # mapping = settings.get_required('input')
    # settings = Settings(mapping)
    # return AudioInput.parse_settings(settings)


def _parse_processor_settings(settings):

    processor_classes = {cls.type_name: cls for cls in _PROCESSOR_CLASSES}

    settings = settings.get_required('processors')

    return [
        _parse_processor_settings_aux(s, processor_classes)
        for s in settings]


def _parse_processor_settings_aux(mapping, processor_classes):

    settings = Settings(mapping)

    name = settings.get_required('name')
    type = settings.get_required('type')
    input = settings.get_required('input')
    mapping = settings.get('settings', {})

    try:
        cls = processor_classes[type]
    except KeyError:
        raise ValueError(f'Unrecognized processor type "{type}".')
    
    settings = cls.parse_settings(Settings(mapping))

    return Bunch(
        name=name,
        type=type,
        input=input,
        settings=settings)


def _parse_sidecar_settings(settings):

    sidecar_classes = {cls.type_name: cls for cls in _SIDECAR_CLASSES}

    settings = settings.get('sidecars')

    if settings is None:
        return []
    
    else:
        return [
            _parse_sidecar_settings_aux(s, sidecar_classes)
            for s in settings]


def _parse_sidecar_settings_aux(mapping, sidecar_classes):

    settings = Settings(mapping)

    name = settings.get_required('name')
    type = settings.get_required('type')
    mapping = settings.get('settings', {})

    try:
        cls = sidecar_classes[type]
    except KeyError:
        raise ValueError(f'Unrecognized sidecar type "{type}".')
    
    settings = cls.parse_settings(Settings(mapping))

    return Bunch(name=name, type=type, settings=settings)
