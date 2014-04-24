"""Constants pertaining to 2012 Old Bird clip archive."""


from nfc.util.bunch import Bunch


_STATION_NAMES = [
    'Ajo', 'Alfred', 'ColumbiaLC', 'Danby', 'Derby', 'HSHS', 'Jamestown',
    'Minatitlan', 'NMHS', 'Ottawa', 'Skinner', 'WFU']


STATIONS = [Bunch(name=name) for name in _STATION_NAMES]


_DETECTOR_NAMES = ['Tseep']


DETECTORS = [Bunch(name=name) for name in _DETECTOR_NAMES]


_CALL_CLIP_CLASS_NAMES = [
                          
    'AMRE', 'ATSP', 'BAWW', 'BRSP', 'BTBW', 'CAWA', 'CCSP', 'CHSP',
    'CMWA', 'COYE', 'CSWA', 'FOSP', 'GHSP', 'HESP', 'HOWA', 'INBU',
    'LALO', 'LCSP', 'MOWA', 'NOPA', 'NWTH', 'OVEN', 'PAWA', 'PROW',
    'SNBU', 'SVSP', 'VESP', 'WCSP', 'WIWA', 'WTSP', 'YRWA',
    
    'WTSP.Songtype',
    
    'DbUp', 'Other', 'SNBULALO', 'SwLi', 'Unknown', 'Weak', 'Zeep'

]


_CLIP_CLASS_NAMES = \
    ['Call', 'Noise', 'Tone'] + \
    ['Call.' + name for name in _CALL_CLIP_CLASS_NAMES]
         
                          
CLIP_CLASSES = [Bunch(name=name) for name in _CLIP_CLASS_NAMES]
