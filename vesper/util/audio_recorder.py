"""Module containing the `AudioRecorder` class."""


from queue import Queue
from threading import Thread

import pyaudio

from vesper.util.bunch import Bunch
from vesper.util.notifier import Notifier
from vesper.util.schedule import ScheduleRunner


# TODO:
#
# 1. Give each `AudioRecorder` its own thread that reads audio data from
#    a `queue`. The audio data are written to the `queue` by the recorder's
#    PyAudio callback. This will keep the PyAudio callback execution time
#    to a minimum by moving `AudioRecorderListener` processing from the
#    callback thread to the recorder thread.
#
# 2. Review the schedule listener methods and the `AudioRecorder.wait`
#    method. Are they what we want? How will scheduled recording relate
#    to scheduled processing of recordings, e.g. detection followed by
#    coarse classification?
#
# 3. Implement a recorder command that gets a list of available input
#    devices.
#
# 4. Make the `AudioRecorder` configuration mutable. Some state will
#    be mutable only when a recorder is stopped and its schedule is
#    disabled. As before, synchronize state manipulation with a lock
#    where needed.
#
# 5. Add HTTP access to `AudioRecorder` state. Include a way to get
#    a list of available input devices.
#
# 6. Test local deployment as a Windows service.
#
# 7. Test MPG Ranch deployment as a Windows service.


class AudioRecorder:
    
    """Records audio asynchronously."""
    
    
    # This class uses a lock to ensure that the `start`, `_callback`, and
    # `stop` methods execute atomically. These methods can run on various
    # threads, and making them atomic ensures that they have a coherent
    # view of the state of a recorder.
    

    def __init__(self, num_channels, sample_rate, buffer_size, schedule=None):
        
        self._num_channels = num_channels
        self._sample_rate = sample_rate
        self._buffer_size = buffer_size
        self._schedule = schedule
        
        self._recording = False
        self._stop_pending = False
        
        self._notifier = Notifier()
        
        self._command_queue = Queue()
        self._thread = Thread(target=self._run)
        self._thread.start()

        if schedule is not None:
            self._schedule_runner = ScheduleRunner(schedule)
            listener = _ScheduleListener(self)
            self._schedule_runner.add_listener(listener)
        else:
            self._schedule_runner = None
            
    
    @property
    def num_channels(self):
        return self._num_channels
    
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def buffer_size(self):
        return self._buffer_size
    
    
    @property
    def schedule(self):
        return self._schedule
    
    
    @property
    def recording(self):
        return self._recording
    
    
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
    
    
    def remove_listener(self, listener):
        self._notifier.remove_listener(listener)
    
    
    def clear_listeners(self):
        self._notifier.clear_listeners()
    
    
    def _notify_listeners(self, method_name, *args, **kwargs):
        self._notifier.notify_listeners(method_name, self, *args, **kwargs)
            
            
    def start(self):
        if self._schedule_runner is not None:
            self._schedule_runner.start()
        else:
            self._start()
                
                
    def _start(self):
        command = Bunch(name='start')
        self._command_queue.put(command)
            
    
    def stop(self):
        if self._schedule_runner is not None:
            self._schedule_runner.stop()
        else:
            self._stop()
                
                
    def _stop(self):
        command = Bunch(name='stop')
        self._command_queue.put(command)
            
            
    def _run(self):
        
        # TODO: What do we do if this method raises an exception?
        
        while True:
            
            command = self._command_queue.get()

            handler_name = '_on_' + command.name
            handler = getattr(self, handler_name)
            handler(command)
                
    
    def _on_start(self, command):
        
        if not self._recording:
            
            self._notify_listeners('recording_starting')
            
            self._recording = True
            self._stop_pending = False

            self._pyaudio = pyaudio.PyAudio()
            
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.num_channels,
                rate=self.sample_rate,
                frames_per_buffer=self.buffer_size,
                input=True,
                stream_callback=self._pyaudio_callback)
    

    def _pyaudio_callback(self, samples, buffer_size, time_info, status):
        
        # TODO: Should we copy samples before queueing them?
        
        if self._recording:
            
            command = Bunch(
                name='input',
                samples=samples,
                buffer_size=buffer_size)
            
            self._command_queue.put(command)
            
            return (None, pyaudio.paContinue)
        
        else:
            return (None, pyaudio.paComplete)


    def _on_input(self, command):
        
        self._notify_listeners(
            'samples_arrived', command.samples, command.buffer_size)

        if self._stop_pending:
            
            self._recording = False
            self._stop_pending = False
            
            self._stream.stop_stream()
            self._stream.close()
            self._pyaudio.terminate()
            
            self._notify_listeners('recording_stopped')


    def _on_stop(self, command):
        
        # Instead of stopping recording here, we just set a flag
        # indicating that a stop is pending, and then stop in the
        # next call to the`_on_input` method *after* processing
        # the next buffer of input samples. If we stop here we
        # usually record one less buffer than one would expect.
        if self._recording:
            self._stop_pending = True
    

    # TODO: Review the schedule listener methods and this method.
    def wait(self):
        if self._schedule_runner is not None:
            self._schedule_runner.wait()


class _ScheduleListener:
    
    
    def __init__(self, recorder):
        self._recorder = recorder
        
        
    def schedule_run_started(self, schedule, time, state):
        if state:
            self._recorder._start()
    
    
    def schedule_state_changed(self, schedule, time, state):
        if state:
            self._recorder._start()
        else:
            self._recorder._stop()
    
    
    def schedule_run_stopped(self, schedule, time, state):
        self._recorder._stop()
    
    
    def schedule_run_completed(self, schedule, time, state):
        self._recorder._stop()


class AudioRecorderListener:
    
    """
    Listener for events generated by an audio recorder.
    
    The default implementations of the methods of this class do nothing.
    """
    
    
    def recording_starting(self, num_channels, sample_rate):
        pass
    
    
    def samples_arrived(self, samples, buffer_size):
        pass
    
    
    def recording_stopped(self):
        pass
