"""Module containing class `Archive`."""


from collections import namedtuple
import datetime
import os.path

import pytz
import sqlite3 as sqlite

from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.recording import Recording
from vesper.archive.station import Station
from vesper.util.bunch import Bunch
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


'''
Questions regarding cloud archives:

* What should GAE entity groups be?
* How do we support classification histories?
* How do we support aggregate statistics?
* What indexes do we need?
* Should we require login, perhaps just for certain functionality?
* Do we provide just sounds, or spectrograms, too?
* How soon could we have multiple people classifying?
* How can we automate uploading?
'''


_MANIFEST_FILE_NAME = 'Archive Manifest.yaml'
_DATABASE_FILE_NAME = 'Archive Database.sqlite'
_CLIPS_DIR_NAME = 'Clips'
    
# named tuple classes for database tables
_StationTuple = namedtuple(
    '_StationTuple',
    ('id', 'name', 'long_name', 'time_zone_name', 'latitude', 'longitude',
     'elevation'))
_DetectorTuple = namedtuple('_DetectorTuple', ('id', 'name'))
_ClipClassTuple = namedtuple('_ClipClassTuple', ('id', 'name'))
_ClipClassNameComponentTuple = \
    namedtuple('_ClipClassNameComponentTuple', ('id', 'component'))
_RecordingTuple = namedtuple(
    '_RecordingTuple',
    ('id', 'station_id', 'start_time', 'length', 'sample_rate'))
_ClipTuple = namedtuple(
    '_ClipTuple',
    ('id', 'station_id', 'detector_id', 'start_time', 'night', 'duration',
     'selection_start_index', 'selection_length',
     'clip_class_id', 'clip_class_name_0_id', 'clip_class_name_1_id',
     'clip_class_name_2_id'))


# TODO: Replace separate recording, clip, and selection abstractions
# with a single sound abstraction. Add sound tags and/or key/value
# stores to support features like sound sets and multi-user classification.
# Where do stations and detectors fit into this? How does such an
# organization scale?

# TODO: Review SQL for vulnerability to injection attacks. Would it be
# possible to use ?s everywhere? String formatting can be safe, but it
# would be safer still to not use it at all.

# TODO: Add non-null requirements, e.g. for station and detector names
# and station time zone names.


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

_SELECT_STATION_SQL = 'select * from Station where name = ?'

_INSERT_RECORDING_SQL = \
    'insert into Recording values (' + \
    ', '.join(['?'] * len(_RecordingTuple._fields)) + ')'
    
_SELECT_RECORDINGS_SQL = (
    'select * from Recording where station_id = ? and '
    'start_time >= ? and start_time < ?')

_INSERT_CLIP_SQL = \
    'insert into Clip values (' + \
    ', '.join(['?'] * len(_ClipTuple._fields)) + ')'

_SELECT_CLIP_SQL = (
    'select * from Clip where station_id = ? and detector_id = ? and '
    'start_time = ?')
    
_CLASSIFY_CLIP_SQL = (
    'update Clip set clip_class_id = ?, clip_class_name_0_id = ?, '
    'clip_class_name_1_id = ?, clip_class_name_2_id = ? where id = ?')

_SET_CLIP_SELECTION_SQL = (
    'update Clip set selection_start_index = ?, selection_length = ? '
    'where id = ?')


