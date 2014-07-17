from __future__ import print_function

import datetime

from PySide.QtCore import QSize
from PySide.QtGui import QHBoxLayout, QComboBox, QFrame, QLabel, QSizePolicy

from nfc.archive.archive import Archive
import nfc.archive.archive_utils as archive_utils
import nfc.util.calendar_utils as calendar_utils


class QueryFrame(QFrame):
    
    
    def __init__(
        self, parent, archive, station_name=None, detector_name=None,
        clip_class_name=None, include_month=False, month_name=None):
        
        super(QueryFrame, self).__init__(parent)
        
        self._archive = archive

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self._create_form(
            station_name, detector_name, clip_class_name, include_month,
            month_name)
        
        self._observer = None
        
        
    def _create_form(
        self, station_name, detector_name, clip_class_name, include_month,
        month_name):
        
        texts = [s.name for s in self._archive.stations]
        self._station_combo_box = self._create_combo_box(
            'Station', texts, station_name, self._on_station_changed)
        
        texts = [s.name for s in self._archive.detectors]
        self._detector_combo_box = self._create_combo_box(
            'Detector', texts, detector_name, self._on_detector_changed)
        
        texts = self._get_clip_class_texts()
        self._clip_class_combo_box = self._create_combo_box(
            'Class', texts, clip_class_name, self._on_clip_class_changed)
        
        if include_month:
            self._year_month_pairs = \
                archive_utils.get_year_month_pairs(self._archive)
            texts = [calendar_utils.get_year_month_string(*p)
                     for p in self._year_month_pairs]
            self._month_combo_box = self._create_combo_box(
                'Month', texts, month_name, self._on_month_changed)
        else:
            self._year_month_pairs = []
        
        widgets = [
            ('Station', self._station_combo_box),
            ('Detector', self._detector_combo_box),
            ('Class', self._clip_class_combo_box),
        ]
        
        if include_month:
            widgets.append(('Month', self._month_combo_box))
            
        self._lay_out_widgets(widgets)
        
    
    def _create_combo_box(
        self, label, item_texts, current_text, on_current_index_changed):
        
        combo_box = QComboBox(self)
        combo_box.addItems(item_texts)
        _set_current_text(combo_box, current_text)
        
        combo_box.currentIndexChanged.connect(on_current_index_changed)
        
        return combo_box

        
    def _get_clip_class_texts(self):
        
        '''
        Any
        Call
        Call.AMRE
        .
        .
        .
        Call.WTSP
        Call.WTSP.Songtype
        .
        .
        .
        Noise
        Tone
        Unclassified
        
        
        Subclasses:
            Include
            Exclude
            Only
        '''
        
        # TODO: Generate wildcard class names automatically.
        texts = [s.name for s in self._archive.clip_classes] + \
                [Archive.CLIP_CLASS_NAME_ANY,
                 Archive.CLIP_CLASS_NAME_UNCLASSIFIED,
                 'Call*']
        texts.sort()
        return texts
    
        
    def _lay_out_widgets(self, pairs):
        
        box = QHBoxLayout()
            
        for label, widget in pairs:
            
            b = QHBoxLayout()
            b.addWidget(QLabel(label + ':'))
            b.addWidget(widget)
            
            box.addLayout(b)
            box.addSpacing(10)
            
        self.setLayout(box)
        
        
    @property
    def observer(self):
        return self._observer
    
    
    @observer.setter
    def observer(self, observer):
        self._observer = observer
        
        
    @property
    def station_name(self):
        return self._station_combo_box.currentText()


    @property
    def detector_name(self):
        return self._detector_combo_box.currentText()


    @property
    def clip_class_name(self):
        return self._clip_class_combo_box.currentText()
    
    
    @property
    def year(self):
        return self._get_current_year_month_pair_item(0)
    
    
    def _get_current_year_month_pair_item(self, i):
        pairs = self._year_month_pairs
        if len(pairs) == 0:
            return None
        else:
            month = self._month_combo_box.currentIndex()
            return pairs[month][i]
     
     
    @property
    def month(self):
        return self._get_current_year_month_pair_item(1)
     
     
    @property
    def date(self):
        if len(self._year_month_pairs) == 0:
            return None
        else:
            return datetime.date(self.year, self.month, 1)


    def _on_station_changed(self, i):
        self._update()
        
        
    def _on_detector_changed(self, i):
        self._update()
        
        
    def _on_clip_class_changed(self, i):
        self._update()
        
        
    def _on_month_changed(self, i):
        self._update()
        
        
    def _update(self):
        if self.observer is not None:
            self.observer()
        
        
    # TODO: Figure out what we should really do here, and with the
    # `setSizePolicy` call in the `__init__` method, to get what we
    # want (if possible), which is a query frame that hugs its
    # content horizontally. We also do not want the splitter frame
    # that holds a query frame to expand the query frame horizontally
    # when the splitter frame grows.
    def sizeHint(self):
        return QSize(0, -1)
    
    
def _set_current_text(combo_box, text):
    if text is not None:
        for i in xrange(combo_box.count()):
            if combo_box.itemText(i) == text:
                combo_box.setCurrentIndex(i)
