from __future__ import print_function

import math
import operator

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QApplication, QBrush, QColor, QComboBox, QCursor, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QPainter, QStatusBar, QVBoxLayout,
    QWidget)
import numpy as np

from vesper.ui.clip_times_rug_plot import ClipTimesRugPlot
from vesper.ui.flow_layout import FlowLayout
from vesper.ui.multiselection import Multiselection
from vesper.ui.spectrogram_clip_figure import \
    SpectrogramClipFigure as ClipFigure
from vesper.util.bunch import Bunch
from vesper.util.preset_manager import preset_manager
import vesper.util.preferences as prefs


_SPACING_ASPECT_RATIO = 2
"""ratio of vertical clip spacing to minimum horizontal spacing."""


class ClipsWindow(QMainWindow):
    
    
    def __init__(
            self, parent, archive, station_name, detector_name, night,
            clip_class_name, commands_preset_name):
        
        super(ClipsWindow, self).__init__(parent)
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self._archive = archive
        
        self._create_ui()
        
        self._init_commands(commands_preset_name)
        
        self.set_clips(station_name, detector_name, night, clip_class_name)
        
        date = str(self._date.day) + ' ' + self._date.strftime('%B %Y')
        title = '{:s} - {:s} - {:s} - {:s}'.format(
            self._archive.name, self._station_name, self._detector_name, date)
        self.setWindowTitle(title)
        
                
    def _create_ui(self):
        parent = QWidget(self)
        self._create_ui_components(parent)
        self._lay_out_ui_components(parent)
        
        
    def _create_ui_components(self, parent):
        
        (self._commands_combo_box, self._commands_indices,
         self._commands_presets) = \
            _create_preset_combo_box(
                self, 'Classification Commands', self._on_commands_changed)
        self._commands_combo_box.setFocusPolicy(Qt.NoFocus)

        self._title_label = QLabel(parent)
        self._title_label.setAlignment(Qt.AlignCenter)

        self._rug_plot = ClipTimesRugPlot(parent, self.move_to_page)
        
        config = Bunch(
            clips_area_width=prefs.get('clips_window.duration'),
            clip_spacing=prefs.get('clips_window.spacing'),
            num_rows=prefs.get('clips_window.num_rows'),
            min_clip_height=40,
            selection_rect_thickness=3,
            selection_rect_color='red'
        )
        self._figures_frame = _FiguresFrameWithFlowLayout(parent, config)
        
        self._status_bar = QStatusBar()
        
        
    def _lay_out_ui_components(self, parent):
        
        grid = QGridLayout()
        grid.setContentsMargins(20, 0, 20, 0)
        grid.addWidget(self._title_label, 0, 1, Qt.AlignHCenter)
        
        if self._commands_combo_box is not None:
            box = QHBoxLayout()
            box.addWidget(QLabel('Commands:', parent))
            box.addWidget(self._commands_combo_box)
            grid.addLayout(box, 0, 2, Qt.AlignRight)
            
        for i in xrange(3):
            grid.setColumnMinimumWidth(i, 10)
            grid.setColumnStretch(i, 1)
        
        hBox = QHBoxLayout()
        hBox.addSpacing(20)
        hBox.addWidget(self._rug_plot.canvas)
        hBox.addSpacing(20)
        
        box = QVBoxLayout()
        box.addLayout(grid)
        box.addLayout(hBox)
        box.addWidget(self._figures_frame, stretch=1)
        
        parent.setLayout(box)
        
        # We set the left, right, and bottom margins of the box layout
        # to zero since we will lay out the figures of the figure frame
        # ourselves. It seems to be important to set the margins after
        # the call to `self.setLayout` rather than before since before
        # the call the margins are all zero.
        margins = box.contentsMargins()
        margins.setLeft(0)
        margins.setRight(0)
        margins.setBottom(0)
        box.setContentsMargins(margins)

        self.setCentralWidget(parent)
        self.setStatusBar(self._status_bar)

    
    def _on_commands_changed(self, index):
        self._update_commands_preset(index)
        
        
    def _update_commands_preset(self, index):
        preset = self._commands_presets[index]
        self._commands = preset.commands
        
        
    def _init_commands(self, preset_name):
        
        if self._commands_combo_box is not None:
            
            self._clip_classes = self._create_clip_classes_dict()
            
            index = 0
            
            if preset_name is not None:
                
                try:
                    index = self._commands_indices[preset_name]
                    
                except KeyError:
                    # TODO: Log error.
                    pass
                    
            if self._commands_combo_box.currentIndex() == index:
                self._update_commands_preset(index)
                
            else:
                self._commands_combo_box.setCurrentIndex(index)
                
        else:
            # no commands presets
            
            self._classification_dict = {}
        
        
    def _create_clip_classes_dict(self):
        return dict((c.name, c) for c in self._archive.clip_classes)
    
    
    def set_clips(self, station_name, detector_name, date, clip_class_name):

        # TODO: Does this make sense? Think about what `None` arguments
        # mean and whether or not we actually support them (it seems like
        # we currently don't, except perhaps for the clip class name).
        if station_name is None or detector_name is None or \
           date is None or clip_class_name is None:
            
            self._clips = []
            
        else:
            # Update clips.
            # TODO: Handle `getClips` failure gracefully.
            # TODO: Get clips on a separate thread so UI thread can
            # keep running. Set clips on self._figures_frame on UI thread
            # when that thread completes.
            print('getting clips from archive...')
            self._clips = self._archive.get_clips(
                station_name, detector_name, date, clip_class_name)
        
        self._station_name = station_name
        self._detector_name = detector_name
        self._date = date
        self._clip_class_name = clip_class_name
        
        print('updating UI...')
        self._update_ui()
        
        print('done')
        
        
    def _update_ui(self):
        frame = self._figures_frame
        frame.clips = self._clips
        self._rug_plot.set_clips(self._clips, frame.page_start_indices)
        self._update_title()
        

    def _update_title(self):
        
        if self._station_name is None or self._detector_name is None or \
           self._date is None or self._clip_class_name is None:
            
            title = 'No Clips'
            
        else:
            title = self._create_clips_string()

        self._rug_plot.current_page_num = self._figures_frame.page_num
        self._title_label.setText(title)

        
    def _create_clips_string(self):
        
        frame = self._figures_frame
        n = len(self._clips)
        
        if n == 0:
            return 'No {:s} Clips'.format(self._clip_class_name)
        
        else:
            
            first = frame.first_visible_clip_num
            last = min(first + frame.num_visible_clips - 1, n - 1)
            
            if first == last:
                return '{:s} Clip {:d} of {:d}'.format(
                    self._clip_class_name, first + 1, n)
            
            else:
                return '{:s} Clips {:d}-{:d} of {:d}'.format(
                    self._clip_class_name, first + 1, last + 1, n)
    
        
    def keyPressEvent(self, e):
        
        command_name = _get_command_from_key_event(e)
        
        if command_name is not None:

            command = self._commands.get(command_name)
            
            if command is not None:
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                self._figures_frame.execute_command(command)
                QApplication.restoreOverrideCursor()
                self._update_title()
                
            else:
                # key is not a classification command
                
                self._key_press_event(e)
                
        
        else:
            # key is not a classification command
            
            self._key_press_event(e)
            
            
    def _key_press_event(self, e):
        
        is_key = _is_key
        
        if is_key(e, Qt.Key_Space) or is_key(e, Qt.Key_PageDown):
            self.move_down_one_page()
            
        elif is_key(e, Qt.Key_Space, Qt.ShiftModifier) or \
                is_key(e, Qt.Key_PageUp):
            
            self.move_up_one_page()
            
        elif is_key(e, Qt.Key_Tab):
            self.move_singleton_selection_forward()
            
        # Note that when the user presses the tab key with the shift
        # key held down, the event we get is for the backtab key
        # rather than the tab key, with the shift modifier.
        elif is_key(e, Qt.Key_Backtab, Qt.ShiftModifier):
            self.move_singleton_selection_backward()
            
        else:
            super(ClipsWindow, self).keyPressEvent(e)

    
    def move_down_one_page(self):
        self._figures_frame.move_down_one_page()
        self._update_title()
                        
            
    def move_up_one_page(self):
        self._figures_frame.move_up_one_page()
        self._update_title()
        
        
    def move_to_page(self, page_num):
        self._figures_frame.move_to_page(page_num)
        self._update_title()
        
        
    def move_singleton_selection_forward(self):
        self._figures_frame.move_singleton_selection_forward()
        self._update_title()


    def move_singleton_selection_backward(self):
        self._figures_frame.move_singleton_selection_backward()
        self._update_title()