class Archive:
    
    
    CLIP_CLASS_NAME_COMPONENT_SEPARATOR = '.'
    CLIP_CLASS_NAME_WILDCARD = '*'
    CLIP_CLASS_NAME_UNCLASSIFIED = 'Unclassified'


    @staticmethod
    def exists(dir_path):
        # TODO: Check for manifest and ensure that archive type and
        # version are supported.
        db_file_path = os.path.join(dir_path, _DATABASE_FILE_NAME)
        return os.path.isfile(db_file_path)
    
    
    @staticmethod
    def create(dir_path, stations=None, detectors=None, clip_classes=None):
        
        # TODO: Validate arguments, for example to make sure that
        # clip class names do not have more than three components?
        
        if stations is None:
            stations = []
            
        if detectors is None:
            detectors = []
            
        if clip_classes is None:
            clip_classes = []
        
        # Create archive directory, along with any needed directories above,
        # if needed.
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
        _create_archive_manifest(dir_path)
        
        archive = Archive(dir_path)
        archive._open_db()
        archive._create_tables(stations, detectors, clip_classes)
        archive._close_db()
        
        return archive
    
    
    def __init__(self, dir_path):
        self._archive_dir_path = dir_path
        self._name = os.path.basename(dir_path)
        self._db_file_path = os.path.join(dir_path, _DATABASE_FILE_NAME)
        
        
    @property
    def name(self):
        return self._name
    
    
    def open(self, cache_db=False):
        self._check_archive_dir()
        self._open_db(cache_db)
        self._create_dicts()
        self._clip_dir_paths = set()


    def _check_archive_dir(self):
        if not os.path.exists(self._archive_dir_path):
            raise ValueError(
                'Archive directory "{}" does not exist.'.format(
                    self._archive_dir_path))
        
        
    def _open_db(self, cache_db=False):
        
        self._open_manifest_file()
        
        self._cache_db = cache_db
        
        if self._cache_db:
            file_conn = self._open_db_file()
            self._conn = sqlite.connect(':memory:')
            _copy_db(file_conn, self._conn)
            file_conn.close()
            
        else:
            self._conn = self._open_db_file()

        self._cursor = self._conn.cursor()


    def _open_manifest_file(self):
        
        path = os.path.join(self._archive_dir_path, _MANIFEST_FILE_NAME)
        
        try:
            manifest = os_utils.read_yaml_file(path)
        except OSError as e:
            raise ValueError(str(e))
        
        _check_manifest(manifest, path)
        
        
    def _open_db_file(self):
        
        path = self._db_file_path
        
        try:
            return sqlite.connect(path)
        
        except:
            
            if not os.path.exists(path):
                raise ValueError(
                    'Database file "{:s}" does not exist'.format(path))
            else:
                m = 'Database file "{:s}" exists but could not be opened.'
                raise ValueError(m.format(path))


    def close(self):
        self._close_db()
    
    
    def _close_db(self):
        
        if self._cache_db:
            
            path = self._db_file_path + ' new'
            
            # write memory database to new file
            file_conn = sqlite.connect(path)
            _copy_db(self._conn, file_conn)
            file_conn.close()
            
            # delete old database file if it exists
            if os.path.exists(self._db_file_path):
                os.remove(self._db_file_path)
                
            # rename new database file
            os.rename(path, self._db_file_path)
        
        self._conn.close()
        
        
    def _drop_tables(self):
        self._drop_table('Station')
        self._drop_table('Detector')
        self._drop_table('ClipClass')
        self._drop_table('ClipClassNameComponent')
        self._drop_table('Recording')
        self._drop_table('Clip')
        
        
    def _drop_table(self, name):
        
        try:
            self._cursor.execute('drop table ' + name)
            
        except sqlite.OperationalError:
            
            # TODO: Recover gracefully here.
            pass
            
            
    def _create_tables(self, stations, detectors, clip_classes):
        self._create_station_table(stations)
        self._create_detector_table(detectors)
        self._create_clip_class_table(clip_classes)
        self._create_clip_class_name_component_table(clip_classes)
        self._create_recording_table()
        self._create_clip_table()
    
    
    def _create_station_table(self, stations):
        self._create_table(
            'Station', _CREATE_STATION_TABLE_SQL, stations,
            self._create_station_tuple)
        
        
    def _create_table(self, name, create_sql, objects=(), tuple_creator=None):
        
        self._cursor.execute(create_sql)
        
        if len(objects) > 0:
            
            if tuple_creator is None:
                tuples = objects
            else:
                tuples = [tuple_creator(obj) for obj in objects]
            
            marks = ', '.join(['?'] * len(tuples[0]))
            sql = 'insert into {:s} values ({:s})'.format(name, marks)
            
            self._cursor.executemany(sql, tuples)
            
        self._conn.commit()
    
    
    def _create_station_tuple(self, station):
        s = station
        return _StationTuple(
            id=None, name=s.name, long_name=s.long_name,
            time_zone_name=s.time_zone.zone,
            latitude=s.latitude, longitude=s.longitude, elevation=s.elevation)
    
    
    def _create_detector_table(self, detectors):
        self._create_table(
            'Detector', _CREATE_DETECTOR_TABLE_SQL, detectors,
            self._create_detector_tuple)
        
        
    def _create_detector_tuple(self, detector):
        return _DetectorTuple(id=None, name=detector.name)
    
    
    def _create_clip_class_table(self, clip_classes):
        self._create_table(
            'ClipClass', _CREATE_CLIP_CLASS_TABLE_SQL, clip_classes,
            self._create_clip_class_tuple)
        
        
    def _create_clip_class_tuple(self, clip_class):
        return _ClipClassTuple(id=None, name=clip_class.name)
    
    
    def _create_clip_class_name_component_table(self, clip_classes):
        components = _get_name_components(clip_classes)
        tuples = [_ClipClassNameComponentTuple(None, c) for c in components]
        self._create_table(
            'ClipClassNameComponent',
            _CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL,
            tuples)
        
        
    def _create_recording_table(self):
        self._create_table('Recording', _CREATE_RECORDING_TABLE_SQL)
        self._cursor.execute(_CREATE_RECORDING_TABLE_START_TIME_INDEX_SQL)
        self._conn.commit()
        
        
    def _create_clip_table(self):
        self._create_table('Clip', _CREATE_CLIP_TABLE_SQL)
        self._cursor.execute(_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL)
        self._cursor.execute(_CREATE_CLIP_TABLE_NIGHT_INDEX_SQL)
        self._conn.commit()
        
        
    def _create_dicts(self):
        aux = self._create_dicts_aux
        (self._station_ids, self._stations) = aux(self.stations)
        (self._detector_ids, self._detectors) = aux(self.detectors)
        (self._clip_class_ids, self._clip_classes) = \
            aux(self.clip_classes)
        self._clip_class_name_component_ids = \
            dict((o.component, o.id)
                 for o in self._get_clip_class_name_components())
        
        
    def _create_dicts_aux(self, objects):
        ids_dict = dict((o.name, o.id) for o in objects)
        objects_dict = dict((o.id, o) for o in objects)
        return (ids_dict, objects_dict)
        
        
    def _get_clip_class_name_components(self):
        sql = 'select * from ClipClassNameComponent order by id'
        self._cursor.execute(sql)
        rows = self._cursor.fetchall()
        return self._create_bunches(_ClipClassNameComponentTuple, rows)
    
    
    def _create_bunches(self, cls, rows):
        return [Bunch(**dict(zip(cls._fields, r))) for r in rows]
    

    @property
    def stations(self):
        return self._create_objects_from_db_table(Station)
    
    
    def _create_objects_from_db_table(self, cls):
        sql = 'select * from {:s} order by id'.format(cls.__name__)
        self._cursor.execute(sql)
        rows = self._cursor.fetchall()
        objects = [_create_with_id(cls, *r) for r in rows]
        objects.sort(key=lambda o: o.name)
        return objects
    
    
    def get_station(self, name):
        id_ = self._check_station_name(name)
        return self._stations[id_]
        
        
    @property
    def detectors(self):
        return self._create_objects_from_db_table(Detector)
    
    
    def get_detector(self, name):
        id_ = self._check_detector_name(name)
        return self._detectors[id_]
    
    
    @property
    def clip_classes(self):
        return self._create_objects_from_db_table(ClipClass)
    
    
    def get_clip_class(self, name):
        id_ = self._check_clip_class_name(name)
        return self._clip_classes[id_]
        
        
    @property
    def start_night(self):
        return self._get_extremal_night('min')
    
    
    def _get_extremal_night(self, function_name):
        sql = 'select {:s}(night) from Clip'.format(function_name)
        self._cursor.execute(sql)
        date_int = self._cursor.fetchone()[0]
        return _int_to_date(date_int)
        
        
    @property
    def end_night(self):
        return self._get_extremal_night('max')
        
        
    def add_recording(self, station_name, start_time, length, sample_rate):
        
        """
        Adds a recording to this archive.
        
        :Parameters:
        
            station_name : `str`
                the name of the station of the clip.
                
            start_time : `datetime`
                the UTC start time of the recording.
                
                To help ensure archive data quality, the start time is
                required to have the `pytz.utc` time zone.
                
            length : `int`
                the length of the recording in sample frames.
               
            sample_rate : `int` or `float`
                the sample rate of the recording in hertz.
                
        :Returns:
            the inserted recording, of type `Recording`.
            
        :Raises ValueError:
            if the specified station name is not recognized, or if
            there is already a recording in the archive with the
            specified station name and start time.
        """
        
        
        station_id = self._check_station_name(station_name)
        
        if start_time.tzinfo is not pytz.utc:
            raise ValueError('Recording time zone must be `pytz.utc`.')
        
        recording_tuple = _RecordingTuple(
            id=None,
            station_id=station_id,
            start_time=_format_time(start_time),
            length=length,
            sample_rate=sample_rate)
    
        try:
            self._cursor.execute(_INSERT_RECORDING_SQL, recording_tuple)
            
        except sqlite.IntegrityError:
            f = ('There is already a recording in the archive for station '
                 '"{:s}" and UTC start time {:s}.')
            raise ValueError(
                f.format(station_name, _format_time(start_time)))
        
        station = self._stations[station_id]
        recording = Recording(station, start_time, length, sample_rate)
        
        # We wait until here to commit since we don't want to commit if
        # any of the above steps fail.
        self._conn.commit()
                    
        return recording

        
    def _get_clip_class_name_component_ids(self, class_name):
        components = class_name.split('.') if class_name is not None else []
        ids = [self._clip_class_name_component_ids[c] for c in components]
        return ids + [None] * (3 - len(components))
        
        
    def _check_station_name(self, name):
        try:
            return self._station_ids[name]
        except KeyError:
            raise ValueError('Unrecognized station name "{:s}".'.format(name))
        
        
    def _check_detector_name(self, name):
        try:
            return self._detector_ids[name]
        except KeyError:
            raise ValueError('Unrecognized detector name "{:s}".'.format(name))
        
        
    def _check_clip_class_name(self, name):
        
        if name is None:
            return None
        
        else:
            
            try:
                return self._clip_class_ids[name]
            except KeyError:
                raise ValueError(
                    'Unrecognized clip class name "{:s}".'.format(name))
        
        
    def get_recordings(self, station_name, night):
            
        """
        Gets the archived recordings for the specified station and night.
        
        :Returns:
            a list of recordings for the specified station and night.
        """
        
        station_id = self._check_station_name(station_name)
        station = self._stations[station_id]
        
        night_start_time = time_utils.create_utc_datetime(
            night.year, night.month, night.day, 12,
            time_zone=station.time_zone)
        
        night_end_time = night_start_time + datetime.timedelta(days=1)
        
        # Convert times to strings for database query.
        night_start_time = _format_time(night_start_time)
        night_end_time = _format_time(night_end_time)
        
        self._cursor.execute(
            _SELECT_RECORDINGS_SQL,
            (station_id, night_start_time, night_end_time))
        
        recordings = [self._create_recording(_RecordingTuple._make(row))
                      for row in self._cursor]
        
        return recordings
    
    
    def _create_recording(self, recording):
        r = recording
        station = self._stations[r.station_id]
        start_time = _parse_time(r.start_time)
        return Recording(station, start_time, r.length, r.sample_rate)
        
        
    def get_clip_counts(
            self, station_name=None, detector_name=None, start_night=None,
            end_night=None, clip_class_name=None):
        
        """
        Counts the archived clips matching the specified criteria.
        
        :Returns:
            Per-night clip counts in a dictionary that maps start
            night dates (of type `Date`) to clip counts (of type
            `int`).
        """
        

        where = self._create_where_clause(
            station_name, detector_name, start_night, end_night,
            clip_class_name)
        
        sql = 'select night, count(*) from Clip' + where + ' group by night'
        
