"""
Script that trims the example archive.

This script deletes from an archive the stations and detectors for which
there are no clips. It deletes noise clips if needed to reduce the fraction
of noise clips in the archive to a specified value.
"""

from __future__ import print_function

import os
import random

from nfc.archive.archive import Archive


_ARCHIVE_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/Old Bird/Example'
_NOISE_FRACTION = .5


def main():
    
    _delete_extra_stations_and_detectors()
    _adjust_call_to_noise_ratio()
    
    
def _adjust_call_to_noise_ratio():
    
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open(True)
    
    retention_probability = _get_noise_retention_probability(archive)
    
    if retention_probability < .98:
        _delete_noises(archive, retention_probability)

    archive.close()
        
        
def _get_noise_retention_probability(archive):
    
    clip_class_counts = _get_clip_counts(
        archive, [], 'clip_class_name', ['Call*', 'Noise*'])

    num_calls = clip_class_counts['Call*']
    num_noises = clip_class_counts['Noise*']
    
    desired_num_noises = _NOISE_FRACTION * num_calls
    
    return min(desired_num_noises / float(num_noises), 1.)
        

def _delete_noises(archive, retention_probability):
    
    conn = archive._conn
    cursor = archive._cursor
    
    stations = archive.stations
    detectors = archive.detectors
    
    for station in stations:
        
        for detector in detectors:
            
            counts = archive.get_clip_counts(
                station.name, detector.name, clip_class_name='Noise*')
            
            nights = counts.keys()
            nights.sort()
            
            for night in nights:
                
                clips = archive.get_clips(
                    station.name, detector.name, night, 'Noise*')
                
                num_deleted = 0
                
                for clip in clips:
                    r = random.uniform(0, 1)
                    if r > retention_probability:
                        _delete_clip(clip, cursor)
                        num_deleted += 1
                        
                print(station.name, detector.name, night, len(clips),
                      num_deleted)

    # We commit if and only if all of the deletions succeed.
    conn.commit()
    

def _delete_clip(clip, cursor):
    
    sql = 'delete from clip where id = ?'
      
    try:
        cursor.execute(sql, (clip._id,))
        
    except Exception as e:
        f = ('Could not delete clip with id {:d} from archive. '
             'SQLite delete failed with message: {:s}')
        raise ValueError(f.format(clip._id, str(e)))
    
    try:
        os.remove(clip.file_path)
        
    except Exception as e:
        f = ('Could not delete clip with id {:d} from archive. '
             'File deletion failed with message: {:s}')
        raise ValueError(f.format(clip._id, str(e)))


def _delete_extra_stations_and_detectors():
    
    archive = Archive(_ARCHIVE_DIR_PATH)
    archive.open(True)
    
    stations = archive.stations
    detectors = archive.detectors
    clip_classes = archive.clip_classes
    
    station_counts = _get_clip_counts(archive, stations, 'station_name')
    detector_counts = _get_clip_counts(archive, detectors, 'detector_name')
    clip_class_counts = _get_clip_counts(
        archive, clip_classes, 'clip_class_name', ['Call*', 'Unclassified'])
        
    _show_clip_counts(station_counts, 'station')
    _show_clip_counts(detector_counts, 'detector')
    _show_clip_counts(clip_class_counts, 'clip class')
    
    # This method makes assumptions about the archive implementation that
    # it eventually should not. We should enhance the archive interface
    # to support station and detector deletion, which will allow us to
    # implement this method without making such assumptions.
    
    conn = archive._conn
    cursor = archive._cursor
    
    _delete_zero_count_entities(station_counts, cursor, 'station')
    _delete_zero_count_entities(detector_counts, cursor, 'detector')
    
    # We commit if and only if all of the deletions succeed.
    conn.commit()
    
    archive.close()
                
    
def _delete_zero_count_entities(counts, cursor, description):
    
    sql = 'delete from {:s} where name = ?'.format(description)
    
    names = [name for name, count in counts.iteritems() if count == 0]
    
    for name in names:
        
        print('deleting {:s} "{:s}"...'.format(description, name))
        
        try:
            cursor.execute(sql, (name,))
            
        except Exception as e:
            f = ('Could not delete {:s} "{:s}" from archive. '
                 'SQLite error message was: {:s}')
            raise ValueError(f.format(description, name, str(e)))
        

def _get_clip_counts(archive, items, arg_name, extra_item_names=None):
    names = [i.name for i in items]
    names += extra_item_names if extra_item_names is not None else []
    return dict((n, _get_clip_counts_aux(archive, n, arg_name)) for n in names)


def _get_clip_counts_aux(archive, name, arg_name):
    counts = archive.get_clip_counts(**{arg_name: name})
    return sum(c for c in counts.itervalues())


def _show_clip_counts(counts, item_type):
    
    print('Clip counts by {:s}:'.format(item_type))
    
    names = counts.keys()
    names.sort()
    
    for name in names:
        print('    {:s} {:d}'.format(name, counts[name]))
        
    print()


if __name__ == '__main__':
    main()


"""
Archive operations

For scalability, at least some types of archive operations will be limited
in scope, including queries that get clips or clip counts and queries that
delete clips. I'm inclined to start with the rule that such queries should
be limited to a single station and detector, and that archives should be
limited in temporal extent, for example to a single season (spring or fall)
or a single year.

Note that certain queries, for example one that deletes all data for a
particular station, cannot be so limited. Such queries, however, can be
implemented in terms of the limited ones.

Specific archive operations:

* Get stations
* Get detectors
* Get clip classes
* Get clip counts
* Get clips

* Add station
* Add detector
* Add clip class
* Add clip

* Modify station
* Modify detector
* Modify clip class
* Modify clip

* Delete station
* Delete detector
* Delete clip class
* Delete clips

The implementation of some operations may result in multiple operations,
e.g. database queries, behind the scenes.


We will eventually need *agent*, *classification*, and *comment* entities.
An agent is either a person or an algorithm. A classification assigns a clip
to a clip class, and has an associated agent and time. A comment refers to
one or more entities (including other comments, though not itself) and has
an agent and a version history.

There are two basic types of metadata, *measurements* and *annotations*.
The difference between the two is that measurmenets are (in principle,
at least) reproducible while annotations may not be. So a number produced
by a particular version of an algorithm is a measurement, while a
classification produced by a person is not. Annotations can have change
histories, while measurements cannot. There may, however, be measurements
made by different versions of the same algorithm.

Is there some term that encompasses both measurements and annotations?

We should record version histories for annotations.

Are comments just annotations?

An algorithmic agent has a name as well as an algorithm name, version number,
and parameters.

A human agent has a name and perhaps other information, like an email address
and password.

What about continuous recordings, and clips that refer to them?

What about multi-channel or multi-microphone recordings, and clips from
different channels or microphones that record the same vocalization?

What about separate collections of metadata derived from the same data,
for example "Joe's Classifications, Second Pass"?

What is the difference between *data* and *metadata*? For example, what
would one call clips that refer to segments of continuous recordings, as
opposed to clips that have been extracted from continuous recordings?
Is this distinction really important? It may help to think in terms of
directed graphs of entities.

The term "provenance" may be useful.
"""
