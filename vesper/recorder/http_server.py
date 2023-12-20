"""Module containing class `HttpServer`."""


from datetime import datetime as DateTime
from http.server import HTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo

from vesper.util.bunch import Bunch


# TODO: Show configuration error messages in red text on web page.


class HttpServer(HTTPServer):
    
    """Vesper Recorder HTTP server."""
    
    
    def __init__(self, port_num, recorder_version_num, recorder):
        
        address = ('', port_num)
        super().__init__(address, _HttpRequestHandler)
        
        self._recording_data = Bunch(
            recorder_version_num=recorder_version_num,
            recorder=recorder)
       
    
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
                
        status_table = self._create_status_table(recorder, now)
        station_table = self._create_station_table(recorder.station)
        devices = recorder.get_input_devices()
        devices_table = self._create_devices_table(devices, recorder.input)
        input_table = self._create_input_table(devices, recorder.input)
        processor_tables = \
            self._create_processor_tables(recorder.processor_graph)
        schedule_table = self._create_schedule_table(
            recorder.schedule, recorder.station.time_zone, now)
        
        tables = '\n'.join(
            [status_table, station_table, devices_table, input_table] +
            processor_tables +
            [schedule_table])
        
        body = _PAGE.format(_CSS, data.recorder_version_num, tables)
        
        return body.encode()
    
    
    def _create_status_table(self, recorder, now):
        
        time_zone = recorder.station.time_zone
        
        time = _format_datetime(now, time_zone)
        recording = 'Yes' if recorder.recording else 'No'
        
        interval = self._get_status_schedule_interval(recorder.schedule, now)
        
        if interval is None:
            prefix = 'Next'
            start_time = 'None'
            end_time = 'None'
        else:
            start_time = _format_datetime(interval.start, time_zone)
            end_time = _format_datetime(interval.end, time_zone)
            prefix = 'Current' if interval.start <= now else 'Next'
            
        rows = (
            ('Current Time', time),
            ('Recording', recording),
            (prefix + ' Recording Start Time', start_time),
            (prefix + ' Recording End Time', end_time)
        )
        
        return _create_table('Recording Status', rows)
        
        
    def _get_status_schedule_interval(self, schedule, time):
        intervals = schedule.get_intervals(start=time)
        try:
            return next(intervals)
        except StopIteration:
            return None
        
        
    def _create_station_table(self, station):
        rows = (
            ('Station Name', station.name),
            ('Latitude (degrees north)', station.lat),
            ('Longitude (degrees east)', station.lon),
            ('Time Zone', str(station.time_zone)))
        return _create_table('Station', rows)
    
    
    def _create_devices_table(self, devices, input):
        
        if len(devices) == 0:
            header = None
            rows = None
            footer = '<p>No input devices were found.</p>'
        
        else:
            header = ('Name', 'Channel Count')
            selected_device_name = input.input_device_name
            rows = [
                self._create_devices_table_row(d, selected_device_name)
                for d in devices]
            footer = '* Selected input device.'
        
        return _create_table('Available Input Devices', rows, header, footer)

    
    def _create_devices_table_row(self, device, selected_device_name):
        prefix = '*' if device.name == selected_device_name else ''
        return (prefix + device.name, device.input_channel_count)
    
    
    def _create_input_table(self, devices, input):
        
        device_dict = {d.name: d for d in devices}
        device_name = input.input_device_name
        device = device_dict.get(device_name)

        if device is None:
            device_name = \
                f'There is no input device with name {device_name}.'
        else:
            device_name = device.name
            
        rows = (
            ('Device Name', device_name),
            ('Channel Count', input.channel_count),
            ('Sample Rate (Hz)', input.sample_rate),
            ('Buffer Size (seconds)', input.buffer_size)
        )

        return _create_table('Input', rows)
    
    
    def _create_processor_tables(self, processor_graph):
        return [
            _create_table(t.title, t.rows)
            for t in processor_graph.get_status_tables()]


    def _create_schedule_table(self, schedule, time_zone, now):
        rows = [
            self._create_schedule_table_row(index, interval, time_zone, now)
            for index, interval in enumerate(schedule.get_intervals())]
        header = ('Recording', 'Start Time', 'End Time', 'Status')
        return _create_table('Recording Schedule', rows, header)
    
    
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


def _create_table(title, rows, header=None, footer=None):
    title = _create_table_title(title)
    body = _create_table_body(header, rows)
    footer = _create_table_footer(footer)
    return title + body + footer


def _create_table_title(text):
    return f'<h2>{text}</h2>\n'


def _create_table_body(header, rows):

    if header is None and rows is None:
        return ''
    
    else:
        header = _create_table_header(header)
        rows = ''.join(_create_table_row(r) for r in rows)
        return '<table>\n' + header + rows + '</table>\n'


def _create_table_header(items):
    if items is None:
        return ''
    else:
        return _create_table_row(items, 'h')


def _create_table_row(items, tag_letter='d'):
    items = ''.join(_create_table_item(i, tag_letter) for i in items)
    return '  <tr>\n' + items + '  </tr>\n'
    
    
def _create_table_item(item, tag_letter):
    return f'    <t{tag_letter}>{item}</t{tag_letter}>\n'


def _create_table_footer(text):
    if text is None:
        return ''
    else:
        return f'<p>{text}</p>\n'
