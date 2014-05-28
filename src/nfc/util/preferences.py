"""Module containing NFC Viewer preferences."""


from __future__ import print_function
import json
        
            
_COMMAND_SETS = {
                 
    'Coarse': '''
        c Call
        C Call All
        n Noise
        N Noise All
    ''',
    
    'Calls': '''
        a AMRE
        A ATSP
        b BTBW
        B BAWW
        c CSWA
        C CMWA
        Ctrl-c COYE
        Ctrl-C CCSP
        Alt-c CAWA
        Alt-C CHSP
        D ShDbUp
        f FOSP
        g GHSP
        h HOWA
        H HESP
        i INBU
        l LCSP
        m MOWA
        n Noise
        N NWTH
        o Oven
        O Other
        p PAWA
        P PALM
        q Unknown
        s SVSP
        S SwLi
        Ctrl-s SNBULALO
        T ATSP
        v VESP
        w WIWA
        W WTSP
        Alt-w WCSP
        x Weak
        y YRWA
        z Zeep
    '''
    
}


def _load_preferences():
    
    try:
        preferences = json.loads('''
{
    "archiveDirPath": "/Users/Harold/Desktop/NFC/Data/Old Bird/2012 Summer and Fall",
    "stationName": "Alfred",
    "detectorName": "Tseep",
    "clipClassName": "Call",
    "monthName": "September 2012",
    "mainWindow.width": 1000,
    "mainWindow.height": 800,
    "mainWindow.countDisplayType": "archive calendar",
    "clipsWindow.width": 1200,
    "clipsWindow.height": 800,
    "clipGrid.numRows": 4,
    "clipGrid.numColumns": 5,
    "clipGrid.showMouseTimeFreq": true,
    "clipGrid.showClipClassNames": true,
    "clipGrid.showClipTimes": true,
    "clipGrid.clipTextFontSize": 11,
    "clipGrid.clipTextColor": "white",
    "clipGrid.clipClassTextColors": { "Call": "cyan" },
    "classification.defaultCommandSet": "Calls"
    
}
''')
        
    except ValueError:
        print('Could not parse preferences file.')
        return {}
    
    try:
        preferences['classification.commandSets'] = \
            _parse_command_sets(_COMMAND_SETS)
    except ValueError as e:
        print(str(e))
        
    return preferences


def _parse_command_sets(commandSets):
    return dict(_parse_command_set(*i) for i in commandSets.iteritems())


def _parse_command_set(name, text):
    lines = [line.strip() for line in text.splitlines()]
    pairs = [_parseCommand(line, i + 1, name)
             for i, line in enumerate(lines) if line != '']
    return (name, dict(pairs))


_ALL_MARKER = 'All'


def _parseCommand(line, lineNum, commandSetName):
    
    items = line.split()
    n = len(items)
    
    if n < 2 or n > 3:
        raise ValueError(
            ('Bad command specification "{:s}" for command set "{:s}": '
             'specification must have either two or three components '
             'separated by spaces.').format(line, commandSetName))
    
    name = items[0]
    command = items[1]
    all_ = n == 3
    
    if all_ and items[2] != _ALL_MARKER:
        raise ValueError(
            ('Bad command specification "{:s}" for command set "{:s}": '
             'third component must be "{:s}".').format(
                line, commandSetName, _ALL_MARKER))
        
    return (name, (command, all_))


preferences = _load_preferences()