#        print('Archive.get_clip_counts:', sql)
        
        self._cursor.execute(sql)
        
        return dict((_int_to_date(d), c) for (d, c) in self._cursor)
        
        
    def _create_where_clause(
            self, station_name, detector_name, start_night, end_night,
            clip_class_name):
        
        conds = []
        
        conds += self._get_station_conditions(station_name)
        conds += self._get_detector_conditions(detector_name)
        conds += self._get_night_conditions(start_night, end_night)
        conds += self._get_clip_class_conditions(clip_class_name)
        
        return ' where ' + ' and '.join(conds) if len(conds) != 0 else ''
        

    def _get_station_conditions(self, station_name):
        
        if station_name is None:
            return []
        
        else:
            id_ = self._check_station_name(station_name)
            return ['station_id = {:d}'.format(id_)]
            
            
    def _get_detector_conditions(self, detector_name):
        
        if detector_name is None:
            return []
        
        else:
            id_ = self._check_detector_name(detector_name)
            return ['detector_id = {:d}'.format(id_)]
            
            
    def _get_night_conditions(self, start_night, end_night):
        
        if start_night != end_night:
            aux = self._get_night_conditions_aux
            return aux(start_night, '>=') + aux(end_night, '<=')
                   
        elif start_night is not None:
            # start date and end date are equal and not `None`
            
            return ['night = {:d}'.format(_date_to_int(start_night))]
        
        else:
            # start date and end date are both `None`
            
            return []

                   
    def _get_night_conditions_aux(self, date, operator):
        
        if date is None:
            return []
        
        else:
            return ['night {:s} {:d}'.format(operator, _date_to_int(date))]
        
        
    def _get_clip_class_conditions(self, class_name):
        
        if class_name is None or \
                class_name == Archive.CLIP_CLASS_NAME_WILDCARD:
            
            return []
        
        else:
            
            include_subclasses = False
            
            if class_name.endswith(Archive.CLIP_CLASS_NAME_WILDCARD):
                include_subclasses = True
                n = len(Archive.CLIP_CLASS_NAME_WILDCARD)
                class_name = class_name[:-n]
            
            if class_name == Archive.CLIP_CLASS_NAME_UNCLASSIFIED:
                return ['clip_class_id is null']
                
            else:
                
                self._check_clip_class_name(class_name)

                if include_subclasses:
                    
                    components = class_name.split('.')
                    
                    ids = [self._clip_class_name_component_ids[c]
                           for c in components]
                    
                    return ['clip_class_name_{:d}_id = {:d}'.format(*p)
                            for p in enumerate(ids)]
                        
                else:
                    id_ = self._clip_class_ids[class_name]
                    return ['clip_class_id = {:d}'.format(id_)]
    
    
    def get_clips(
            self, station_name=None, detector_name=None, night=None,
            clip_class_name=None):
        
        """
        Gets the archived clips matching the specified criteria.
        
        :Returns:
            a list of `Clip` objects ordered by start time.
        """
        
        where = self._create_where_clause(
            station_name, detector_name, night, night, clip_class_name)
        
        sql = 'select * from Clip' + where + ' order by start_time'
        
