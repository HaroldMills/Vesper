"""Clip figure that displays a spectrogram."""


from __future__ import print_function

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
import numpy as np
import os.path

from vesper.archive.archive import Archive
from vesper.ui.clip_figure import ClipFigure
from vesper.ui.clip_figure_play_button import ClipFigurePlayButton
import vesper.util.measurements as measurements
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier
import vesper.util.nfc_detection_utils as nfc_detection_utils
import vesper.util.preferences as prefs
import vesper.util.time_frequency_analysis_utils as tfa_utils


'''
Matplotlib/PyQt4 issues to look into:

1. Matplotlib FigureCanvas event `guiEvent` attribute is apparently
   always `None`. It should be set to the Qt event that triggered the
   Matplotlib event.

2. Matplotlib axes_leave_event does not seem to fire when mouse leaves
   axes. It should.

3. Matplotlib figure_enter_event does not seem to include mouse location.
   It should.

4. Matplotlib `Figure.contains` method returns a pair rather than a
   boolean, but documentation does not explain what the elements of the
   pair mean (in particular, the second element appears to be a
   dictionary). It should.
   
5. Many Matplotlib `MouseEvent` instances appear to have no `key`
   attribute (e.g. for mouse motion events), but the documentation
   indicates that they should.
   
6. Matplotlib `MouseEvent` instances delivered when the mouse is released
   (`button_release_event`) have a `key` attribute of `None`.
'''


_MEASUREMENT_DATA = {
    'Entropy': (measurements.entropy, 0, 6),
    'Equivalent Bandwidth': (measurements.equivalent_bandwidth, 0, 30)
}

_SHOW_MEASUREMENT_LINE = False
_MEASUREMENT_NAME = 'Entropy'
_MEASUREMENT_BLOCK_SIZE = 1

# _IMAGE_TYPE = 'Instantaneous Frequency'
_IMAGE_TYPE = 'Spectrogram'
_DENOISE = False
_DENOISING_PERCENTILE = 70

_SHOW_AUX_FIGURE = False
_AUX_FIGURE_TYPE = 'Spectrum'
# _AUX_FIGURE_TYPE = 'Instantaneous Frequency'

_SELECTION_START_COLOR = (1, 0, 0, 1)
_SELECTION_COLOR = (1, 0, 0, .15)

_DETECTION_COLOR = (0, 1, 0, .15)


class _SelectionEventHandler(object):
    
    
    def __init__(self, figure):
        self._figure = figure
        self.start_time = None
        
        
    def on_button_press(self, event):

        clip = self._figure.clip
        button = event.button
        
        if button == 1:
            time = event.xdata
            if self.start_time is None:
                self.start_time = time
            else:
                sample_rate = clip.sound.sample_rate
                start_index = int(round(self.start_time * sample_rate))
                end_index = int(round(time * sample_rate))
                length = end_index - start_index + 1
                clip.selection = (start_index, length)
                self.start_time = None
            
        elif button == 3:
            self.start_time = None
            clip.selection = None
            
        
class SpectrogramClipFigure(ClipFigure):
    
    
    def __init__(self, parent, figure):
        
        super(SpectrogramClipFigure, self).__init__(parent, figure)
        
        self._axes = self.figure.add_axes([0, 0, 1, 1])
        self._axes.set_frame_on(False)
        
        self._axes.xaxis.set_visible(False)
        self._axes.yaxis.set_visible(False)
        
        self._waveform_line = None
        self._spectrogram_image = None
        self._measurement_line = None
        self._clip_text = _create_clip_text(self._axes)
        self._play_button = ClipFigurePlayButton(self)
        
        self._show_selections = \
            prefs.get('clip_figure.show_selections', False)
            
        if self._show_selections:
            self._selection_polygon = None
            self._selection_event_handler = _SelectionEventHandler(self)
            
        self._show_detection = \
            prefs.get('clip_figure.show_detection', False)
            
        if self._show_detection:
            self._detection_polygon = None
            
        self._show_segment_coarse_classifications = \
            prefs.get('clip_figure.show_segment_coarse_classifications', False)
            
        if self._show_segment_coarse_classifications:
            self._coarse_classification_line = None

        # Note that axis rendering is very expensive. Perhaps we should
        # draw our own grid with a collection of line2D artists? Also
        # need to set grid line positions based on axis limits, which
        # are determined when the clip is set.