_MODIFIER_PAIRS = [('Alt', Qt.AltModifier)]
"""
list of recognized (modifier name, QT keyboard modifier flag) pairs,
excluding shift.

Note that we do *not* allow classification commands that use the control
modifier (i.e. the control key on Linux and Windows and the command key
on Mac OS X) since they could collide with menu item keyboard accelerators.
"""

_ALL_MODIFIERS = reduce(
    operator.or_, [m for _, m in _MODIFIER_PAIRS], Qt.ShiftModifier)
"""disjunction of recognized command modifiers, including shift."""


def _get_command_from_key_event(key_event):
    
    char = str(key_event.text())
    
    if char == '':
        return None
    
    else:
        
        modifiers = key_event.modifiers()
        
        if modifiers | _ALL_MODIFIERS != _ALL_MODIFIERS:
            # unrecognized modifier present
            return None
            
        mods = ''.join(s + '-' for s, m in _MODIFIER_PAIRS if modifiers & m)
        
        return mods + char
    
    
def _is_key(key_event, key, modifiers=Qt.NoModifier):
     
    if key_event.key() != key:
        return False
     
    else:
        return key_event.modifiers() == modifiers


class _FiguresFrame(QWidget):
    
    
    def __init__(self, parent, config):
        
        super(_FiguresFrame, self).__init__(parent)