#        print('Archive.get_clips', sql)
        
#        planSql = 'explain query plan ' + sql
#        print('Archive.get_clips', planSql)
#        self._cursor.execute(planSql)
#        rows = self._cursor.fetchall()
#        print(rows)
        
        # TODO: Try to speed this up. Are we using indices effectively?
        self._cursor.execute(sql)
        
        return self._create_clips()
    
    
    def _create_clips(self):
        # rows = self._cursor.fetchall()
        # return [self._create_clip(_ClipTuple._make(row)) for row in rows]
        # TODO: Try to speed this up. The iteration is slow. Perhaps
        # returning a generator that constructs clips from rows on
        # the fly would be faster?
        return [self._create_clip(_ClipTuple._make(row))
                for row in self._cursor]
    
    
    def _create_clip(self, clip):
        
        station = self._stations[clip.station_id]
        detector_name = self._detectors[clip.detector_id].name
        
        class_id = clip.clip_class_id
        try:
            clip_class_name = self._clip_classes[class_id].name
        except KeyError:
            clip_class_name = None
            
        start_time = _parse_time(clip.start_time)
        
        if clip.selection_start_index is None:
            selection = None
        else:
            selection = (clip.selection_start_index, clip.selection_length)
        
        return _Clip(
            self, clip.id, station, detector_name, start_time, clip.duration,
            selection, clip_class_name)
        
        
    def get_clip(self, station_name, detector_name, start_time):
        
        station_id = self._check_station_name(station_name)
        detector_id = self._check_detector_name(detector_name)
        
        if start_time.tzinfo is not pytz.utc:
            raise ValueError('Clip time zone must be `pytz.utc`.')
        
        start_time = _format_time(start_time)
        clip_info = (station_id, detector_id, start_time)
        self._cursor.execute(_SELECT_CLIP_SQL, clip_info)
    
        row = self._cursor.fetchone()
        
        if row is None:
            return None
        
        else:
            return self._create_clip(_ClipTuple._make(row))
        
        
    def _classify_clip(self, clip_id, clip_class_name):
        
        class_id = self._check_clip_class_name(clip_class_name)
        component_ids = self._get_clip_class_name_component_ids(
            clip_class_name)
        
        values = [class_id] + component_ids + [clip_id]
        self._cursor.execute(_CLASSIFY_CLIP_SQL, values)
        self._conn.commit()
        
        
    def _set_clip_selection(self, clip_id, selection):
        
        if selection is None:
            start_index = None
            length = None
        else:
            start_index, length = selection
            
        values = (start_index, length, clip_id)
        self._cursor.execute(_SET_CLIP_SELECTION_SQL, values)
        self._conn.commit()
        
        
    def _create_clip_dir_if_needed(self, path):
        
        dir_path = os.path.dirname(path)
        
        if dir_path not in self._clip_dir_paths:
            # directory either doesn't exist or hasn't yet been
            # added to `_clip_dir_paths`
            
            try:
                os.makedirs(dir_path)
                
            except OSError:
                
                if not (os.path.exists(dir_path) and os.path.isdir(dir_path)):
                    # makedirs did not fail because directory
                    # already existed
                    
                    raise
                
            # If we get here, makedirs either succeeded or failed
            # because the directory already existed.
            self._clip_dir_paths.add(dir_path)
                    
        
    def _create_clip_file_path(self, station, detector_name, start_time):
        dir_path = self._create_clip_dir_path(station, start_time)
        file_name = _create_clip_file_name(
            station.name, detector_name, start_time)
        return os.path.join(dir_path, file_name)
        
        
    def _create_clip_dir_path(self, station, start_time):
        n = station.get_night(start_time)
        year_name = _create_year_dir_name(n.year)
        month_name = _create_month_dir_name(n.year, n.month)
        day_name = _create_day_dir_name(n.year, n.month, n.day)
        return os.path.join(
            self._archive_dir_path, _CLIPS_DIR_NAME, station.name,
            year_name, month_name, day_name)
    

