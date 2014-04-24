"""NFC viewer application."""


from __future__ import print_function

import sys

from PySide.QtGui import QApplication
    
from nfc.ui.main_window import MainWindow
from nfc.util.preferences import preferences as prefs


def _main():
    
    app = QApplication(sys.argv)
    
    window = MainWindow(
        prefs['archiveDirPath'], prefs['mainWindow.countDisplayType'],
        prefs['stationName'], prefs['detectorName'], prefs['clipClassName'],
        prefs['monthName'])
    
    _set_geometry(window, app.desktop().availableGeometry())
    window.show()
    window.activateWindow()
    window.raise_()
    
    app.exec_()
    
    sys.exit()


def _set_geometry(window, available_rect):
    
    r = available_rect
    
    w = min(prefs['mainWindow.width'], r.width())
    h = min(prefs['mainWindow.height'], r.height())
    x = (r.width() - w) / 2
    y = (r.height() - h) / 2
    
    window.setGeometry(x, y, w, h)
    

if __name__ == '__main__':
    _main()