#        self.setStyleSheet('QFrame { background-color: red }')
        
        self._num_rows = config.num_rows
        self._selection_rect_thickness = config.selection_rect_thickness
        self._selection_rect_color = config.selection_rect_color
        
        self._first_visible_row_num = None
        self._inactive_clip_frames = []
        self._active_clip_frames = []
        
        # We leave the initial setting of `self._clips` and
        # `self._selection` to subclass initializers since that
        # process often uses subclass instance data that have not
        # yet been initialized when this method runs.


    @property
    def num_rows(self):
        return self._num_rows


    @property
    def clips(self):
        return self._clips
    
    
    @clips.setter
    def clips(self, clips):
        # self._show_clip_durs(clips)
        self._set_clips(clips)


    def _show_clip_durs(self, clips):
        sounds = [c.sound for c in clips]
        durs = [len(s.samples) / s.sample_rate for s in sounds]
        durs.sort()
        if len(durs) > 0:
            print('_FigureFrame', durs[0], durs[-1])
            
           
    def _set_clips(self, clips):
        raise NotImplementedError()
    
    
    @property
    def selection(self):
        return self._selection
    
    
    @property
    def total_num_rows(self):
        raise NotImplementedError()
        
        
    @property
    def max_first_visible_row_num(self):
        if self.total_num_rows == 0:
            return None
        else:
            return max(0, self.total_num_rows - self.num_rows)
    
    
    @property
    def first_visible_row_num(self):
        return self._first_visible_row_num
            
        
    @first_visible_row_num.setter
    def first_visible_row_num(self, n):
        if self.total_num_rows != 0:
            self._set_first_visible_row_num(n)
        
        
    def _set_first_visible_row_num(self, n, force_update=False):
        
        n = max(n, 0)
        n = min(n, self.total_num_rows - 1)
        
        if n != self._first_visible_row_num or force_update:
            
            self._first_visible_row_num = n
            
            clip_num = self._get_first_clip_num_of_row(n)
            clips = self._clips[clip_num:clip_num + self.num_visible_clips]
            
            self._activate_clip_frames(clips)
            
    
    @property
    def first_visible_clip_num(self):
        n = self.first_visible_row_num
        return self._get_first_clip_num_of_row(n) if n is not None else None
    
    
    def _get_first_clip_num_of_row(self, n):
        raise NotImplementedError()
    
    
    @property
    def num_visible_clips(self):
        
        if self.total_num_rows == 0:
            return 0
        
        else:
            # have some clips
            
            clip_num = self._get_first_clip_num_of_row(
                self.first_visible_row_num + self.num_rows)
            
            if clip_num is None:
                return len(self._clips) - self.first_visible_clip_num
            
            else:
                return clip_num - self.first_visible_clip_num
    
    
    @property
    def num_pages(self):
        return int(math.ceil(self.total_num_rows / float(self.num_rows)))
    
    
    @property
    def page_start_indices(self):
        return [self._get_first_clip_num_of_row(i * self.num_rows)
                for i in xrange(self.num_pages)]
        
        
    @property
    def page_num(self):
        clip_num = self.first_visible_clip_num
        if clip_num is None:
            return None
        else:
            return np.searchsorted(
                self.page_start_indices, clip_num, side='right') - 1
            
            
    def execute_command(self, command):
        
        action, scope = command
        
        if scope == 'All':
            intervals = ((0, len(self._clips) - 1),)
            self._execute_action(action, intervals)
            
        else:
            
            if self.num_visible_clips == 0:
                return
            
            first = self.first_visible_clip_num
            
            if scope == 'Page':
                intervals = ((first, first + self.num_visible_clips - 1),)
            else:
                intervals = _shift(self.selection.selected_intervals, first)
                
            self._execute_action(action, intervals)
            
            if prefs.get('clips_window.advance_after_classification'):
                self._advance_after_classification(scope)
                
                            
    def _execute_action(self, action, intervals):
        
        first = self.first_visible_clip_num
            
        for i, j in intervals:
            
            for k in xrange(i, j + 1):
                
                clip = self._clips[k]
                
                action.execute(clip)
                
                if k >= first and k < first + self.num_visible_clips:
                
                    # TODO: Find a better way to update clip frames.
                    # The figures frame should not access private clip
                    # frame members as in the code below. Perhaps clips
                    # should support observers, and a clip frame should
                    # observe its clip and update its clip text when the
                    # clip changes.
                    frame = self._active_clip_frames[k - first]
                    figure = frame._clip_figure
                    figure._update_clip_text()
                    

    def _advance_after_classification(self, scope):
        
        if scope == 'Selected':
            self.move_singleton_selection_forward()
                
        elif scope == 'Page':
                    
            last_visible_clip_num = \
                self.first_visible_clip_num + self.num_visible_clips - 1
            
            if last_visible_clip_num != len(self._clips) - 1:
                # there are more clips
                
                self.move_down_one_page()
                
        
    def move_down_one_page(self):
        if self.first_visible_row_num + self.num_rows < self.total_num_rows:
            self._move_by_num_rows(self.num_rows)
        
    
    def _move_by_num_rows(self, num_rows):
        if self.total_num_rows != 0:
            self.first_visible_row_num += num_rows
            
            
    def move_up_one_page(self):
        self._move_by_num_rows(-self.num_rows)
        
    
    def move_to_page(self, page_num):
        if self.total_num_rows != 0:
            if page_num < 0:
                page_num = 0
            elif page_num >= self.num_pages:
                page_num = self.num_pages - 1
            self.first_visible_row_num = page_num * self.num_rows
            
            
    def move_singleton_selection_forward(self):
        
        intervals = self.selection.selected_intervals
        
        if _is_singleton(intervals):
            
            clip_num = self.first_visible_clip_num + intervals[0][0]
            
            last_visible_clip_num = \
                self.first_visible_clip_num + self.num_visible_clips - 1
            
            if clip_num != last_visible_clip_num:
                # selected clip is not last on this page
                
                self._select_clip(clip_num + 1)

            elif clip_num != len(self._clips) - 1:
                # there are clips after this page
                
                self.move_down_one_page()
                self._select_clip(clip_num + 1)
                
                
    def _select_clip(self, clip_num):
        
        self.selection.select(clip_num - self.first_visible_clip_num)
        
        # TODO: Should selections be observable, so that we
        # can observe the selection and update our graphical
        # representation of it when it changes?
        self._update_clip_frame_selection_states()
        

    def _update_clip_frame_selection_states(self):
        for frame in self._active_clip_frames:
            frame.selected = frame.index in self.selection


    def move_singleton_selection_backward(self):

        intervals = self.selection.selected_intervals
        
        if _is_singleton(intervals):
            
            clip_num = self.first_visible_clip_num + intervals[0][0]
            
            if clip_num != self.first_visible_clip_num:
                # selected clip is not first on this page
                
                self._select_clip(clip_num - 1)

            elif clip_num != 0:
                # there are clips before this page
                
                self.move_up_one_page()
                self._select_clip(clip_num - 1)
                
                
    def _handle_selection_event(self, figure_frame, event):
        
        index = figure_frame.index
        selection = self._selection
        
        if _control_down(event):
            selection.toggle(index)
            
        elif _shift_down(event):
            selection.extend(index)
            
        else:
            selection.select(index)
            
        self._update_clip_frame_selection_states()
            
        self.setFocus()