def _create_archive_manifest(archive_dir_path):
    file_path = os.path.join(archive_dir_path, _MANIFEST_FILE_NAME)
    contents = ''.join([line.strip() + '\n' for line in '''
        archive_type: "Vesper SQLite/File System Archive"
        archive_version: "0.01"
    '''.strip().split('\n')])
    os_utils.write_file(file_path, contents)

    
def _check_manifest(manifest, path):
    _check_manifest_aux(
        manifest, 'archive_type', 'Vesper SQLite/File System Archive', path)
    _check_manifest_aux(manifest, 'archive_version', '0.01', path)
    
    
def _check_manifest_aux(manifest, key, expectedValue, path):
    value = manifest.get(key)
    if value != expectedValue:
        raise ValueError((
            'Unrecognized value "{:s}" for archive manifest key "{:s}". '
            'Was expecting "{:s}".').format(value, key, expectedValue))
        

def _copy_db(from_conn, to_conn):
    _create_db_tables(to_conn)
    _copy_db_tables(from_conn, to_conn)
    
    
def _copy_db_tables(from_conn, to_conn):
    _copy_db_table('Station', from_conn, to_conn)
    _copy_db_table('Detector', from_conn, to_conn)
    _copy_db_table('ClipClass', from_conn, to_conn)
    _copy_db_table('ClipClassNameComponent', from_conn, to_conn)
    _copy_db_table('Clip', from_conn, to_conn)

    
