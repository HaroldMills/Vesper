"""NFC viewer application."""


from __future__ import print_function

import argparse
import sys

from PyQt4.QtGui import QApplication
    
from nfc.ui.main_window import MainWindow
from nfc.util.preferences import preferences as prefs


def _main():
    
    args = _parse_args()
    archive_dir_path = _get_archive_dir_path(args, prefs)
    commands_preset_name = _get_commands_preset_name(args, prefs)

    # This must happen before any other QT operations, including
    # creating the main window.
    app = QApplication(sys.argv)
    
    window = MainWindow(
        archive_dir_path,
        prefs['mainWindow.initialStation'],
        prefs['mainWindow.initialDetector'],
        prefs['mainWindow.initialClipClass'],
        commands_preset_name)
    
    _set_geometry(window, app.desktop().availableGeometry())
    
    window.show()
    window.activateWindow()
    window.raise_()
    
    app.exec_()
    
    sys.exit()


def _parse_args():
    
    parser = argparse.ArgumentParser(description='NFC Viewer')
    
    parser.add_argument(
        '--archive', help='the name of the archive to view')
    
    parser.add_argument(
        '--classification-commands',
        help='the name of the commands preset to use')
    
    args = parser.parse_args()
    
    return args


def _get_archive_dir_path(args, prefs):
    
    name = args.archive
    if name is None:
        name = prefs.get('archive')
        
    if name is None:
        _handle_init_error(
            'No archive name specified. Please specify one either via an '
            '"--archive" command line argument or the "archive" preference.')
        
    archives = prefs.get('archives')
    
    if archives is None:
        _handle_init_error(
            'No "archives" preference found. This preference is required '
            'and should be a JSON object whose member names and values '
            'are archive names and directory paths, respectively.')

    path = archives.get(name)
    
    if path is None:
        f = 'No archive "{:s}" found in "archives" preference.'
        _handle_init_error(f.format(name))
        
    return path
    
    
def _handle_init_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def _get_commands_preset_name(args, prefs):
    
    name = args.classification_commands
    if name is None:
        name = prefs.get('clipsWindow.defaultClassificationCommands')
        
    return name
        
    
def _set_geometry(window, available_rect):
    
    w = prefs.get('mainWindow.width')
    h = prefs.get('mainWindow.height')
    
    if w is not None and h is not None:
        # width and height preferences specified
        
        r = available_rect
        
        w = min(w, r.width())
        h = min(h, r.height())
        x = (r.width() - w) / 2
        y = (r.height() - h) / 2
        
        window.setGeometry(x, y, w, h)
    

if __name__ == '__main__':
    _main()