def _shift(intervals, n):
    return tuple([(i + n, j + n) for i, j in intervals])


def _is_singleton(intervals):
    
    if len(intervals) != 1:
        return False
    
    else:
        start, end = intervals[0]
        return start == end
    

class _FiguresFrameWithFlowLayout(_FiguresFrame):
    
    
    def __init__(self, parent, config, **kwargs):
        
        super(_FiguresFrameWithFlowLayout, self).__init__(
            parent, config, **kwargs)
        
        # This helps prevent clip frames for short clips from winding
        # up with zero width, which causes problems on Windows. It is
        # not really a solution to that problem. It can be removed
        # when issue #31 is addressed.
        self.setMinimumSize(500, 300)
        
        # clip layout parameters
        self._clips_area_width = config.clips_area_width
        self._clip_spacing = config.clip_spacing
        self._min_clip_height = config.min_clip_height
        
        self.clips = []
        
        
    def _set_clips(self, clips):
        
        self._clips = clips
        
        self._layout = self._assign_clips_to_rows()

        if self.total_num_rows == 0:
            self._deactivate_clip_frames()
            self._first_visible_row_num = None
            self._selection = None
            
        else:
            self._set_first_visible_row_num(0, force_update=True)
        
            
    def _assign_clips_to_rows(self):
        durations = [clip.duration for clip in self._clips]
        width = self._clips_area_width
        layout = FlowLayout(width, width * self._clip_spacing)
        return layout.lay_out_items(durations)
        
        
    def _deactivate_clip_frames(self):
        
        for frame in self._active_clip_frames:
            frame.hide()
            frame.clip = None
            frame.selected = False
            
        self._inactive_clip_frames += self._active_clip_frames
        self._active_clip_frames = []
        
        
    def _activate_clip_frames(self, clips):
        
        self._deactivate_clip_frames()
        
        m = self._first_visible_row_num
        num_frames = sum(n for (_, n) in self._layout[m:m + self.num_rows])
        
        inactive_frames = self._inactive_clip_frames
        n = num_frames - len(inactive_frames)
        if n > 0:
            print('    creating clip frames...')
            thickness = self._selection_rect_thickness
            color = self._selection_rect_color
            for _ in xrange(n):
                frame = _FigureFrame(self, thickness, color)
                inactive_frames.append(frame)
        
        print('    setting clips on frames...')
        for i in xrange(num_frames):
            frame = inactive_frames.pop()
            frame.clip = clips[i]
            frame.index = i