#        self._axes.tick_params(color='red', size=0)  # `size=0` hides ticks
#        self._axes.set_xticks([.05, .1, .15, .2, .25])
#        self._axes.set_yticks([2000, 4000, 6000, 8000, 10000])
#        color = (.75, .75, .75)
#        linestyle = '-'
#        self._axes.xaxis.grid(color=color, linestyle=linestyle)
#        self._axes.yaxis.grid(color=color, linestyle=linestyle)
                
        connect = self.canvas.mpl_connect
        connect('figure_enter_event', self._on_figure_enter)
        connect('figure_leave_event', self._on_figure_leave)
        connect('axes_enter_event', self._on_axes_enter)
        connect('axes_leave_event', self._on_axes_leave)
        connect('button_press_event', self._on_button_press)
        connect('button_release_event', self._on_button_release)
        connect('motion_notify_event', self._on_motion)
        connect('key_press_event', self._on_key_press)
        connect('key_release_event', self._on_key_release)
        
        self.canvas.mouseReleaseEvent = \
            _PyQt4EventHandlerWrapper(self, self.canvas.mouseReleaseEvent)
            
        if self._show_segment_coarse_classifications:
            self._coarse_classifier = \
                nfc_coarse_classifier.create_classifier('Tseep')
        
        
    def _set_clip(self, clip):
        
        super(SpectrogramClipFigure, self)._set_clip(clip)
        
#         self._create_waveform_line()
        self._create_spectrogram_image()
        
        self._update_clip_text()
        self._play_button.reset()
        
        if self._show_selections:
            self._update_selection()
        
        if self._show_segment_coarse_classifications and clip is not None:
            
            (bits, frame_rate, start_time) = \
                self._coarse_classifier.classify_clip_segments(clip)
                
            self._create_coarse_classification_line(
                bits, frame_rate, start_time)
            
            file_name = os.path.basename(clip.file_path)
            print(file_name, bits, frame_rate, start_time)
        
        if _SHOW_MEASUREMENT_LINE:
            self._create_measurement_line()
            
        if self._show_detection:
            self._update_detection()
            
        
    def _update_selection(self):
        
        if self.clip is None:
            return
        
        axes = self._axes
        
        if self._selection_polygon is not None:
            axes.patches.remove(self._selection_polygon)
            self._selection_polygon = None
            
        selection = self.clip.selection
        
        if selection is not None:
        
            start_index, length = selection
            
            sample_rate = self.clip.sound.sample_rate
            start_time = start_index / sample_rate
            end_time = start_time + (length - 1) / sample_rate
            
            self._selection_polygon = axes.axvspan(
                start_time, end_time, color=_SELECTION_COLOR)
            
        else:
            # selection is None
            
            start_time = self._selection_event_handler.start_time
            
            if start_time is not None:
                # have new selection start time
                
                self._selection_polygon = axes.axvspan(
                    start_time, start_time, color=_SELECTION_START_COLOR)
            
                
    def _create_waveform_line(self):

        axes = self._axes
        
        # TODO: Calling `cla` is very slow. It appears from profiling
        # that `cla` causes the x and y axes to do some stuff that takes
        # a long time. Some of the stuff (e.g. concerning tick marks) is
        # irrelevant to us since we do not display the axes. Can we cut
        # out the irrelevant stuff somehow, perhaps by deleting certain
        # artists, so that `cla` will perform acceptably? Note that
        # something like this might also allow us to improve the
        # performance of figure creation, which seems to involve a
        # call to `cla`.
