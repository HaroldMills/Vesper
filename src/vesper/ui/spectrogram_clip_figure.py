"""Clip figure that displays a spectrogram."""


from __future__ import print_function

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
import numpy as np

from vesper.archive.archive import Archive
from vesper.ui.clip_figure import ClipFigure
from vesper.ui.clip_figure_play_button import ClipFigurePlayButton
from vesper.util.preferences import preferences as prefs
import vesper.util.measurements as measurements
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

_SHOW_AUX_FIGURE = False
_AUX_FIGURE_TYPE = 'Spectrum'
# _AUX_FIGURE_TYPE = 'Instantaneous Frequency'


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
        
        
    def _set_clip(self, clip):
        
        super(SpectrogramClipFigure, self)._set_clip(clip)
        
#         self._create_waveform_line()
        self._create_spectrogram_image()
        
        if _SHOW_MEASUREMENT_LINE:
            self._create_measurement_line()
            
        self._update_clip_text()
        self._play_button.reset()
        
        
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
                    tfa_utils.log_to_linear(spectra, out=spectra)
                    tfa_utils.denoise(spectra, out=spectra)
                    tfa_utils.linear_to_log(spectra, out=spectra)
                    
                else:
                    spectra = clip.spectrogram.spectra
            
                min_power = prefs.get('clipFigure.spectrogram.minPower', -20)
                max_power = prefs.get('clipFigure.spectrogram.maxPower', 80)
            
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
                start_freq=6000., end_freq=10000.,
                denoise=_DENOISE, block_size=_MEASUREMENT_BLOCK_SIZE)
            normalized_ys = (ms - m_min) / (m_max - m_min)
            ys = y_min + (y_max - y_min) * normalized_ys
            self._measurement_line = axes.plot(times, ys, 'b')[0]
            

    def _update_clip_text(self, event=None):
        
        if self.clip is None:
            text = ''
            
        else:
            # clip is not `None`
            
            pos = self._get_mouse_pos(event)
            
            if prefs['clipFigure.showMouseLocation'] and pos is not None:
                x, y = pos
                text = '{:.3f} s  {:d} Hz'.format(x, int(round(y)))
                
            else:
                text = _get_clip_text(self.clip)
        
        self._clip_text.set_text(text)
        
        self.canvas.draw()
        
        
    def _get_mouse_pos(self, event):
        
        if event is not None and hasattr(event, 'xdata') and \
           event.xdata is not None:
            
            return (event.xdata, event.ydata)
        
        else:
            return None
        
            
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
    color = prefs['clipFigure.clipTextColor']
    size = prefs['clipFigure.clipTextFontSize']
    return axes.text(
        .5, .02, '', color=color, size=size, ha='center',
        transform=axes.transAxes)


def _get_clip_text(clip):
    
    name = _get_clip_class_display_name(clip.clip_class_name)
    
    if prefs['clipFigure.showClipTimes']:
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


def _get_clip_class_display_name(name):
    
    if prefs['clipFigure.showClipClassNames']:
        
        if name is None:
            return Archive.CLIP_CLASS_NAME_UNCLASSIFIED
            
        # TODO: Move this to some sort of classification scheme module.
        elif name.startswith('Call.'):
            return name[len('Call.'):]
            
        else:
            return name
        
    else:
        # not displaying clip class names
        
        return None
        
            
def _format_clip_time(clip):
    
    # Get clip time localized to station time zone.
    time_zone = clip.station.time_zone
    time = clip.start_time.astimezone(time_zone)
    
    hms = time.strftime('%H:%M:%S')
    milliseconds = int(round(time.microsecond / 1000.))
    milliseconds = '{:03d}'.format(milliseconds)
    time_zone = time.strftime('%Z')
    
    return hms + '.' + milliseconds + ' ' + time_zone


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
