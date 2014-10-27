from __future__ import print_function

import calendar

from PyQt4.QtGui import QFrame, QGridLayout

from nfc.ui.clip_count_month_calendar import ClipCountMonthCalendar
from nfc.util.notifier import Notifier
import nfc.archive.archive_utils as archive_utils


# TODO: Constrain figure canvas size according to number of calendar
# rows? (Vertical scroll bar?)


class ClipCountArchiveCalendar(QFrame):
    
    
    def __init__(self, parent, archive):
        
        super(ClipCountArchiveCalendar, self).__init__(parent)
        
        self._archive = archive
        
        self._station_name = None
        self._detector_name = None
        self._clip_class_name = None
        
        self._notifier = Notifier()
        
        self._month_calendars = self._create_month_calendars()
        
        self._lay_out_month_calendars()
        


    def _create_month_calendars(self):
        pairs = archive_utils.get_year_month_pairs(self._archive)
        return [self._create_month_calendar(*p) for p in pairs]
    
    
    def _create_month_calendar(self, year, month):
        calendar = ClipCountMonthCalendar(self, self._archive)
        calendar.configure(self._station_name, self._detector_name,
                           self._clip_class_name, year, month)
        calendar.add_listener(self._notifier.notify_listeners)
        return calendar
        
        
    def _lay_out_month_calendars(self):
        
        grid = QGridLayout()
        
        calendars = self._month_calendars
        
        if len(calendars) > 0:
        
            num_cols = 3
            start_col_num = (calendars[0].month - 1) % num_cols
        
            for i, calendar in enumerate(calendars):
                
                col_num = (start_col_num + i) % num_cols
                row_num = (start_col_num + i) // num_cols
                
                grid.addWidget(calendar, row_num, col_num)
                
        self.setLayout(grid)
        
        
    @property
    def station_name(self):
        return self._station_name
    
    
    @property
    def detector_name(self):
        return self._detector_name
    
    
    @property
    def clip_class_name(self):
        return self._clip_class_name
    
    
    def configure(
        self, station_name, detector_name, clip_class_name, year, month):
        
        self._station_name = station_name
        self._detector_name = detector_name
        self._clip_class_name = clip_class_name
        
        for c in self._month_calendars:
            c.configure(self.station_name, self.detector_name,
                        self.clip_class_name, c.year, c.month)
            
            
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
        
        
    def remove_listener(self, listener):
        self._notifier.remove_listener(listener)
        
        
    def clear_listeners(self):
        self._notifier.clear_listeners()