#            axes.cla()

        if self._waveform_line is not None:
            axes.lines.remove(self._waveform_line)
            self._waveform_line = None
                
        clip = self.clip
        
        if clip is not None:
            
            axes.set_xlim([0, clip.duration])
            axes.set_ylim([-32768, 32768])
            sound = clip.sound
            samples = sound.samples
            times = np.arange(len(samples)) / float(sound.sample_rate)
            self._waveform_line = axes.plot(times, samples, 'b')[0]


    def _create_spectrogram_image(self):
        
        axes = self._axes
        
        if self._spectrogram_image is not None:
            axes.images.remove(self._spectrogram_image)
            self._spectrogram_image = None
                
        clip = self.clip
        
        if clip is not None:
            
            duration = clip.duration
            fs = clip.sound.sample_rate
            
            axes.set_xlim([0, duration])
            axes.set_ylim([0, fs / 2.])
                
            if _IMAGE_TYPE == 'Spectrogram':
                
                if _DENOISE:
                    spectra = np.array(clip.spectrogram.spectra)
                    tfa_utils.denoise(
                        spectra, percentile=_DENOISING_PERCENTILE, out=spectra)
                    
                else:
                    spectra = clip.spectrogram.spectra
            
                min_power = prefs.get('clip_figure.spectrogram.min_power', -20)
                max_power = prefs.get('clip_figure.spectrogram.max_power', 80)
            
            elif _IMAGE_TYPE == 'Instantaneous Frequency':
                
                spectra = clip.instantaneous_frequencies.analyses
                min_power = -500
                max_power = 500
                
            spectra = spectra.transpose()
            times = clip.spectrogram.times
            freqs = clip.spectrogram.freqs
            axes.set_xlim(times[0], times[-1])
            self._spectrogram_image = axes.imshow(
                spectra, origin='lower',
                extent=(times[0], times[-1], freqs[0], freqs[-1]),
                aspect='auto', cmap='Greys', vmin=min_power, vmax=max_power,
                interpolation='bilinear', picker=None)
        
        
    def _create_coarse_classification_line(
            self, bits, frame_rate, start_time):

        axes = self._axes
        
        # TODO: Calling `cla` is very slow. It appears from profiling
        # that `cla` causes the x and y axes to do some stuff that takes
        # a long time. Some of the stuff (e.g. concerning tick marks) is
        # irrelevant to us since we do not display the axes. Can we cut
        # out the irrelevant stuff somehow, perhaps by deleting certain
        # artists, so that `cla` will perform acceptably? Note that
        # something like this might also allow us to improve the
        # performance of figure creation, which seems to involve a
        # call to `cla`.
#            axes.cla()

        if self._coarse_classification_line is not None:
            axes.lines.remove(self._coarse_classification_line)
            self._coarse_classification_line = None
                
        clip = self.clip
        
        if clip is not None:
            times = start_time + np.arange(len(bits)) / float(frame_rate)
            fs2 = clip.sound.sample_rate / 2.
            freqs = (.1 + .8 * np.array(bits)) * fs2
            self._coarse_classification_line = axes.plot(times, freqs, 'b')[0]


    def _create_measurement_line(self):

        measurement, m_min, m_max = _MEASUREMENT_DATA[_MEASUREMENT_NAME]
        
        axes = self._axes
        
        if self._measurement_line is not None:
            axes.lines.remove(self._measurement_line)
            self._measurement_line = None
                
        clip = self.clip
        
        if clip is not None:
            
            y_min, y_max = axes.get_ylim()
            ms, times = measurements.apply_measurement_to_spectra(
                measurement, clip.spectrogram,
                start_freq=6000, end_freq=10000,
                denoise=_DENOISE, block_size=_MEASUREMENT_BLOCK_SIZE)
            normalized_ys = (ms - m_min) / (m_max - m_min)
            ys = y_min + (y_max - y_min) * normalized_ys
            self._measurement_line = axes.plot(times, ys, 'b')[0]
            

    def _update_detection(self):
        
        if self.clip is None:
            return
        
        axes = self._axes
        
        if self._detection_polygon is not None:
            axes.patches.remove(self._detection_polygon)
            self._detection_polygon = None
            
        selections = nfc_detection_utils.detect_tseeps(self.clip)
        selection = nfc_detection_utils.get_longest_selection(selections)
        
        if selection is not None:
            start_time, end_time = selection
            self._detection_polygon = axes.axvspan(
                start_time, end_time, color=_DETECTION_COLOR)
            

    def _update_clip_text(self, event=None):
        
        figure_text = _get_clip_figure_clip_text(self.clip, event)
        self._clip_text.set_text(figure_text)
        self.canvas.draw()
        
        status_text = _get_status_bar_clip_text(self.clip, event)
        self._set_status_text(status_text)
        
        
    def _set_status_text(self, text):
        # The following is a bad way to update text in the application's
        # status bar, since a clip figure should not know so much about
        # its ancestors in the widget containment hierarchy. At the point
        # of this writing, however, we plan to replace this GUI with a
        # web-based one within a matter of months, and hence want to
        # minimize time spent maintaining this code. If this code winds
        # up living longer than expected, we should use the observer
        # pattern to allow instances of this class to notify other
        # interested objects of clip figure events that might interest
        # them. Note that there are other, similar violations of good
        # practice in this class, for example in the  `_on_button_release`
        # and `_update_aux_figure*` methods.
        self.parent.parent().parent().parent()._status_bar.showMessage(text)
        
        
    def _on_figure_enter(self, event):
        self._update_clip_text(event)
        self._play_button._on_figure_enter(event)
