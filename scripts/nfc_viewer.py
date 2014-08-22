"""NFC viewer application."""


from __future__ import print_function

import argparse
import sys

from PySide.QtGui import QApplication
    
from nfc.ui.main_window import MainWindow
from nfc.util.preferences import preferences as prefs


def _main():
    
    app = QApplication(sys.argv)
    
    args = _parse_args()
    
    archive_dir_path = _get_archive_dir_path(args, prefs)
    command_set_name = _get_command_set_name(args, prefs)
    count_display_type = 'archive calendar'

    window = MainWindow(
        archive_dir_path, command_set_name, count_display_type,
        prefs['mainWindow.initialStation'],
        prefs['mainWindow.initialDetector'],
        prefs['mainWindow.initialClipClass'])
    
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
        '--command-set', help='the name of the command set to use')
    
    args = parser.parse_args()
    
    return args


def _get_archive_dir_path(args, prefs):
    
    # TODO: Handle errors more gracefully.
    
    name = args.archive
    if name is None:
        name = prefs['archive']
        
    return prefs['archives'][name]
    
    
def _get_command_set_name(args, prefs):
    
    # TODO: Handle errors more gracefully.
    
    name = args.command_set
    if name is None:
        name = prefs['clipsWindow.defaultCommandSet']
        
    return name
        
    
def _set_geometry(window, available_rect):
    
    r = available_rect
    
    w = min(prefs['mainWindow.width'], r.width())
    h = min(prefs['mainWindow.height'], r.height())
    x = (r.width() - w) / 2
    y = (r.height() - h) / 2
    
    window.setGeometry(x, y, w, h)
    

if __name__ == '__main__':
    _main()
