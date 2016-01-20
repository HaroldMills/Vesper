"""Vesper viewer application."""


from __future__ import print_function
import argparse
import os
import sys

from PyQt4.QtGui import QApplication
    
from vesper.ui.main_window import MainWindow
import vesper.util.preferences as prefs


def _main():
    
    args = _parse_args()
    _load_preferences(args.preferences)
    archive_dir_path = _get_archive_dir_path(args)
    commands_preset_name = _get_commands_preset_name(args)

    # This must happen before any other QT operations, including
    # creating the main window.
    app = QApplication(sys.argv)
    
    window = MainWindow(
        archive_dir_path,
        prefs.get('mainWindow.initialStation'),
        prefs.get('mainWindow.initialDetector'),
        prefs.get('mainWindow.initialClipClass'),
        commands_preset_name)
    
    _set_geometry(window, app.desktop().availableGeometry())
    
    window.show()
    window.activateWindow()
    window.raise_()
    
    app.exec_()
    
    sys.exit()


def _parse_args():
    
    parser = argparse.ArgumentParser(description='Vesper Viewer')
    
    parser.add_argument(
        '--preferences',
        help='the name of the preferences file to use')
    
    parser.add_argument(
        '--archive',
        help='the directory path of the archive to view')
    
    parser.add_argument(
        '--classification-commands',
        help='the name of the commands preset to use')
    
    args = parser.parse_args()
    
    return args


def _load_preferences(file_name):
    if file_name is not None:
        prefs.load_preferences(file_name)
    else:
        prefs.load_preferences()


def _get_archive_dir_path(args):
    
    path = args.archive
    
    if path is None:
        return os.getcwd()
    else:
        return path
    
    
def _get_commands_preset_name(args):
    
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