#        _show_event(event, 'SpectrogramClipFigure._on_figure_enter')
    
    
    def _on_figure_leave(self, event):
        self._update_clip_text()
        self._play_button._on_figure_leave(event)
#        _show_event(event, 'SpectrogramClipFigure._on_figure_leave')
   
    
    def _on_axes_enter(self, event):
        self._update_clip_text(event)
#        _show_event(event, 'SpectrogramClipFigure._on_axes_enter')
    
    
    def _on_axes_leave(self, event):
        self._update_clip_text(event)
#        _show_event(event, 'SpectrogramClipFigure._on_axes_leave')
        
        
    def _on_button_press(self, event):
        self._update_clip_text(event)
        self._play_button._on_button_press(event)
        if self._show_selections and not self._play_button._contains(event):
            self._selection_event_handler.on_button_press(event)
            self._update_selection()
#        _show_event(event, 'SpectrogramClipFigure._on_button_press')
            
            
    def _on_button_release(self, event):
        
        self._update_clip_text(event)
        
        if event.button == 1 and self._contains(event) and \
           not self._play_button.down:
            
            event.guiEvent = self._qt_event
            self.parent._handle_selection_event(event)
            
        self._play_button._on_button_release(event)

#        _show_event(event, 'SpectrogramClipFigure._on_button_release')

            
    def _contains(self, event):
        return self.figure.contains(event)[0]
    
    
    def _on_motion(self, event):
        self._update_clip_text(event)
        self._play_button._on_motion(event)
        self._update_aux_figure(event)
#        _show_event(event, 'SpectrogramClipFigure._on_motion')
        
        
    def _update_aux_figure(self, event):
        if _SHOW_AUX_FIGURE:
            p = self.parent.parent()
            if not hasattr(p, '_aux_figure'):
                p._aux_figure, p._aux_canvas = self._create_aux_figure()
            if _AUX_FIGURE_TYPE == 'Spectrum':
                self._update_aux_figure_spectrum_plot(event)
            elif _AUX_FIGURE_TYPE == 'Instantaneous Frequency':
                self._update_aux_figure_if_plot(event)
            else:
                s = 'Unrecognized auxiliary figure type {:s}.'
                print(s.format(_AUX_FIGURE_TYPE))
                
                
    def _create_aux_figure(self):
   
        figure = Figure()
        
        canvas = FigureCanvasQTAgg(figure)
        canvas.setWindowTitle('Clip Slice')
        
        figure.add_subplot(1, 1, 1)
        
        canvas.show()
        canvas.raise_()
        
        return (figure, canvas)
        
    
    def _update_aux_figure_spectrum_plot(self, event):
        clip = self.clip
        gram = clip.spectrogram
        p = self.parent.parent()
        figure = p._aux_figure
        axes = figure.axes[0]
        axes.clear()
        i = int(round((event.xdata - gram.times[0]) * gram.analysis_rate))
        axes.plot(gram.freqs, gram.spectra[i])
        axes.set_xlim([0, gram.freqs[-1]])
        axes.set_ylim([-20, 80])
        axes.grid(True)
        axes.set_xlabel('Frequency (Hz)')
        axes.set_ylabel('Power (dB)')
        axes.set_title('Spectrum at {:.3f} s'.format(event.xdata))
        axes.axvline(event.ydata, color='r')
        p._aux_canvas.draw()
        
        
    def _update_aux_figure_if_plot(self, event):
        clip = self.clip
        gram = clip.instantaneous_frequencies
        p = self.parent.parent()
        figure = p._aux_figure
        axes = figure.axes[0]
        axes.clear()
        i = int(round((event.xdata - gram.times[0]) * gram.analysis_rate))
        xs = gram.freqs
        ys = xs + gram.analyses[i]
        axes.plot(xs, ys, marker='.')
        axes.plot([xs[0], xs[-1]], [xs[0], xs[-1]], color='r')
