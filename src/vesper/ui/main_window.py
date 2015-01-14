from __future__ import print_function

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMainWindow, QScrollArea, QVBoxLayout, QWidget

from vesper.archive.archive import Archive
from vesper.ui.clip_count_archive_calendar import ClipCountArchiveCalendar
from vesper.ui.clips_window import ClipsWindow
from vesper.ui.query_frame import QueryFrame
from vesper.util.preferences import preferences as prefs


class MainWindow(QMainWindow):
    
    
    def __init__(
            self, archive_dir_path, station_name, detector_name,
            clip_class_name, commands_preset_name):
        
        super(MainWindow, self).__init__()
        
        self._archive = Archive(archive_dir_path)
        self._archive.open(False)
        
        self.setWindowTitle('Vesper Viewer - {:s}'.format(self._archive.name))
        self._create_ui(station_name, detector_name, clip_class_name)
        
        self._commands_preset_name = commands_preset_name
        
        
    def _create_ui(self, station_name, detector_name, clip_class_name):
        
        widget = QWidget(self)

        self._query_frame = self._create_query_frame(
            widget, station_name, detector_name, clip_class_name)
                    
        self._date_chooser = ClipCountArchiveCalendar(widget, self._archive)
        self._date_chooser.add_listener(self._on_date_choice)
        self._configure_date_chooser()
        
        scroll_area = _CalendarScrollArea(self._date_chooser)
        
        box = QVBoxLayout()
        box.addWidget(self._query_frame)
        box.addWidget(scroll_area)
        widget.setLayout(box)

        self.setCentralWidget(widget)
        
        
    def _create_query_frame(
            self, parent, station_name, detector_name, clip_class_name):
        
        frame = QueryFrame(
            parent, self._archive, station_name, detector_name,
            clip_class_name)
        
        frame.observer = self._on_query_frame_change
        
        return frame

    
    def _on_date_choice(self, date):
        
        f = self._query_frame
        window = ClipsWindow(
            self, self._archive, f.station_name, f.detector_name, date,
            f.clip_class_name, self._commands_preset_name)
        
        width = prefs['clipsWindow.width']
        height = prefs['clipsWindow.height']
        window.setGeometry(100, 100, width, height)
        
        openMaximized = prefs.get('clipsWindow.maximize')
        if openMaximized:
            window.showMaximized()
        else:
            window.show()
        

    def _configure_date_chooser(self):
        f = self._query_frame
        self._date_chooser.configure(
            f.station_name, f.detector_name, f.clip_class_name)
        
        
    def _on_query_frame_change(self):
        self._configure_date_chooser()


    # The name of this method is camel case since it comes from Qt.
    def closeEvent(self, event):
        self._archive.close()
        event.accept()


class _CalendarScrollArea(QScrollArea):
    
    """Scroll area for archive calendar, including size hint."""
    
    
    def __init__(self, calendar):
        super(_CalendarScrollArea, self).__init__()
        self.setWidget(calendar)
        self.setAlignment(Qt.AlignCenter)
        
        
    def sizeHint(self):
        return self.widget().scroll_area_size_hint
