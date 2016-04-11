import csv
import datetime
import os

import pytz

import vesper.util.ephem_utils as ephem_utils


_DATA_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data'

_RS_INPUT_FILE_PATH = os.path.join(_DATA_DIR_PATH, 'USNO Rise Set Data.csv')
_RS_DIFFS_FILE_PATH = \
    os.path.join(_DATA_DIR_PATH, 'USNO-PyEphem Rise Set Diffs.csv')
    
_RS_DIFF_REPORTING_THRESHOLD = 35
"""
Reporting threshold for rise/set differences, in seconds.

USNO rise/set times are rounded to the nearest minute, while PyEphem
rise/set times are not. Hence we consider a PyEphem rise/set time to
differ from a USNO one if and only if the magnitude of their difference
exceeds 30 seconds, i.e. if the PyEphem time rounded to the nearest
minute differs from the USNO time. We report only differences whose
magnitudes exceed `_RS_DIFF_REPORTING_THRESHOLD`.
"""

_AA_INPUT_FILE_PATH = \
    os.path.join(_DATA_DIR_PATH, 'USNO Altitude Azimuth Data.csv')
_AA_DIFFS_FILE_PATH = \
    os.path.join(_DATA_DIR_PATH, 'USNO-PyEphem Altitude Azimuth Diffs.csv')
    
_AA_SMALL_ALTITUDE_DIFF_REPORTING_THRESHOLD = .6
"""
Reporting threshold for altitude differences for USNO altitudes in the
range [0, 10], in degrees.

PyEphem altitudes differ from USNO altitudes in the [0, 10] degree range
more than they do for altitudes outside of this range, probably because of
USNO atmospheric refraction calculations.
"""
# TODO: Verify that differences stem from atmospheric refraction
# calculations. Can PyEphem (or we, outside of PyEphem) handle it in the
# same way and produce more similar numbers?

_AA_ANGLE_DIFF_REPORTING_THRESHOLD = .100001
"""
Reporting threshold for altitude and azimuth differences, in degrees.

See `_AA_SMALL_ALTITUDE_DIFF_REPORTING_THRESHOLD` for a different
threshold that is used instead of this one for USNO altitudes in the
range [0, 10] degrees.
"""

_AA_ILLUMINATION_DIFF_REPORTING_THRESHOLD = .51
"""
Reporting threshold for illumination differences, in percent.

USNO illuminations are rounded to the nearest percent, while PyEphem
illuminations are not. Hence we consider a PyEphem illumination to
differ from a USNO one if and only if the magnitude of their difference
exceeds .5 percent, i.e. if the PyEphem illumination rounded to the
nearest percent differs from the USNO illumination. We report only
differences whose magnitudes exceed
`_AA_ILLUMINATION_DIFF_REPORTING_THRESHOLD`.

"""

_LAT_LIMIT = 70
"""
Latitude limit of tests, in degrees.

Input data at latitudes whose magnitudes exceed the limit are ignored.
"""


def _main():
    tester = _Tester()
    tester.test_rs_times()
    tester.test_aa_data()


