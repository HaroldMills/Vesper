from __future__ import print_function

from nfc.archive.archive import Archive
from nfc.util.preferences import preferences as prefs


'''
Thinking about call counts in a pandas dataframe:

station x night date x minute x clip class
10 x 100 x 500 x 30 = 1.5e7 counts = 15 megabytes (one byte per count)

station x night date x five minute period x clip class
10 x 100 x 100 x 30 = 3e6 counts = 6 megabytes (two bytes per count)

station x night date x ten minute period x clip class
10 x 100 x 50 x 30 = 1.5e6 counts = 3 megabytes (two bytes per count)

We'd like to scale to hundreds of stations.

It might be a good idea to add a method to the `Archive` class that gets clip
counts binned to a specified number of minutes. How would this relate to the
existing `get_clip_counts` method?
'''


def main():
    
    archive = Archive.open(prefs['archiveDirPath'])
    
    print('getting call clips...')
    
    # Inside the archive we don't need to construct clips. We can bin
    # counts directly from cursor rows. Note that a given clip may
    # count for more than one class, since we have subclasses. But
    # perhaps we could aggregate subclass counts after obtaining an
    # initial set of counts by counting each clip exactly once?
    clips = archive.get_clips()  # (clip_class_name='Call')
    
    print('done')

    print(len(clips))


if __name__ == '__main__':
    main()
