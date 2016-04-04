from PyQt4.QtGui import QHBoxLayout, QComboBox, QFrame, QLabel

import vesper.archive.archive_utils as archive_utils


class QueryFrame(QFrame):
    
    
    def __init__(
            self, parent, archive, station_name=None, detector_name=None,
            clip_class_name=None):
        
        super(QueryFrame, self).__init__(parent)
        
        self._archive = archive
        self._create_form(station_name, detector_name, clip_class_name)
        self._observer = None
        
        
    def _create_form(self, station_name, detector_name, clip_class_name):
        
        texts = [s.name for s in self._archive.stations]
        self._station_combo_box = self._create_combo_box(
            'Station', texts, station_name, self._on_station_changed)
        
        texts = [s.name for s in self._archive.detectors]
        self._detector_combo_box = self._create_combo_box(
            'Detector', texts, detector_name, self._on_detector_changed)
        
        texts = archive_utils.get_clip_class_name_options(self._archive)
        
        self._clip_class_combo_box = self._create_combo_box(
            'Class', texts, clip_class_name, self._on_clip_class_changed)
        
        widgets = [
            ('Station', self._station_combo_box),
            ('Detector', self._detector_combo_box),
            ('Class', self._clip_class_combo_box),
        ]
        
        self._lay_out_widgets(widgets)
        
    
    def _create_combo_box(
            self, label, item_texts, current_text, on_index_changed):
        
        combo_box = QComboBox(self)
        combo_box.addItems(item_texts)
        _set_current_text(combo_box, current_text)
        
        combo_box.currentIndexChanged.connect(on_index_changed)
        
        return combo_box

        
    def _lay_out_widgets(self, pairs):
        
        box = QHBoxLayout()
        
        for (i, (label, widget)) in enumerate(pairs):
            
            box.addWidget(QLabel(label + ':'))
            box.addWidget(widget)
            
            if i == len(pairs) - 1:
                box.addStretch(1)
            else:
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
        return str(self._station_combo_box.currentText())


    @property
    def detector_name(self):
        return str(self._detector_combo_box.currentText())


    @property
    def clip_class_name(self):
        return str(self._clip_class_combo_box.currentText())
    
    
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
        
        
def _set_current_text(combo_box, text):
    if text is not None:
        for i in range(combo_box.count()):
            if combo_box.itemText(i) == text:
                combo_box.setCurrentIndex(i)