#            frame.show()
            self._active_clip_frames.append(frame)
        
        print('    creating selection...')
        self._selection = Multiselection(0, len(clips) - 1)
        
        print('    laying out clip frames...')
        self._lay_out_clips()
        
        print('    showing clip frames...')
        self._show_clip_frames()
        
        print('    done')

    
    # This is a Qt event handler, so don't rename it!
    def resizeEvent(self, event):
        self._lay_out_clips()
            
            
    def _lay_out_clips(self):
        
        if len(self._clips) == 0:
            return
        
        size = self.size()
        clips_frame_width = size.width()
        clips_frame_height = size.height()
        
        min_spacing = 2 * self._selection_rect_thickness
        h_spacing = max(clips_frame_width * self._clip_spacing, min_spacing)
        v_spacing = max(
            clips_frame_height * self._clip_spacing * _SPACING_ASPECT_RATIO,
            min_spacing)
        
        (ys, height) = self._lay_out_clip_rows(clips_frame_height, v_spacing)
        
        num_rows = min(
            self.num_rows, self.total_num_rows - self._first_visible_row_num)
        frame_num = 0
        border_sizes = []
                
        for i in xrange(num_rows):
            
            row_num = self._first_visible_row_num + i
            
            (start_clip_num, num_clips) = self._layout[row_num]
            
            # The `max(clips_frame_width, 1)` in the following prevents
            # division by zero.
            seconds_per_pixel = \
                float(self._clips_area_width) / max(clips_frame_width, 1)
            
            clip_widths = [
                int(round(self._clips[j].duration / seconds_per_pixel))
                for j in xrange(start_clip_num, start_clip_num + num_clips)]
            
            # Under this spacing regime, the space between clips is
            # `h_spacing` and the remaining space is divided equally
            # between the left and right borders.
