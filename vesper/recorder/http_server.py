"""Module containing class `HttpServer`."""


from datetime import datetime as DateTime
from http.server import HTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo

from vesper.util.bunch import Bunch


class HttpServer(HTTPServer):
    
    """Vesper Recorder HTTP server."""
    
    
    def __init__(
            self, port_num, recorder_version_num, station, recorder,
            level_meter, local_audio_file_writer):
        
        address = ('', port_num)
        super().__init__(address, _HttpRequestHandler)
        
        self._recording_data = Bunch(
            recorder_version_num=recorder_version_num,
            station=station,
            recorder=recorder,
            level_meter=level_meter,
            local_audio_file_writer=local_audio_file_writer)
        
    
_PAGE = '''<!DOCTYPE html>
<html>
<head>
<title>Vesper Recorder</title>
{}
</head>
<body>

<h1>Vesper Recorder {}</h1>

<p>
Welcome to the Vesper Recorder! This page displays recorder status.
Refresh the page to update the status.
</p>

<h2>Recording Status</h2>
{}

<h2>Station</h2>
{}

<h2>Available Input Devices</h2>
{}

<h2>Input</h2>
{}

<h2>Local Recording</h2>
{}

<h2>Recording Schedule</h2>
{}

</body>
</html>
'''


_CSS = '''
<style>
h2 {
    margin-top: 30px;
    margin-bottom: 5px;
}
table {
    border-collapse: collapse;
    width: 600px;
}
td, th {
    border: 1px solid #a0a0a0;
    text-align: left;
    padding: 8px;
}
tr:nth-child(even) {
    background-color: #d0d0d0;
}
</style>
'''
        
        
class _HttpRequestHandler(BaseHTTPRequestHandler):
    
    
    def do_GET(self):
        
        if self.path == '/':
            body = self._create_status_page_body()
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(body)
            
        else:
            self.send_response(404, 'Not Found')
            self.end_headers()
                    
        
    def _create_status_page_body(self):
        
        data = self.server._recording_data
        recorder = data.recorder
        now = DateTime.now(tz=ZoneInfo('UTC'))
                
        status_table = self._create_status_table(data, recorder, now)
        station_table = self._create_station_table(data)
        devices = recorder.get_input_devices()
        devices_table = self._create_devices_table(devices)
        input_table = self._create_input_table(devices, recorder)
        local_recording_table = \
            self._create_local_recording_table(data.local_audio_file_writer)
        schedule_table = self._create_schedule_table(
            recorder.schedule, data.station.time_zone, now)
        
        body = _PAGE.format(
            _CSS, data.recorder_version_num, status_table, station_table,
            devices_table, input_table, local_recording_table,
            schedule_table)
        
        return body.encode()
    
    
    def _create_status_table(self, data, recorder, now):
        
        time_zone = data.station.time_zone
        
        time = _format_datetime(now, time_zone)
        recording = 'Yes' if recorder.recording else 'No'
        
        value_suffix = '' if recorder.channel_count == 1 else 's'
        level_meter = data.level_meter
        if level_meter is not None:
            rms_values = _format_levels(level_meter.rms_values)
            peak_values = _format_levels(level_meter.peak_values)
        
        interval = self._get_status_schedule_interval(recorder.schedule, now)
        
        if interval is None:
            prefix = 'Next'
            start_time = 'None'
            end_time = 'None'
        else:
            start_time = _format_datetime(interval.start, time_zone)
            end_time = _format_datetime(interval.end, time_zone)
            prefix = 'Current' if interval.start <= now else 'Next'
            
        if level_meter is None:
            level_meter_rows = ()
        else:
            level_meter_rows = (
                (f'Recent RMS Sample Value{value_suffix} (dBFS)', rms_values),
                (f'Recent Peak Sample Value{value_suffix} (dBFS)', peak_values)
            )

        rows = (
            ('Current Time', time),
            ('Recording', recording)
        ) + level_meter_rows + (
            (prefix + ' Recording Start Time', start_time),
            (prefix + ' Recording End Time', end_time)
        )
        
        return _create_table(rows)
        
        
    def _get_status_schedule_interval(self, schedule, time):
        intervals = schedule.get_intervals(start=time)
        try:
            return next(intervals)
        except StopIteration:
            return None
        
        
    def _create_station_table(self, data):
        station = data.station
        rows = (
            ('Station Name', station.name),
            ('Latitude (degrees north)', station.lat),
            ('Longitude (degrees east)', station.lon),
            ('Time Zone', str(station.time_zone)))
        return _create_table(rows)
    
    
    def _create_devices_table(self, devices):
        
        if len(devices) == 0:
            return '<p>No input devices were found.</p>'
        
        else:
            recorder = self.server._recording_data.recorder
            selected_device_name = recorder.input_device_name
            rows = [
                self._create_devices_table_row(d, selected_device_name)
                for d in devices]
            header = ('Name', 'Channel Count')
            table = _create_table(rows, header)
            table += '<p>* Selected input device.</p>'
            return table

    
    def _create_devices_table_row(self, device, selected_device_name):
        prefix = '*' if device.name == selected_device_name else ''
        return (prefix + device.name, device.input_channel_count)
    
    
    def _create_input_table(self, devices, recorder):
        
        device_dict = {d.name: d for d in devices}
        device_name = recorder.input_device_name
        device = device_dict.get(device_name)

        if device is None:
            device_name = \
                f'There is no input device with name {device_name}.'
        else:
            device_name = device.name
            
        rows = (
            ('Device Name', device_name),
            ('Channel Count', recorder.channel_count),
            ('Sample Rate (Hz)', recorder.sample_rate),
            ('Buffer Size (seconds)', recorder.buffer_size)
        )
        return _create_table(rows)
    
    
    def _create_local_recording_table(self, local_audio_file_writer):
        writer = local_audio_file_writer
        if writer is None:
            rows = (('Enabled', 'No'),)
        else:
            recording_dir_path = writer.recording_dir_path.absolute()
            rows = (
                ('Enabled', 'Yes'),
                ('Recording Directory', recording_dir_path),
                ('Max Audio File Duration (seconds)', writer.max_file_duration)
            )
        return _create_table(rows)


    def _create_schedule_table(self, schedule, time_zone, now):
        rows = [
            self._create_schedule_table_row(index, interval, time_zone, now)
            for index, interval in enumerate(schedule.get_intervals())]
        header = ('Recording', 'Start Time', 'End Time', 'Status')
        return _create_table(rows, header)
    
    
    def _create_schedule_table_row(self, index, interval, time_zone, now):
        start_time = _format_datetime(interval.start, time_zone)
        end_time = _format_datetime(interval.end, time_zone)
        if now > interval.end:
            status = 'Past'
        elif now < interval.start:
            status = 'Future'
        else:
            status = 'Current'
        return (index, start_time, end_time, status)
        
        
def _format_datetime(dt, time_zone=None):
    if time_zone is not None:
        dt = dt.astimezone(time_zone)
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def _format_levels(levels):
    if levels is None:
        return '-'
    else:
        levels = [f'{l:.2f}' for l in levels]
        return ', '.join(levels)


def _create_table(rows, header=None):
    header = _create_table_header(header)
    rows = ''.join(_create_table_row(r) for r in rows)
    return '<table>\n' + header + rows + '</table>\n'


def _create_table_header(items):
    return _create_table_row(items, 'h') if items is not None else ''


def _create_table_row(items, tag_letter='d'):
    items = ''.join(_create_table_item(i, tag_letter) for i in items)
    return '  <tr>\n' + items + '  </tr>\n'
    
    
def _create_table_item(item, tag_letter):
    return f'    <t{tag_letter}>{item}</t{tag_letter}>\n'