#         axes.set_xlim([0, gram.freqs[-1]])
#         axes.set_ylim([-100, gram.freqs[-1] + 100])
        axes.set_xlim([5000, 10000])
        axes.set_ylim([5000, 10000])
#        axes.set_ylim([-20, 20])
        axes.grid(True)
        axes.set_xlabel('Grid Frequency (Hz)')
        axes.set_ylabel('Instantaneous Frequency (Hz)')
        s = 'Instantaneous Frequencies at {:.3f} s'
        axes.set_title(s.format(event.xdata))
        axes.axvline(event.ydata, color='r')
#        print(gram.times[0], gram.times[-1], event.xdata)
        p._aux_canvas.draw()
        
        
    def _on_key_press(self, event):
        pass
#        print('SpectrogramClipFigure._on_key_press', event.key)
        
        
    def _on_key_release(self, event):
        pass
#        print('SpectrogramClipFigure._on_key_release', event.key)
        
        
def _show_event(e, prefix):
    if hasattr(e, 'x'):
        print(prefix, e.name, e.x, e.y, e.xdata, e.ydata)
    else:
        print(prefix, e.name)


def _create_clip_text(axes):
    # TODO: Allow control of font name?
    color = prefs.get('clip_figure.clip_text_color')
    size = prefs.get('clip_figure.clip_text_font_size')
    return axes.text(
        .5, .02, '', color=color, size=size, ha='center',
        transform=axes.transAxes)


def _get_clip_figure_clip_text(clip, event):
    
    if clip is None:
        return ''
    
    else:
        
        pos = _get_mouse_pos(event)
        
        if pos is None:
            # mouse is not in clip figure
            
            if prefs.get('clip_figure.show_clip_class_names'):
                name = _get_clip_class_display_name(clip.clip_class_name)
            else:
                name = None
            
            if prefs.get('clip_figure.show_clip_times'):
                time = _format_clip_time(clip)
            else:
                time = None
            
            if name is not None and time is not None:
                return name + ' ' + time
            elif name is not None:
                return name
            elif time is not None:
                return time
            else:
                return ''
        
        else:
            # mouse is in clip figure
            
            if prefs.get('clip_figure.show_mouse_location'):
                return _format_mouse_pos(pos)
            else:
                return ''
            
            
def _get_mouse_pos(event):
    
    if event is not None and hasattr(event, 'xdata') and \
       event.xdata is not None:
        
        return (event.xdata, event.ydata)
    
    else:
        return None
        
            
def _get_clip_class_display_name(name):
    
    if name is None:
        return Archive.CLIP_CLASS_NAME_UNCLASSIFIED
        
    # TODO: Move this to some sort of classification scheme module.
    elif name.startswith('Call.'):
        return name[len('Call.'):]
        
    else:
        return name
        
            
def _format_clip_time(clip):
    
    # Get clip time localized to station time zone.
    time_zone = clip.station.time_zone
    time = clip.start_time.astimezone(time_zone)
    
    hms = time.strftime('%H:%M:%S')
    milliseconds = int(round(time.microsecond / 1000.))
    milliseconds = '{:03d}'.format(milliseconds)
    time_zone = time.strftime('%Z')
    
    return hms + '.' + milliseconds + ' ' + time_zone


def _format_mouse_pos(pos):
    x, y = pos
    return '{:.3f} s  {:d} Hz'.format(x, int(round(y)))


def _get_status_bar_clip_text(clip, event):
    
    pos = _get_mouse_pos(event)
    
    if clip is None or pos is None:
        return ''
    
    else:

        name = clip.clip_class_name
        time = _format_clip_time(clip)
        pos = _format_mouse_pos(pos)
        return name + '   ' + time + '   ' + pos


# TODO: This class was needed for PySide, but is it needed for PyQt4?
# TODO: Fix PyQt4 (and wx, if it is also broken) event handling
# so this class is not needed.
class _PyQt4EventHandlerWrapper(object):
    
    """
    Wrapper for Matplotlib figure canvas PyQt4 event handlers.
    
    The default handlers discard the Qt event for which they were
    invoked, but this wrapper saves it in a clip figure's `_qt_event`
    attribute.
    """
    
    def __init__(self, clip_figure, handler):
        self._clip_figure = clip_figure
        self._wrapped_handler = handler
        
    def __call__(self, qt_event):
        # print('_QtEventHandlerWrapper')
        self._clip_figure._qt_event = qt_event
        self._wrapped_handler(qt_event)