#             spacing = h_spacing
#             borderSize = (clips_frame_width - sum(clip_widths) - \
#                           (num_clips - 1) * spacing) / 2.
#             borderSize = max(borderSize, min_spacing)
            
            # Under this spacing regime, the space in a row is nominally
            # divided evenly between the borders and the spaces between
            # clips. Rows for which this would cause the spacing to be
            # undesirably large are treated specially.
            space = clips_frame_width - sum(clip_widths)
            spacing = space / float(num_clips + 1)
            spacing = max(spacing, min_spacing)
            border_size = spacing
            if spacing >= 5 * h_spacing:
                spacing = 3 * h_spacing
                if row_num != self.total_num_rows - 1:
                    border_size = (space - (num_clips - 1) * spacing) / 2.
                else:
                    sizes = np.array(border_sizes)
                    if len(sizes) == 0:
                        border_size = spacing
                    else:
                        border_size = np.median(sizes)
            border_sizes.append(border_size)

            clip_x = border_size
            y = ys[i]
            
            for i in xrange(num_clips):
                
                x = int(round(clip_x - self._selection_rect_thickness))
                width = clip_widths[i]
                
                frame = self._active_clip_frames[frame_num]
                frame.setGeometry(x, y, width, height)
                
                clip_x += width + spacing
                
                frame_num += 1
                
                
    def _lay_out_clip_rows(self, clips_frame_height, spacing):
        
        min_height = self._min_clip_height
        thickness = self._selection_rect_thickness
        
        total_height = (clips_frame_height - (self.num_rows + 1) * spacing)
        clip_height = max(total_height / float(self.num_rows), min_height)
        clip_frame_height = int(round(clip_height)) + 2 * thickness

        offsets = (clip_height + spacing) * np.arange(self.num_rows)
        ys = spacing - thickness + offsets
        ys = np.array(ys, dtype=int)
        
        return (ys, clip_frame_height)
        

    @property
    def total_num_rows(self):
        return len(self._layout)
    
    
    def _get_first_clip_num_of_row(self, n):
        if n < 0 or n >= self.total_num_rows:
            return None
        else:
            return self._layout[n][0]
        
        
    def _show_clip_frames(self):
        for frame in self._active_clip_frames:
            frame.show()
        
        
