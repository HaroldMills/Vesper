"""Module containing `Archive` class."""


from __future__ import print_function

from collections import namedtuple
import datetime
import os.path

import numpy as np
import sqlite3 as sqlite

from nfc.util.audio_file_utils import \
    WAVE_FILE_NAME_EXTENSION as _CLIP_FILE_NAME_EXTENSION
from nfc.util.bunch import Bunch
from nfc.util.spectrogram import Spectrogram
import nfc.util.sound_utils as sound_utils


'''
Questions regarding cloud archives:

* What should GAE entity groups be?
* How do we support classification histories?
* How do we support aggregate staistics?
* What indexes do we need?
* Should we require login, perhaps just for certain functionality?
* Do we provide just sounds, or spectrograms, too?
* How soon could we have multiple people classifying?
* How can we automate uploading?
'''


# TODO: Use "night" rather than "nightDate" in database?


_CLIP_CLASS_NAME_WILDCARD = '*'

_CLIP_DATABASE_FILE_NAME = 'ClipDatabase.db'
    
# named tuple classes for database tables
_StationTuple = namedtuple('_StationTuple', ('id', 'name'))
_DetectorTuple = namedtuple('_DetectorTuple', ('id', 'name'))
_ClipClassTuple = namedtuple('_ClipClassTuple', ('id', 'name'))
_ClipClassNameComponentTuple = \
    namedtuple('_ClipClassNameComponentTuple', ('id', 'component'))
_ClipTuple = namedtuple(
    '_ClipTuple',
    ('id', 'stationId', 'detectorId', 'time', 'nightDate', 'duration',
     'clipClassId', 'clipClassNameComponent0Id', 'clipClassNameComponent1Id',
     'clipClassNameComponent2Id'))


_CREATE_STATION_TABLE_SQL = '''
    create table Stations (
        id integer primary key,
        name text,
        unique(name) on conflict rollback)'''
        
        
_CREATE_DETECTOR_TABLE_SQL = '''
    create table Detectors (
        id integer primary key,
        name text,
        unique(name) on conflict rollback)'''
        
        
_CREATE_CLIP_CLASS_TABLE_SQL = '''
    create table ClipClasses (
        id integer primary key,
        name text,
        unique(name) on conflict rollback)'''
        
        
_CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL = '''
    create table ClipClassNameComponents (
        id integer primary key,
        component text,
        unique(component) on conflict rollback)'''
        
        
_CREATE_CLIP_TABLE_SQL = '''
    create table Clips (
        id integer primary key,
        stationId integer,
        detectorId integer,
        time datetime,
        nightDate integer,
        duration real,
        clipClassId integer,
        clipClassNameComponent0Id integer,
        clipClassNameComponent1Id integer,
        clipClassNameComponent2Id integer,
        unique(stationId, detectorId, time) on conflict rollback)'''
        
_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL = '''
    create index ClipsIndex on Clips(stationId, detectorId, nightDate)
'''

_CREATE_CLIP_TABLE_NIGHT_DATE_INDEX_SQL = '''
    create index NightDateIndex on Clips(nightDate)
'''

_INSERT_CLIP_SQL = \
    'insert into Clips values (' + \
    ', '.join(['?'] * len(_ClipTuple._fields)) + ')'


_CLASSIFY_CLIP_SQL = (
    'update Clips set clipClassId = ?, clipClassNameComponent0Id = ?, '
    'clipClassNameComponent1Id = ?, clipClassNameComponent2Id = ? '
    'where id = ?')


