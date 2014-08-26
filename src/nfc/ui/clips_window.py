from __future__ import print_function

from collections import defaultdict

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide.QtCore import Qt
from PySide.QtGui import (
    QBrush, QFrame, QLabel, QMainWindow, QPainter, QVBoxLayout, QWidget)
import numpy as np

from nfc.archive.archive import Archive
from nfc.ui.flow_layout import FlowLayout
from nfc.ui.multiselection import Multiselection
from nfc.ui.spectrogram_clip_figure import SpectrogramClipFigure as ClipFigure
from nfc.util.bunch import Bunch
from nfc.util.preferences import preferences as prefs
import nfc.util.classification_command_set_utils as command_set_utils


_SPACING_ASPECT_RATIO = 2
"""ratio of vertical clip spacing to minimum horizontal spacing."""


# TODO: Figure out where this belongs and put it there.
_CLIP_CLASS_NAME_COMPONENT_SEPARATOR = '.'


class ClipsWindow(QMainWindow):
    
    
    def __init__(
        self, parent, archive, station_name, detector_name, night,
        clip_class_name, command_set_name):
        
        super(ClipsWindow, self).__init__(parent)
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self._archive = archive
        
        self._init_classification_dict(command_set_name)
        
        self._create_ui()
        
        self.set_clips(station_name, detector_name, night, clip_class_name)
        
        date = str(self._date.day) + ' ' + self._date.strftime('%B %Y')
        title = '{:s} - {:s} - {:s}'.format(
            self._station_name, self._detector_name, date)
        self.setWindowTitle(title)
        
        
    def _init_classification_dict(self, command_set_name):
        
        if command_set_name is None:
            self._classification_dict = {}
            
        else:
            self._classification_dict = \
                self._create_classification_dict(command_set_name)
        
        
    def _create_classification_dict(self, command_set_name):
        
        command_sets = prefs.get('clipsWindow.commandSets')
        
        if command_sets is None:
            
            # TODO: Handle error.
            return {}
        
        command_set = command_sets.get(command_set_name)
        
        if command_set is None:
            
            # TODO: Handle error.
            return {}
            
        # Want to wind up with a mapping from commands to clip classes.
        # This will be the composition of the command set, which maps commands
        # to clip class name fragments, and a mapping from clip class name
        # fragments to clip classes. For each clip class name fragment
        # of a command set, there must be exactly one clip class whose name
        # ends with that fragment.
        
        classes = self._archive.clip_classes
        classes_dict = self._create_fragment_to_classes_dict(classes)
        classification_dict = {}
        
        for command, (fragment, all_) in command_set.iteritems():
            
            classes = classes_dict.get(fragment)
            
            if classes is None:
                # TODO: Handle error.
                pass
            
            elif len(classes) != 1:
                # TODO: Handle error.
                pass
            
            else:
                classification_dict[command] = (classes[0], all_)
            
#         for command, (clip_class, all_) in classification_dict.iteritems():
#             print(command, clip_class.name, all_)
            
        return classification_dict
        
        
    def _create_fragment_to_classes_dict(self, clip_classes):
        d = defaultdict(list)
        d[Archive.CLIP_CLASS_NAME_UNCLASSIFIED].append(None)
        for c in clip_classes:
            for f in self._get_clip_class_name_fragments(c.name):
                d[f].append(c)
        return d
    
    
    def _get_clip_class_name_fragments(self, name):
        sep = _CLIP_CLASS_NAME_COMPONENT_SEPARATOR
        parts = name.split(sep)
        n = len(parts)
        return [sep.join(parts[i:n]) for i in xrange(n)]
    
    
    def _create_ui(self):
        
        widget = QWidget(self)