class _FigureFrame(QFrame):
    
    """
    Frame that displays one clip.
    
    The frame contains an inset spectrogram and a border whose color
    indicates the selection status of the clip.
    """
    
    
    def __init__(self, parent, selection_rect_thickness, selection_rect_color):
        
        super(_FigureFrame, self).__init__(parent)
        
        self._index = None
        
        self._selection_rect_thickness = selection_rect_thickness
        self._selection_rect_color = selection_rect_color
        
        self._brush = QBrush(QColor(selection_rect_color))
        
        self.selected = False
        
        figure = Figure()
        canvas = FigureCanvasQTAgg(figure)
        canvas.setParent(self)
        self._clip_figure = ClipFigure(self, figure)

        
    @property
    def clip(self):
        return self._clip_figure.clip
    
    
    @clip.setter
    def clip(self, clip):
        self._clip_figure.clip = clip
        
        
    @property
    def index(self):
        return self._index
    
    
    @index.setter
    def index(self, index):
        self._index = index
        
        
    @property
    def selected(self):
        return self._selected
    
    
    @selected.setter
    def selected(self, selected):
        self._selected = selected
        self.update()
        
        
    # overrides QFrame.paintEvent
    def paintEvent(self, event):
        p = QPainter()
        p.begin(self)
        p.setBrush(Qt.red if self.selected else Qt.transparent)
        p.setPen(Qt.NoPen)
        size = self.size()
        p.drawRect(0, 0, size.width(), size.height())
        p.end()
        
        
    # overrides QFrame.resizeEvent
    def resizeEvent(self, event):
        size = self.size()
        w = size.width()
        h = size.height()
        t = self._selection_rect_thickness
        canvas = self._clip_figure.figure.canvas
        canvas.setGeometry(t, t, w - 2 * t, h - 2 * t)
        
        
    def _handle_selection_event(self, event):
        self.parent()._handle_selection_event(self, event)
    
    
# The following four functions are Qt-specific, since Matplotlib's
# `event.key` appears to be unreliable. For example, if one starts up
# the Vesper viewer and shift-clicks in a figure, the reported `event.key`
# is `None` rather than the expected `'shift'`. If one first clicks with
# no modifier keys down, however, subsequent modifier key presses
# (excepting the command key on the Macintosh, which is apparently
# ignored) are properly reported except that multiple modifiers are not
# reported, only the most recent one. Problems also occur when one clicks
# on a new figure with a modified key down after having first clicked on
# another. It again appears to be necessary to first click on the new
# figure with no modifier keys down in order for subsequent events to
# have useful `key` properties.


def _alt_down(event):
    return _test_for_modifier(event, Qt.AltModifier)


def _test_for_modifier(event, modifier):
    e = event.guiEvent
    return e is not None and e.modifiers() & modifier
    

def _control_down(event):
    return _test_for_modifier(event, Qt.ControlModifier)

    
def _meta_down(event):
    return _test_for_modifier(event, Qt.MetaModifier)


def _shift_down(event):
    return _test_for_modifier(event, Qt.ShiftModifier)


def _create_preset_combo_box(parent, preset_type_name, slot):
    
    preset_data = preset_manager.get_presets(preset_type_name)
    pairs = preset_manager.flatten_preset_data(preset_data)
    
    if len(pairs) != 0:
        
        preset_name_tuples, presets = zip(*pairs)
        preset_names = [' - '.join(t) for t in preset_name_tuples]
        
        combo_box = QComboBox(parent)
        combo_box.addItems(preset_names)
        combo_box.currentIndexChanged.connect(slot)
        
        indices = dict((p.name, i) for i, p in enumerate(presets))
        presets = dict((i, p) for i, p in enumerate(presets))
        
        return (combo_box, indices, presets)
    
    else:
        return (None, None, None)