class Archive(object):
    
    
    # TODO: Move these somewhere else. They are UI constants, and
    # this class should not know anything about UI. Note that when
    # they are moved the `_getClipClassWhereConditions` method will
    # need to be modified accordingly.
    CLIP_CLASS_NAME_ANY = 'Any'
    CLIP_CLASS_NAME_UNCLASSIFIED = 'Unclassified'


    @staticmethod
    def get_night(time):
        
        """
        Gets the starting date of the night that includes the specified time.
        
        :Parameters:
        
            time : `datetime`
                the specified time.
                
        :Returns:
            the starting date of the night that includes the specified
            time, of type `date`.
            
            For a time whose hour is at least 12, the night start date
            is the time's date. For a time whose hour is less than 12,
            the night start date is that of the day prior to the day
            that includes the clip time.
        """
            
        if time.hour < 12:
            time -= datetime.timedelta(hours=12)
            
        return time.date()
    

    @staticmethod
    def get_clip_class_name_components(classes):
        
        components = set()
        components.update(*[c.name.split('.') for c in classes])
        
        components = list(components)
        components.sort()
    
        return components
    
    
    @staticmethod
    def create(dir_path, stations, detectors, clip_classes):
        
        # TODO: Create directory if it does not exist.
        
        # TODO: Validate arguments, for example to make sure that
        # clip class names do not have more than three components?
        
        archive = Archive(dir_path)
        archive._drop_tables()
        archive._create_tables(stations, detectors, clip_classes)
        archive._create_dicts()
        return archive
    
    
    @staticmethod
    def open(dir_path):
        archive = Archive(dir_path)
        archive._create_dicts()
        return archive
        
        
    def __init__(self, dir_path):
        
        self._archive_dir_path = dir_path
        
        db_file_path = os.path.join(dir_path, _CLIP_DATABASE_FILE_NAME)
        self._conn = sqlite.connect(db_file_path)
        self._cursor = self._conn.cursor()
        
        self._clip_dir_paths = set()
        
        
    def _drop_tables(self):
        self._drop_table('Stations')
        self._drop_table('Detectors')
        self._drop_table('ClipClasses')
        self._drop_table('ClipClassNameComponents')
        self._drop_table('Clips')
        
        
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
        self._create_clip_table()
    
    
    def _create_station_table(self, stations):
        self._create_table(
            'Stations', _CREATE_STATION_TABLE_SQL, stations,
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
        return _StationTuple(id=None, name=station.name)
    
    
    def _create_detector_table(self, detectors):
        self._create_table(
            'Detectors', _CREATE_DETECTOR_TABLE_SQL, detectors,
            self._create_detector_tuple)
        
        
    def _create_detector_tuple(self, detector):
        return _DetectorTuple(id=None, name=detector.name)
    
    
    def _create_clip_class_table(self, classes):
        self._create_table(
            'ClipClasses', _CREATE_CLIP_CLASS_TABLE_SQL, classes,
            self._create_clip_class_tuple)
        
        
    def _create_clip_class_tuple(self, clip_class):
        return _ClipClassTuple(id=None, name=clip_class.name)
    
    
    def _create_clip_class_name_component_table(self, classes):
        components = [_ClipClassNameComponentTuple(None, c)
                      for c in Archive.get_clip_class_name_components(classes)]
        self._create_table(
            'ClipClassNameComponents',
            _CREATE_CLIP_CLASS_NAME_COMPONENT_TABLE_SQL,
            components)
        
        
    def _createClipClassNameComponentTuple(self, component):
        return _ClipClassNameComponentTuple(id=None, component=component)
    
    
    def _create_clip_table(self):
        
        self._create_table('Clips', _CREATE_CLIP_TABLE_SQL)
        
        self._cursor.execute(_CREATE_CLIP_TABLE_MULTICOLUMN_INDEX_SQL)
        self._cursor.execute(_CREATE_CLIP_TABLE_NIGHT_DATE_INDEX_SQL)
        
        self._conn.commit()
        
        
    def _create_dicts(self):
        aux = self._create_dicts_aux
        (self._station_ids, self._stations) = aux(self.get_stations())
        (self._detector_ids, self._detectors) = aux(self.get_detectors())
        (self._clip_class_ids, self._clip_classes) = \
            aux(self.get_clip_classes())
        self._clip_class_name_component_ids = \
            dict((o.component, o.id)
                 for o in self._get_clip_class_name_components())
        
        
    def _create_dicts_aux(self, objects):
        ids_dict = dict((o.name, o.id) for o in objects)
        objects_dict = dict((o.id, o) for o in objects)
        return (ids_dict, objects_dict)
        
        
    def get_stations(self):
        self._cursor.execute('select * from Stations order by id')
        return self._create_bunches(_StationTuple, self._cursor.fetchall())
    
    
    def _create_bunches(self, cls, rows):
        return [Bunch(**dict(zip(cls._fields, r))) for r in rows]
    

    def get_detectors(self):
        self._cursor.execute('select * from Detectors order by id')
        return self._create_bunches(_DetectorTuple, self._cursor.fetchall())
    
    
    def get_clip_classes(self):
        self._cursor.execute('select * from ClipClasses order by id')
        classes = self._create_bunches(
            _ClipClassTuple, self._cursor.fetchall())
        classes.sort(key=lambda c: c.name)
        return classes
    
    
    def _get_clip_class_name_components(self):
        self._cursor.execute(
            'select * from ClipClassNameComponents order by id')
        return self._create_bunches(
                   _ClipClassNameComponentTuple, self._cursor.fetchall())
    
    
    def get_start_night(self):
        self._cursor.execute('select min(nightDate) from Clips')
        date_int = self._cursor.fetchone()[0]
        return _int_to_date(date_int)
        
        
    def get_end_night(self):
        self._cursor.execute('select max(nightDate) from Clips')
        date_int = self._cursor.fetchone()[0]
        return _int_to_date(date_int)
        
        
    def add_clip(
        self, station_name, detector_name, time, sound, clip_class_name=None):
        
        """
        Adds a clip to this archive.
        
        :Parameters:
        
            station_name : `str`
                the name of the station of the clip.
                
            detector_name : `str`
                the name of the detector of the clip.
                
            time : `datetime`
                the start time of the clip.
                
            sound : `object`
                the clip sound.
                
                the clip sound must include a `samples` attribute
                whose value is a NumPy array containing the 16-bit
                two's complement samples of the sound, and a
                `sample_rate` attribute specifying the sample rate
                of the sound in hertz.
                
            clip_class_name : `str`
                the clip class name, or `None` if the class is not known.
                
        :Returns:
            the inserted clip, of type `Clip`.
            
        :Raises ValueError:
            if the specified station name, detector name, or clip
            class name is not recognized, or if there is already a
            clip in the archive with the specified station name,
            detector name, and time.
        """
        
        
        duration = len(sound.samples) / float(sound.sample_rate)
        ids = self._get_clip_class_name_component_ids(clip_class_name)
        
        clip_tuple = _ClipTuple(
            id=None,
            stationId=self._check_station_name(station_name),
            detectorId=self._check_detector_name(detector_name),
            time=_format_clip_time(time),
            nightDate=_date_time_to_night_int(time),
            duration=duration,
            clipClassId=self._check_clip_class_name(clip_class_name),
            clipClassNameComponent0Id=ids[0],
            clipClassNameComponent1Id=ids[1],
            clipClassNameComponent2Id=ids[2])
    
        # TODO: Handle exceptions.
        self._cursor.execute(_INSERT_CLIP_SQL, clip_tuple)
        clip_id = self._cursor.lastrowid
        
        file_path = self._create_clip_file_path(
            station_name, detector_name, time, create_dir=True)
        
        sound_utils.write_sound_file(file_path, sound)
        
        self._conn.commit()
                    
        return _Clip(
            self, clip_id, station_name, detector_name, time,
            duration, clip_class_name)


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
        
        
    def _create_clip_file_path(
        self, station_name, detector_name, clip_time, create_dir=False):
        
        dir_path = self._create_clip_dir_path(station_name, clip_time)
        
        if create_dir:
            
            if dir_path not in self._clip_dir_paths:
                # directory either doesn't exist or hasn't yet been
                # added to `_clip_dir_paths`
                
                try:
                    os.makedirs(dir_path)
                    
                except OSError:
                    
                    if not (os.path.exists(dir_path) and \
                            os.path.isdir(dir_path)):
                        # makedirs did not fail because directory
                        # already existed
                        
                        raise
                    
                # If we get here, makedirs either succeeded or failed
                # because the directory already existed.
                self._clip_dir_paths.add(dir_path)
                    
        file_name = _create_clip_file_name(
                        station_name, detector_name, clip_time)
        
        return os.path.join(dir_path, file_name)
        
        
    def _create_clip_dir_path(self, station_name, clip_time):
        n = Archive.get_night(clip_time)
        month_dir_name = _create_month_dir_name(n.year, n.month)
        day_dir_name = _create_day_dir_name(n.year, n.month, n.day)
        return os.path.join(
            self._archive_dir_path, station_name, month_dir_name, day_dir_name)
    
    
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
        
        sql = 'select nightDate, count(*) from Clips' + where + \
              ' group by nightDate'
        
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
            self._check_station_name(station_name)
            id_ = self._station_ids[station_name]
            return ['stationId = {:d}'.format(id_)]
            
            
    def _get_detector_conditions(self, detector_name):
        
        if detector_name is None:
            return []
        
        else:
            self._check_detector_name(detector_name)
            id_ = self._detector_ids[detector_name]
            return ['detectorId = {:d}'.format(id_)]
            
            
    def _get_night_conditions(self, start_night, end_night):
        
        if start_night != end_night:
            aux = self._get_night_conditions_aux
            return aux(start_night, '>=') + aux(end_night, '<=')
                   
        elif start_night is not None:
            # start date and end date are equal and not `None`
            
            return ['nightDate = {:d}'.format(_date_to_int(start_night))]
        
        else:
            # start date and end date are both `None`
            
            return []

                   
    def _get_night_conditions_aux(self, date, operator):
        
        if date is None:
            return []
        
        else:
            return ['nightDate {:s} {:d}'.format(operator, _date_to_int(date))]
        
        
    def _get_clip_class_conditions(self, class_name):
        
        if class_name is None or class_name == Archive.CLIP_CLASS_NAME_ANY:
            return []
        
        else:
            
            include_subclasses = False
            
            if class_name.endswith(_CLIP_CLASS_NAME_WILDCARD):
                include_subclasses = True
                class_name = class_name[:-len(_CLIP_CLASS_NAME_WILDCARD)]
            
            if class_name == Archive.CLIP_CLASS_NAME_UNCLASSIFIED:
                return ['clipClassId is null']
                
            else:
                
                self._check_clip_class_name(class_name)

                if include_subclasses:
                    
                    components = class_name.split('.')
                    
                    ids = [self._clip_class_name_component_ids[c]
                           for c in components]
                    
                    return ['clipClassNameComponent%dId = {:d}'.format(p)
                            for p in enumerate(ids)]
                        
                else:
                    id_ = self._clip_class_ids[class_name]
                    return ['clipClassId = {:d}'.format(id_)]
    
    
    def get_clips(
        self, station_name=None, detector_name=None, night=None,
        clip_class_name=None):
        
        """
        Gets the archived clips matching the specified criteria.
        
        :Returns:
            Per-night clip lists in a dictionary that maps start
            night dates (of type `Date`) to lists of `Clip` objects.
        """
        
        where = self._create_where_clause(
            station_name, detector_name, night, night, clip_class_name)
        
        sql = 'select * from Clips' + where + ' order by time'
        
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
#        rows = self._cursor.fetchall()
#        return [self._create_clip(_ClipTuple._make(row)) for row in rows]
        # TODO: Try to speed this up. The iteration is slow.
        return [self._create_clip(_ClipTuple._make(row))
                for row in self._cursor]
    
    
    def _create_clip(self, clip):
        
        station_name = self._stations[clip.stationId].name
        detector_name = self._detectors[clip.detectorId].name
        
        class_id = clip.clipClassId
        try:
            clip_class_name = self._clip_classes[class_id].name
        except KeyError:
            clip_class_name = None
            
        time = self._parse_clip_time(clip.time)
        
        return _Clip(
            self, clip.id, station_name, detector_name, time,
            clip.duration, clip_class_name)
        
        
    def _parse_clip_time(self, time):
        return datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')
    
    
    def _classify_clip(self, clip_id, clip_class_name):
        
        class_id = self._check_clip_class_name(clip_class_name)
        component_ids = self._get_clip_class_name_component_ids(
                            clip_class_name)
        
        values = [class_id] + component_ids + [clip_id]
        self._cursor.execute(_CLASSIFY_CLIP_SQL, values)
        self._conn.commit()
        
        
    def close(self):
        self._conn.close()
    
    
def _date_time_to_night_int(time):
    date = Archive.get_night(time)
    return _date_to_int(date)


def _date_to_int(date):
    return ((date.year * 100 + date.month) * 100) + date.day


def _int_to_date(night):
    year = night // 10000
    month = (night % 10000) // 100
    day = night % 100
    return datetime.date(year, month, day)


def _format_clip_time(time):
    millisecond = int(round(time.microsecond / 1000.))
    return time.strftime('%Y-%m-%d %H:%M:%S') + '.{:03d}'.format(millisecond)


SPECTROGRAM_PARAMS = Bunch(
    window=np.hanning(100),
    hop_size=25,
    dft_size=None,
    ref_power=1)


class _Clip(object):
    
    
    # TODO: Should we give a clip a station and a detector rather than
    # just names?
    
    def __init__(
        self, archive, clip_id, station_name, detector_name, time, duration,
        clip_class_name=None):
        
        self._archive = archive
        self._id = clip_id
        self.station_name = station_name
        self.detector_name = detector_name
        self.time = time
        self.duration = duration
        self._clip_class_name = clip_class_name
        
        self._sound = None
        self._spectrogram = None
        
        
    @property
    def night(self):
        return Archive.get_night(self.time)
    
    
    @property
    def sound(self):
        
        if self._sound is None:
            # sound not yet read from file
            
            station_name = self.station_name
            detector_name = self.detector_name
            time = self.time
            file_path = self._archive._create_clip_file_path(
                            station_name, detector_name, time)
            
            self._sound = sound_utils.read_sound_file(file_path)
            
        return self._sound
    
    
    @property
    def spectrogram(self):
        
        if self._spectrogram is None:
            # have not yet computed spectrogram
            
            self._spectrogram = Spectrogram(self.sound, SPECTROGRAM_PARAMS)
                
        return self._spectrogram
        
        
    @property
    def clip_class_name(self):
        return self._clip_class_name
    
    
    @clip_class_name.setter
    def clip_class_name(self, name):
        self._archive._classify_clip(self._id, name)
        self._clip_class_name = name


    def play(self):
        
        station_name = self.station_name
        detector_name = self.detector_name
        time = self.time
        file_path = self._archive._create_clip_file_path(
                        station_name, detector_name, time)
            
        sound_utils.play_sound_file(file_path)
    
    
def _create_month_dir_name(year, month):
    return '{:02d}'.format(month)


def _create_day_dir_name(year, month, day):
    return '{:02d}'.format(day)


def _create_clip_file_name(station_name, detector_name, clip_time):
    ms = int(round(clip_time.microsecond / 1000.))
    time = clip_time.strftime('%Y-%m-%d_%H.%M.%S') + '.{:03d}'.format(ms)
    return '{:s}_{:s}_{:s}{:s}'.format(
               station_name, detector_name, time, _CLIP_FILE_NAME_EXTENSION)
