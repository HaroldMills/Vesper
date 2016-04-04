import calendar
import collections

from PyQt4.QtCore import QSize, Qt
from PyQt4.QtGui import QFrame, QGridLayout, QLabel, QVBoxLayout

from vesper.ui.clip_count_month_calendar import ClipCountMonthCalendar
from vesper.util.notifier import Notifier


_CALENDAR_GAP_THRESHOLD = 2
_CALENDAR_BOX_CONTENTS_MARGIN = 40
_CALENDAR_BOX_SPACING = 40
_PERIOD_BOX_CONTENTS_MARGIN = 0
_PERIOD_BOX_SPACING = 20
_GRID_CONTENTS_MARGIN = 0
_GRID_SPACING = 0
_EXTRA_SIZE = 20
_MAX_SIZE_HINT_HEIGHT = 750


class ClipCountArchiveCalendar(QFrame):
    
    
    Period = collections.namedtuple('Period', ('name', 'month_calendars'))


    def __init__(self, parent, archive):
        
        super(ClipCountArchiveCalendar, self).__init__(parent)
        
        self._archive = archive
        
        self._station_name = None
        self._detector_name = None
        self._clip_class_name = None
        
        self._notifier = Notifier()
        
        self._periods = self._create_periods()
#        self._periods = self._create_test_periods([(3, 7), (8, 10)])
        self._lay_out_calendar()
        

    def _create_periods(self):
        
        # Get nights for which there are clips.
        counts = self._archive.get_clip_counts()
        nights = sorted(counts.keys())
        
        # Get (year, month) pairs for which there are clips.
        pairs = list(frozenset((n.year, n.month) for n in nights))
        pairs.sort()
        
        # Get calendar periods.
        spans = _get_calendar_spans(pairs)
        periods = [self._create_period(*s) for s in spans]
        
        return periods
    
    
    def _create_test_periods(self, periods):
        return [self._create_test_period(start, end) for start, end in periods]


    def _create_test_period(self, start_month_num, end_month_num):
        start_month_num = _normalize_test_month_num(start_month_num)
        end_month_num = _normalize_test_month_num(end_month_num)
        return self._create_period(start_month_num, end_month_num)
        
        
    def _create_period(self, start_month_num, end_month_num, name=None):
        
        if name is None:
            name = _create_period_name(start_month_num, end_month_num)
            
        month_calendars = \
            self._create_month_calendars(start_month_num, end_month_num)
            
        return ClipCountArchiveCalendar.Period(name, month_calendars)

        
    def _create_month_calendars(self, start_month_num, end_month_num):
        range_ = range(start_month_num, end_month_num + 1)
        pairs = [_to_pair(i) for i in range_]
        return [self._create_month_calendar(*p) for p in pairs]
    
    
    def _create_month_calendar(self, year, month):
        calendar = ClipCountMonthCalendar(self, self._archive)
        calendar.configure(self._station_name, self._detector_name,
                           self._clip_class_name, year, month)
        calendar.add_listener(self._notifier.notify_listeners)
        return calendar
        
        
    def _lay_out_calendar(self):
        
        periods = self._periods
        
        cbox = _create_layout(
            QVBoxLayout, _CALENDAR_BOX_CONTENTS_MARGIN, _CALENDAR_BOX_SPACING)
        
        for period in periods:
        
            pbox = _create_layout(
                QVBoxLayout, _PERIOD_BOX_CONTENTS_MARGIN, _PERIOD_BOX_SPACING)
            
            label = QLabel(period.name)
            font = label.font()
            font.setPointSize(25)
            label.setFont(font)
            pbox.addWidget(label, alignment=Qt.AlignLeft)
            
            calendars = period.month_calendars
            num_months = len(calendars)

            if num_months <= 3:
                # three or fewer months in period
                
                # Put months in a single row.
                num_cols = num_months
                start_col_num = 0
                
            else:
                # more than three months in period
                
                # Put months in columns as in a 12-month calendar.
                num_cols = 3
                start_col_num = (calendars[0].month - 1) % num_cols
                
            grid = _create_layout(
                QGridLayout, _GRID_CONTENTS_MARGIN, _GRID_SPACING)
            
            for i, calendar in enumerate(calendars):
                n = start_col_num + i
                col_num = n % num_cols
                row_num = n // num_cols
                grid.addWidget(calendar, row_num, col_num)
                    
            # Put stretchy column to right of calendar so month calendars
            # remain to the left when extra space is available.
            grid.setColumnStretch(num_cols, 1)

            pbox.addLayout(grid)
            cbox.addLayout(pbox)
            
        self.setLayout(cbox)
        
        self._layout = cbox

        
    @property
    def station_name(self):
        return self._station_name
    
    
    @property
    def detector_name(self):
        return self._detector_name
    
    
    @property
    def clip_class_name(self):
        return self._clip_class_name
    
    
    def configure(self, station_name, detector_name, clip_class_name):
        
        self._station_name = station_name
        self._detector_name = detector_name
        self._clip_class_name = clip_class_name
        
        for period in self._periods:
            for c in period.month_calendars:
                c.configure(self.station_name, self.detector_name,
                            self.clip_class_name, c.year, c.month)
            
            
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
        
        
    def remove_listener(self, listener):
        self._notifier.remove_listener(listener)
        
        
    def clear_listeners(self):
        self._notifier.clear_listeners()


    @property
    def scroll_area_size_hint(self):
        size = self._layout.sizeHint()
        width = size.width() + _EXTRA_SIZE
        height = min(size.height() + _EXTRA_SIZE, _MAX_SIZE_HINT_HEIGHT)
        return QSize(width, height)
     

