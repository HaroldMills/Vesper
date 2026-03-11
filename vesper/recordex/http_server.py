"""Module containing class `HttpServer`."""


from datetime import datetime as DateTime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from zoneinfo import ZoneInfo
import itertools

from vesper.recordex import __version__
from vesper.util.bunch import Bunch


# TODO: Show configuration error messages in red text on web page.


class HttpServer(HTTPServer):
    
    """
    Vesper Recorder HTTP server.

    The server serves a single HTML recorder status page.
    """
    
    
    def __init__(self, port_num, recorder_process):
        
        address = ('', port_num)
        super().__init__(address, _HttpRequestHandler)
        
        self._recorder_process = recorder_process
       
    
_PAGE = '''<!DOCTYPE html>
<html>
<head>
<title>Vesper Recorder</title>
<script src="/web/js/htmx.min.js"></script>
{}
</head>
<body>

<h1>Vesper Recorder {}</h1>

<p>
Welcome to the Vesper Recorder! This page displays recorder status.
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
        
        # TODO: Consider factoring out common response code from the
        # following.

        if self.path == '/':
            body = self._create_status_page_body()
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(body)
            
        elif self.path == '/status/current-time':
            recorder = self.server._recorder_process
            now = DateTime.now(tz=ZoneInfo('UTC'))
            result = _format_datetime(now, recorder.station.time_zone)
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(result.encode())
            
        elif self.path == '/status/recording':
            recorder = self.server._recorder_process
            result = 'Yes' if recorder.recording else 'No'
            self.send_response(200, 'OK')
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(result.encode())
        
        # TODO: Consider making this work for any file in the `web`
        # subdirectory.
        elif self.path == '/web/js/htmx.min.js':
            htmx_path = Path(__file__).parent / 'web' / 'js' / 'htmx.min.js'
            try:
                body = htmx_path.read_bytes()
                self.send_response(200, 'OK')
                self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404, 'Not Found')
                self.end_headers()
            
        else:
            self.send_response(404, 'Not Found')
            self.end_headers()
                    
        
    def _create_status_page_body(self):
        
        recorder = self.server._recorder_process

        now = DateTime.now(tz=ZoneInfo('UTC'))
                
        status_table = self._create_recording_status_table(recorder, now)
        station_table = self._create_station_table(recorder.station)
        # input_tables = self._create_input_tables(recorder.input)
        # processor_tables = \
        #     self._create_processor_tables(recorder.processor_graph)
        # sidecar_tables = self._create_sidecar_tables(recorder.sidecars)
        schedule_table = self._create_schedule_table(
            recorder.schedule, recorder.station.time_zone)
        
        tables = '\n'.join([status_table, station_table, schedule_table])
        # tables = '\n'.join(
        #     [status_table, station_table] + input_tables + processor_tables +
        #     sidecar_tables + [schedule_table])

        body = _PAGE.format(_CSS, __version__, tables)
        
        return body.encode()
    
    
    def _create_recording_status_table(self, recorder, now):
        
        time_zone = recorder.station.time_zone
        
        value = _format_datetime(now, time_zone)
        time = (
            f'<span hx-get="/status/current-time" hx-trigger="every 1s">'
            f'{value}</span>')
        
        recorder_start_time = _format_datetime(recorder.start_time, time_zone)

        if recorder.quit_time is None:
            recorder_quit_time = 'None'
        else:
            recorder_quit_time = \
                _format_datetime(recorder.quit_time, time_zone)

        value = 'Yes' if recorder.recording else 'No'
        recording = (
            f'<span hx-get="/status/recording" hx-trigger="every 1s">'
            f'{value}</span>')
        
        # interval = self._get_status_schedule_interval(recorder.schedule, now)
        
        # if interval is None:
        #     prefix = 'Next'
        #     recording_start_time = 'None'
        #     recording_end_time = 'None'
        # else:
        #     prefix = 'Current' if interval.start <= now else 'Next'
        #     recording_start_time = _format_datetime(interval.start, time_zone)
        #     recording_end_time = _format_datetime(interval.end, time_zone)
            
        rows = (
            ('Current Time', time),
            ('Recorder Start Time', recorder_start_time),
            ('Recorder Quit Time', recorder_quit_time),
            ('Recording', recording),
            # (prefix + ' Scheduled Recording Start Time', recording_start_time),
            # (prefix + ' Scheduled Recording End Time', recording_end_time)
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
    
    
    def _create_input_tables(self, input):
        return _create_tables(input.get_status_tables())


    def _create_processor_tables(self, processor_graph):
        tables = processor_graph.get_status_tables()
        return _create_tables(tables)


    def _create_sidecar_tables(self, sidecars):
        table_lists = [s.get_status_tables() for s in sidecars]
        chain = itertools.chain.from_iterable
        tables = list(chain(table_lists))
        return _create_tables(tables)
    

    def _create_schedule_table(self, schedule, time_zone):
        rows = [
            self._create_schedule_table_row(index, interval, time_zone)
            for index, interval in enumerate(schedule.get_intervals())]
        header = ('Recording', 'Start Time', 'End Time')
        return _create_table('Recording Schedule', rows, header)
    
    
    def _create_schedule_table_row(self, index, interval, time_zone):
        start_time = _format_datetime(interval.start, time_zone)
        end_time = _format_datetime(interval.end, time_zone)
        return (index, start_time, end_time)
        
        
def _format_datetime(dt, time_zone=None):
    if time_zone is not None:
        dt = dt.astimezone(time_zone)
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def _create_tables(tables):
    return [_create_table(t.title, t.rows, t.header, t.footer) for t in tables]


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
