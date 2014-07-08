from __future__ import print_function

from PySide.QtGui import QMainWindow, QVBoxLayout, QWidget

from nfc.archive.archive import Archive
from nfc.ui.clip_count_month_bar_chart import ClipCountMonthBarChart
from nfc.ui.clip_count_archive_calendar import ClipCountArchiveCalendar
from nfc.ui.clip_count_month_calendar import ClipCountMonthCalendar
from nfc.ui.clips_window import ClipsWindow
from nfc.ui.query_frame import QueryFrame
from nfc.util.preferences import preferences as prefs


class MainWindow(QMainWindow):
    
    
    COUNT_DISPLAY_TYPE_MONTH_BAR_CHART = 'month bar chart'
    COUNT_DISPLAY_TYPE_MONTH_CALENDAR = 'month calendar'
    COUNT_DISPLAY_TYPE_ARCHIVE_CALENDAR = 'archive calendar'


    def __init__(
        self, archive_dir_path, count_display_type, station_name,
        detector_name, clip_class_name, month_name=None):
        
        super(MainWindow, self).__init__()
        
        self._archive = Archive(archive_dir_path)
        self._archive.open(False)
        
        self._count_display_type = count_display_type
        
        self._create_ui(
            station_name, detector_name, clip_class_name, month_name)
        
        self.setWindowTitle('NFC Viewer')
        
        
    def _create_ui(
        self, station_name, detector_name, clip_class_name, month_name):
        
        widget = QWidget(self)

        self._query_frame = self._create_query_frame(
            widget, station_name, detector_name, clip_class_name, month_name)
                    
        self._date_chooser = self._create_date_chooser(widget)
        self._date_chooser.add_listener(self._on_date_choice)
        self._configure_date_chooser()
        
        box = QVBoxLayout()
        box.addWidget(self._query_frame)
        box.addWidget(self._date_chooser)
        widget.setLayout(box)

        self.setCentralWidget(widget)
        
        
    def _create_query_frame(
        self, parent, station_name, detector_name, clip_class_name,
        month_name):
        
        include_month = self._count_display_type != \
                            MainWindow.COUNT_DISPLAY_TYPE_ARCHIVE_CALENDAR
        
        frame = QueryFrame(
            parent, self._archive, station_name, detector_name,
            clip_class_name, include_month, month_name)
        
        frame.observer = self._on_query_frame_change
        
        return frame

    
    def _create_date_chooser(self, parent):
        
        if self._count_display_type == \
               MainWindow.COUNT_DISPLAY_TYPE_MONTH_BAR_CHART:
            
            return ClipCountMonthBarChart(parent, self._archive)
            
        elif self._count_display_type == \
                 MainWindow.COUNT_DISPLAY_TYPE_MONTH_CALENDAR:
            
            return ClipCountMonthCalendar(parent, self._archive)
            
        else:
            return ClipCountArchiveCalendar(parent, self._archive)

            
    def _on_date_choice(self, date):
        
        f = self._query_frame
        window = ClipsWindow(
            self, self._archive, f.station_name, f.detector_name, date,
            f.clip_class_name)
        
        width = prefs['clipsWindow.width']
        height = prefs['clipsWindow.height']
        window.setGeometry(100, 100, width, height)
        
        window.show()
        
        # This appears to be necessary for Anaconda 1.9.2 on Mac OS X
        # (without it the new clips window does not get keyboard focus,
        # even though it's the topmost window), but not for Canopy 2.7.6.
        # Not sure why.
        window.setFocus()
        
        
    def _configure_date_chooser(self):
        f = self._query_frame
        self._date_chooser.configure(
            f.station_name, f.detector_name, f.clip_class_name,
            f.year, f.month)
        
        
    def _on_query_frame_change(self):
        self._configure_date_chooser()


    # The name of this method is camel case since it comes from Qt.
    def closeEvent(self, event):
        self._archive.close()
        event.accept()
