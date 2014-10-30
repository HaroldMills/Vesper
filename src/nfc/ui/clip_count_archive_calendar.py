from __future__ import print_function

import calendar

from PyQt4.QtGui import QFrame, QGridLayout

from nfc.ui.clip_count_month_calendar import ClipCountMonthCalendar
from nfc.util.notifier import Notifier
import nfc.archive.archive_utils as archive_utils


# TODO: Scroll bars for big calendars?


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
        # pairs = [(2014, i) for i in xrange(7, 13)]
        return [self._create_month_calendar(*p) for p in pairs]
    
    
    def _create_month_calendar(self, year, month):
        calendar = ClipCountMonthCalendar(self, self._archive)
        calendar.configure(self._station_name, self._detector_name,
                           self._clip_class_name, year, month)
        calendar.add_listener(self._notifier.notify_listeners)
        return calendar
        
        
    def _lay_out_month_calendars(self):
        
        calendars = self._month_calendars
        num_months = len(calendars)
        
        if num_months != 0:
        
            grid = QGridLayout()

            if num_months <= 3:
                # three or fewer months in calendar
                
                # Put months in a single row.
                num_cols = num_months
                row_num = 0
                for i, calendar in enumerate(calendars):
                    grid.addWidget(calendar, row_num + 1, i + 1)
        
            else:
                # more than three months in calendar
                
                # Put months in columns as in a 12-month calendar.
                num_cols = 3
                start_col_num = (calendars[0].month - 1) % num_cols
                for i, calendar in enumerate(calendars):
                    col_num = (start_col_num + i) % num_cols
                    row_num = (start_col_num + i) // num_cols
                    grid.addWidget(calendar, row_num + 1, col_num + 1)
                    
            num_rows = row_num + 1
            
            # Put stretchy columns to left and right of calendar and
            # stretchy rows above and below. This will cause the
            # calendar to be centered in the available space.
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(num_cols + 1, 1)
            grid.setRowStretch(0, 1)
            grid.setRowStretch(num_rows + 1, 1)
            
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