class _Tester(object):
    
    
    def test_rs_times(self):
        
        diffs_file = open(_RS_DIFFS_FILE_PATH, 'wb')
        self.diffs_writer = csv.writer(diffs_file)
        self.diffs_writer.writerow((
            'Count', 'Latitude', 'Longitude', 'Local Date', 'Event',
            'USNO Time', 'PyEphem Time', 'Offset Difference'))
        self.num_diffs = 0
        
        input_file = open(_RS_INPUT_FILE_PATH)
        input_reader = csv.reader(input_file)
        
        # Skip header.
        next(input_reader)
        
        for row in input_reader:
            usno_data = _UsnoRiseSetData(*row)
            if _include_test_case(usno_data):
                self._test_rs_time(usno_data)
                
        diffs_file.close()
        input_file.close()
            
            
    def _test_rs_time(self, usno_data):
        
        d = usno_data
        
        time = ephem_utils.get_event_time(d.event, d.lat, d.lon, d.local_date)
        
        # TODO: Perhaps we should report when PyEphem does not
        # provide rise/set events that the USNO does. This happens
        # sometimes at higher latitudes.
        
        if time is not None:
        
            diff = (time - d.time).total_seconds()
            
            if abs(diff) > _RS_DIFF_REPORTING_THRESHOLD:
                
                self.diffs_writer.writerow((
                    self.num_diffs, d.lat, d.lon, d.local_date, d.event,
                    d.time, time, diff))
                
                self.num_diffs += 1
            
            
    def test_aa_data(self):
        
        diffs_file = open(_AA_DIFFS_FILE_PATH, 'wb')
        self.diffs_writer = csv.writer(diffs_file)
        self.diffs_writer.writerow((
            'Count', 'Latitude', 'Longitude', 'Time', 'Body',
            'Measurement', 'USNO Value', 'PyEphem Value', 'Difference'))
        self.num_diffs = 0
        
        input_file = open(_AA_INPUT_FILE_PATH)
        input_reader = csv.reader(input_file)
        
        # Skip header.
        next(input_reader)
        
        for row in input_reader:
            usno_data = _UsnoAltitudeAzimuthData(*row)
            if _include_test_case(usno_data):
                self._test_aa_data(usno_data)
                
        diffs_file.close()
        input_file.close()
            
            
    def _test_aa_data(self, usno_data):
        
        d = usno_data
        
        args = (d.body, d.lat, d.lon, d.time)
        altitude = ephem_utils.get_altitude(*args)
        azimuth = ephem_utils.get_azimuth(*args)
        if d.body == 'Sun':
            illumination = None
        else:
            illumination = ephem_utils.get_illumination(*args)
        
        rounded_altitude = round(altitude * 10) / 10.
        diff = rounded_altitude - d.altitude
        if _altitude_diff_exceeds_reporting_threshold(diff, d.altitude):
            self._report_aa_diff(d, 'Altitude', d.altitude, altitude, diff)
        
        rounded_azimuth = round(azimuth * 10) / 10.
        diff = rounded_azimuth - d.azimuth
        if abs(diff) > _AA_ANGLE_DIFF_REPORTING_THRESHOLD:
            self._report_aa_diff(d, 'Azimuth', d.azimuth, azimuth, diff)
            
        if illumination is not None:
            usno_illumination = d.illumination * 100
            diff = illumination - usno_illumination
            if abs(diff) > _AA_ILLUMINATION_DIFF_REPORTING_THRESHOLD:
                self._report_aa_diff(
                    d, 'Illumination', usno_illumination, illumination,
                    diff)
                
    
    def _report_aa_diff(self, d, name, usno_value, ephem_value, diff):
        self.diffs_writer.writerow((
            self.num_diffs, d.lat, d.lon, d.time, d.body,
            name, usno_value, ephem_value, diff))
    
    
def _altitude_diff_exceeds_reporting_threshold(diff, altitude):
    if altitude >= 0 and altitude < 10:
        if abs(diff) > _AA_SMALL_ALTITUDE_DIFF_REPORTING_THRESHOLD:
            return True
    elif abs(diff) > _AA_ANGLE_DIFF_REPORTING_THRESHOLD:
        return True
    else:
        return False


class _UsnoRiseSetData():
    
    def __init__(self, lat, lon, local_date, event, time):
        strptime = datetime.datetime.strptime
        self.lat = float(lat)
        self.lon = float(lon)
        self.local_date = strptime(local_date, '%Y-%m-%d').date()
        self.event = event
        dt = strptime(time, '%Y-%m-%d %H:%M')
        self.time = pytz.utc.localize(dt)


class _UsnoAltitudeAzimuthData():
    
    
    def __init__(self, lat, lon, time, body, altitude, azimuth, illumination):
        
        strptime = datetime.datetime.strptime
        
        self.lat = float(lat)
        self.lon = float(lon)
        self.time = strptime(time, '%Y-%m-%d %H:%M')
        self.body = body
        self.altitude = float(altitude)
        self.azimuth = float(azimuth)
        
        if illumination.strip() == '':
            self.illumination = None
        else:
            self.illumination = float(illumination)
        
        
def _include_test_case(usno_data):
    return abs(usno_data.lat) <= _LAT_LIMIT


if __name__ == '__main__':
    _main()
    