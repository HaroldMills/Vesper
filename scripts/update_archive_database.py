"""
Script that updates an old Vesper archive database file to a version 0.01
database file.

The old database file is assumed to be named "ClipDatabase.db", and to be
located in the current directory. The new database file is called
"Archive Database.sqlite" and is written to the current directory.
"""


from __future__ import print_function
import sqlite3 as sqlite


_CREATE_STATION_TABLE_SQL = '''
    create table Station (
        id integer primary key,
        name text,
        long_name text,
        time_zone_name text,
        latitude real,
        longitude real,
        elevation real,
        unique(name) on conflict rollback)'''
        
        
_CREATE_DETECTOR_TABLE_SQL = '''
    create table Detector (
        id integer primary key,
        name text,
        unique(name) on conflict rollback)'''
        
        
_CREATE_CLIP_CLASS_TABLE_SQL = '''
    create table ClipClass (
        id integer primary key,
        name text,
        unique(name) on conflict rollback)'''
        
        
_CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL = '''
    create table ClipClassNameComponent (
        id integer primary key,
        component text,
        unique(component) on conflict rollback)'''
        
        
_CREATE_RECORDING_TABLE_SQL = '''
    create table Recording (
        id integer primary key,
        station_id integer,
        start_time datetime,
        length integer,
        sample_rate real,
        unique(station_id, start_time) on conflict rollback)'''


_CREATE_CLIP_TABLE_SQL = '''
    create table Clip (
        id integer primary key,
        station_id integer,
        detector_id integer,
        start_time datetime,
        night integer,
        duration real,
        selection_start_index integer,
        selection_length integer,
        clip_class_id integer,
        clip_class_name_0_id integer,
        clip_class_name_1_id integer,
        clip_class_name_2_id integer,
        unique(station_id, detector_id, start_time) on conflict rollback)'''
        
_CREATE_RECORDING_TABLE_START_TIME_INDEX_SQL = '''
    create index StartTimeIndex on Recording(start_time)
'''

_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL = '''
    create index ClipIndex on Clip(station_id, detector_id, night)
'''

_CREATE_CLIP_TABLE_NIGHT_INDEX_SQL = '''
    create index NightIndex on Clip(night)
'''

_INPUT_FILE_NAME = 'ClipDatabase.db'
_OUTPUT_FILE_NAME = 'Archive Database.sqlite'


def _main():
    updater = _ArchiveUpdater()
    updater.update_archive_database()
    
    
class _ArchiveUpdater(object):
    
    
    def update_archive_database(self):
        self._open_databases()
        self._update_tables()
        self._create_recording_table()
        self._add_indices()
        self._close_databases()
        
        
    def _open_databases(self):

        self._input_connection = sqlite.connect(_INPUT_FILE_NAME)
        self._input_cursor = self._input_connection.cursor()
        
        self._output_connection = sqlite.connect(_OUTPUT_FILE_NAME)
        self._output_cursor = self._output_connection.cursor()
    
    
    def _update_tables(self):
        
        self._update_table(
            'Station', _CREATE_STATION_TABLE_SQL, self._create_station_row)
        
        self._update_table('Detector', _CREATE_DETECTOR_TABLE_SQL)
        
        self._update_table('ClipClass', _CREATE_CLIP_CLASS_TABLE_SQL)
        
        self._update_table(
            'ClipClassNameComponent',
            _CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL)
        
        self._update_table(
            'Clip', _CREATE_CLIP_TABLE_SQL, self._create_clip_row)

        self._output_cursor.execute(_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL)
        self._output_cursor.execute(_CREATE_CLIP_TABLE_NIGHT_INDEX_SQL)


    def _update_table(self, table_name, creation_sql, create_output_row=None):
        
        self._output_cursor.execute(creation_sql)
        
        sql = 'select * from {} order by id'.format(table_name)
        self._input_cursor.execute(sql)
        input_rows = self._input_cursor.fetchall()
        
        if create_output_row is not None:
            output_rows = [create_output_row(row) for row in input_rows]
        else:
            output_rows = input_rows
        
        if len(output_rows) > 0:
            n = len(output_rows[0])
            marks = ', '.join(['?'] * n)
            sql = ('insert into {} values (' + marks + ')').format(table_name)
            self._output_cursor.executemany(sql, output_rows)

        self._output_connection.commit()


    def _create_station_row(self, row):
        # Append station latitude, longitude, and elevation.
        return row + (None, None, None)
            
    
    def _create_clip_row(self, row):
        # Insert selection start index and length.
        return row[:6] + (None, None) + row[6:]
    
    
    def _create_recording_table(self):
        self._output_cursor.execute(_CREATE_RECORDING_TABLE_SQL)
        self._output_cursor.execute(
            _CREATE_RECORDING_TABLE_START_TIME_INDEX_SQL)
        self._output_connection.commit()
        
        
    def _add_indices(self):
        pass
    

    def _close_databases(self):
        self._input_connection.close()
        self._output_connection.close()
    
    
if __name__ == '__main__':
    _main()