def _copy_db_table(name, from_conn, to_conn):
    
    from_cursor = from_conn.cursor()
    to_cursor = to_conn.cursor()
    
    sql = 'select * from {:s} order by id'.format(name)
    from_cursor.execute(sql)
    
    sql = None
    
    while True:
        
        rows = from_cursor.fetchmany(1000)
        
        if len(rows) == 0:
            break
        
        if sql is None:
            num_columns = len(rows[0])
            question_marks = ', '.join(['?'] * num_columns)
            sql = 'insert into {:s} values ({:s})'.format(name, question_marks)
            
        to_cursor.executemany(sql, rows)
        
    to_conn.commit()
        
    
def _create_db_tables(conn):
    
    cursor = conn.cursor()
    
    # tables
    cursor.execute(_CREATE_STATION_TABLE_SQL)
    cursor.execute(_CREATE_DETECTOR_TABLE_SQL)
    cursor.execute(_CREATE_CLIP_CLASS_TABLE_SQL)
    cursor.execute(_CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL)
    cursor.execute(_CREATE_CLIP_TABLE_SQL)
    
    # indices
    cursor.execute(_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL)
    cursor.execute(_CREATE_CLIP_TABLE_NIGHT_INDEX_SQL)
    
    conn.commit()
    
    
def _date_to_int(date):
    return ((date.year * 100 + date.month) * 100) + date.day