def _get_calendar_spans(year_month_pairs):
    
    # Convert (year, month) pairs to month numbers.
    month_nums = [_to_month_num(*p) for p in year_month_pairs]
    
    if len(month_nums) == 0:
        return []
    
    else:
        # have at least one month
        
        spans = []
        
        # Start a span at the first month.
        start_month_num = month_nums[0]
        prev_month_num = month_nums[0]
        
        for month_num in month_nums[1:]:
            
            num_empty_months = month_num - prev_month_num - 1
            
            if num_empty_months >= _CALENDAR_GAP_THRESHOLD:
                # enough empty months to warrant a calendar gap
                
                # End current span and start another.
                spans.append((start_month_num, prev_month_num))
                start_month_num = month_num
                
            prev_month_num = month_num
            
        # End current span.
        spans.append((start_month_num, prev_month_num))
        
        return spans


def _to_month_num(year, month, year_zero=1900):
    return (year - year_zero) * 12 + month - 1


def _to_pair(month_num, year_zero=1900):
    year = year_zero + month_num // 12
    month = month_num % 12 + 1
    return (year, month)

 
def _normalize_test_month_num(month_num):
    pair = _to_pair(month_num - 1, year_zero=2014)
    return _to_month_num(*pair)
    
    
_MONTH_NAMES = (
    None,
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
)


def _create_period_name(start_month_num, end_month_num):
    
    start_year, start_month = _to_pair(start_month_num)
    end_year, end_month = _to_pair(end_month_num)
    
    if start_month_num == end_month_num:
        return '{:s} {:d}'.format(_MONTH_NAMES[start_month], start_year)
        
    else:
        
        start_name = _MONTH_NAMES[start_month]
        end_name = _MONTH_NAMES[end_month]
        
        if start_year == end_year:
            return '{:s}-{:s} {:d}'.format(
                start_name, end_name, start_year)
        
        else:
            return '{:s} {:d} - {:s} {:d}'.format(
                start_name, start_year, end_name, end_year)
    
        
def _create_layout(klass, contents_margin, spacing):
    layout = klass()
    m = contents_margin
    layout.setContentsMargins(m, m, m, m)
    layout.setSpacing(spacing)
    return layout


def _get_size_dim(num_calendars, calendar_size):
    n = num_calendars
    s = (calendar_size + 2 * _GRID_CONTENTS_MARGIN)
    return n * s + (n - 1) * _GRID_SPACING + _EXTRA_SIZE