#        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        
        self._title_label = QLabel(widget)
        self._title_label.setAlignment(Qt.AlignCenter)
        
        config = Bunch(
            clips_area_width=prefs['clipsWindow.duration'],
            clip_spacing=prefs['clipsWindow.spacing'],
            num_rows=prefs['clipsWindow.numRows'],
            min_clip_height=40,
            selection_rect_thickness=3,
            selection_rect_color='red'
        )
        self._figures_frame = _FiguresFrameWithFlowLayout(widget, config)
        
        box = QVBoxLayout()
        box.addWidget(self._title_label)
        box.addWidget(self._figures_frame, stretch=1)
        
        widget.setLayout(box)
        
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

        self.setCentralWidget(widget)

    
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
        self._figures_frame.clips = self._clips
        self._update_title()
        

    def _update_title(self):
        
        if self._station_name is None or self._detector_name is None or \
           self._date is None or self._clip_class_name is None:
            
            title = 'No Clips'
            
        else:
            title = self._create_clips_string()

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
        
        command = command_set_utils.get_command_from_key_event(e)
        
        if command is not None:
            
            pair = self.classification_dict.get(command)
        
            if pair is not None:
                self.classify(*pair)
                
            else:
                # key is not a classification command
                
                self._key_press_event(e)
                
        
        else:
            # key is not a classification command
            
            self._key_press_event(e)
            
            
    def _key_press_event(self, e):
        
        key = e.key()
        
        if key == Qt.Key_PageDown or key == Qt.Key_Space:
            self.move_down_one_page()
            
        elif key == Qt.Key_PageUp:
            self.move_up_one_page()
            
        else:
            super(ClipsWindow, self).keyPressEvent(e)

    
    @property
    def classification_dict(self):
        return self._classification_dict
        
        
    def classify(self, clip_class, scope):
        self._figures_frame.classify(clip_class, scope)
        self._update_title()
        

    def move_down_one_page(self):
        self._figures_frame.move_down_one_page()
        self._update_title()
                        
            
    def move_up_one_page(self):
        self._figures_frame.move_up_one_page()
        self._update_title()


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
#        self._show_clip_durs(clips)
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
    
    
    def classify(self, clip_class, scope):
        
        new_name = clip_class.name if clip_class is not None else None
        
        if scope == 'All':
            intervals = ((0, len(self._clips) - 1),)
            self._classify(intervals, new_name)
            
        else:
            
            if self.num_visible_clips == 0:
                return
            
            first = self.first_visible_clip_num
            
            if scope == 'Page':
                intervals = ((first, first + self.num_visible_clips - 1),)
            else:
                intervals = _shift(self.selection.selected_intervals, first)
                
            self._classify(intervals, new_name)
            
            if prefs['clipsWindow.advanceAfterClassification']:
                self._advance_after_classification(scope, intervals)
                
                            
    def _classify(self, intervals, new_name):
        
        first = self.first_visible_clip_num
            
        for i, j in intervals:
            
            for k in xrange(i, j + 1):
                
                clip = self._clips[k]
                
                old_name = clip.clip_class_name
                
                if new_name != old_name:
                    
                    clip.clip_class_name = new_name
                    
                    if  k >= first and k < first + self.num_visible_clips:
                    
                        # This is very naughty. The figures frame should not
                        # be rooting around in clip frames' private parts and
                        # telling their clip figures to update their clip text.
                        # Instead, clips (as models) should probably support
                        # observers and clip figures (as views of clips) should
                        # update themselves when they are notified that their
                        # clips' classifications have changed.
                        frame = self._active_clip_frames[k - first]
                        figure = frame._clip_figure
                        figure._update_clip_text()
                    

    def _advance_after_classification(self, scope, intervals):
        
        if scope == 'Selected' and _is_singleton(intervals):
                
            clip_num = intervals[0][0]
            
            last_visible_clip_num = \
                self.first_visible_clip_num + self.num_visible_clips - 1
            
            if clip_num != last_visible_clip_num:
                # selected clip is not last on this page
                
                self._select_clip(clip_num + 1)

            elif clip_num != len(self._clips) - 1:
                # there are more clips
                
                self.move_down_one_page()
                self._select_clip(last_visible_clip_num + 1)
                
        elif scope == 'Page':
                    
            last_visible_clip_num = \
                self.first_visible_clip_num + self.num_visible_clips - 1
            
            if last_visible_clip_num != len(self._clips) - 1:
                # there are more clips
                
                self.move_down_one_page()
                
        
    def _select_clip(self, clip_num):
        
        self.selection.select(clip_num - self.first_visible_clip_num)
        
        # TODO: Should selections be observable, so that we
        # can observe the selection and update our graphical
        # representation of it when it changes?
        self._update_clip_frame_selection_states()
        

    def _update_clip_frame_selection_states(self):
        for frame in self._active_clip_frames:
            frame.selected = frame.index in self.selection


    def move_down_one_page(self):
        if self.first_visible_row_num + self.num_rows < self.total_num_rows:
            self._move_by_num_rows(self.num_rows)
        
    
    def _move_by_num_rows(self, num_rows):
        if self.total_num_rows != 0:
            self.first_visible_row_num += num_rows
            
            
    def move_up_one_page(self):
        self._move_by_num_rows(-self.num_rows)
        
    
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


def _is_singleton(intervals):
    
    if len(intervals) != 1:
        return False
    
    else:
        start, end = intervals[0]
        return start == end
    

def _shift(intervals, n):
    return tuple([(i + n, j + n) for i, j in intervals])


class _FiguresFrameWithFlowLayout(_FiguresFrame):
    
    
    def __init__(self, parent, config, **kwargs):
        
        super(_FiguresFrameWithFlowLayout, self).__init__(
            parent, config, **kwargs)
        
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
            frame.show()
            self._active_clip_frames.append(frame)
        
        print('    creating selection...')
        self._selection = Multiselection(0, len(clips) - 1)
        
        print('    laying out clip frames...')
        self._lay_out_clips()
        
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
        
        self._brush = QBrush(selection_rect_color)
        
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
# the NFC viewer and shift-clicks in a figure, the reported `event.key`
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