def _int_to_date(night):
    year = night // 10000
    month = (night % 10000) // 100
    day = night % 100
    return datetime.date(year, month, day)


def _parse_time(time):
    time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
    time = pytz.utc.localize(time)
    return time
    
    
def _format_time(time):
    millisecond = int(round(time.microsecond / 1000.))
    return time.strftime('%Y-%m-%d %H:%M:%S') + '.{:03d}'.format(millisecond)


def _create_with_id(cls, id_, *args, **kwds):
    obj = cls(*args, **kwds)
    obj.id = id_
    return obj
    

def _get_name_components(clip_classes):
    
    components = set()
    components.update(*[c.name_components for c in clip_classes])
    
    components = list(components)
    components.sort()

    return components
    
    
_MIN_CLIP_DURATION = .05
"""
the minimum clip duration in seconds.

Clips shorter than this duration are padded with zeros to make them
long enough. This is part of a temporary "fix" to GitHub issue 30.
"""


class _Clip:
    
    
    def __init__(
            self, archive, clip_id, station, detector_name, start_time,
            duration, selection=None, clip_class_name=None):
        
        self._archive = archive
        self._id = clip_id
        self.station = station
        self.detector_name = detector_name
        self.start_time = start_time
        self._duration = duration
        self._selection = selection
        self._clip_class_name = clip_class_name
        
        self._file_path = None
        self._audio = None
        self._spectrogram = None
        self._instantaneous_frequencies = None
        
        
    @property
    def file_path(self):
        
        if self._file_path is None:
            self._file_path = self._archive._create_clip_file_path(
                self.station, self.detector_name, self.start_time)
            
        return self._file_path
    
    
    @property
    def night(self):
        return self.station.get_night(self.start_time)
    
    
    @property
    def recording(self):
        
        station_name = self.station.name
        night = self.night
        recordings = self._archive.get_recordings(station_name, night)
        
        if len(recordings) == 0:
            return None
        
        else:
            
            for recording in recordings:
                
                start_time = self.start_time
                
                if recording.start_time <= start_time and \
                   recording.end_time >= start_time:
                    
                    return recording
                
            # If we get here, the clip start time was outside all
            # recording intervals.
            return None
        
        
#     @property
#     def audio(self):
#         
#         if self._audio is None:
#             # audio not yet read from file
#             
#             self._audio = audio_utils.read_audio_file(self.file_path)
#             
#             # Pad audio with zeros to make it at least `_MIN_CLIP_DURATION`
#             # seconds long. This is part of a temporary "fix" to GitHub
#             # issue 30.
#             if self._duration < _MIN_CLIP_DURATION:
#                 min_length = \
#                     int(round(_MIN_CLIP_DURATION * self._audio.sample_rate))
#                 n = min_length - len(self._audio.samples)
#                 if n > 0:
#                     self._audio.samples = \
#                         np.hstack((self._audio.samples, np.zeros(n)))
#                 
#         return self._audio
    
    
    @property
    def duration(self):
        return max(self._duration, _MIN_CLIP_DURATION)
    
    
    @property
    def clip_class_name(self):
        return self._clip_class_name
    
    
    @clip_class_name.setter
    def clip_class_name(self, name):
        self._archive._classify_clip(self._id, name)
        self._clip_class_name = name


#     def play(self):
#         audio_utils.play_audio_file(self.file_path)
        
        
    @property
    def selection(self):
        return self._selection
    
    
    @selection.setter
    def selection(self, selection):
        self._archive._set_clip_selection(self._id, selection)
        self._selection = selection
        

def _create_year_dir_name(year):
    return '{:d}'.format(year)


def _create_month_dir_name(year, month):
    return '{:02d}'.format(month)


def _create_day_dir_name(year, month, day):
    return '{:02d}'.format(day)


def _create_clip_file_name(station_name, detector_name, start_time):
    ms = int(round(start_time.microsecond / 1000.))
    start_time = start_time.strftime('%Y-%m-%d_%H.%M.%S') + \
        '.{:03d}'.format(ms) + '_Z'
    return '{:s}_{:s}_{:s}.wav'.format(
        station_name, detector_name, start_time)
