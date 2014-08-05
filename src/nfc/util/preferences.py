"""Module containing NFC Viewer preferences."""


from __future__ import print_function
import json
        
            
_COMMAND_SETS = {
                 
    'Coarse': '''
        c Call
        C Call Page
        Alt-c Call All
        n Noise
        N Noise Page
        Alt-n Noise All
        t Tone
        T Tone Page
        Alt-t Tone All
        u Unclassified
        U Unclassified Page
        Alt-u Unclassified All
    ''',
    
    'Calls': '''
        a AMRE
        A ATSP
        b BTBW
        B BAWW
        k Call
        c CSWA
        C CMWA
        Ctrl-c COYE
        Ctrl-C CCSP
        Alt-c CAWA
        Alt-C CHSP
        D DbUp
        f FOSP
        g GHSP
        h HOWA
        H HESP
        i INBU
        l LCSP
        m MOWA
        n Noise
        N NWTH
        o OVEN
        O Other
        p PAWA
        P PROW
        q Unknown
        s SVSP
        S SwLi
        Ctrl-s SNBULALO
        t Tone
        T ATSP
        u Unclassified
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
        preferences = json.loads(r'''
{
    "archiveDirPaths": {
        "2012": "/Users/Harold/Desktop/NFC/Data/Old Bird/2012 Summer and Fall",
        "2014": "/Users/Harold/Desktop/NFC/Data/Old Bird/2014"
    },
    "defaultArchive": "2012",
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
    "classification.defaultCommandSet": "Coarse"
    
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


_SCOPES = frozenset(['Selected', 'Page', 'All'])


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
    scope = items[2] if n == 3 else 'Selected'
    
    if scope not in _SCOPES:
        f = ('Bad command specification "{:s}" for command set "{:s}": '
             'third component must be "Page" or "All".')
        raise ValueError(f.format(line, commandSetName))
        
    return (name, (command, scope))


preferences = _load_preferences()
