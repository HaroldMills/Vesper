"""
Records audio asynchronously using PyAudio.

This example script is modeled on other examples at the PyAudio web site
(https://people.csail.mit.edu/hubert/pyaudio/). The script is short and
self-contained.
"""

import pyaudio
import time
import wave

NUM_CHANNELS = 1
SAMPLE_RATE = 22050
SAMPLE_FORMAT = pyaudio.paInt16
RECORDING_DURATION = 5
WAVE_OUTPUT_FILENAME = 'output.wav'

p = pyaudio.PyAudio()

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(NUM_CHANNELS)
wf.setsampwidth(p.get_sample_size(SAMPLE_FORMAT))
wf.setframerate(SAMPLE_RATE)

stop = False
def callback(in_data, frame_count, time_info, status):
    wf.writeframes(in_data)
    return_code = pyaudio.paContinue if not stop else pyaudio.paComplete
    return (None, return_code)

stream = p.open(
    channels=NUM_CHANNELS,
    rate=SAMPLE_RATE,
    format=SAMPLE_FORMAT,
    input=True,
    stream_callback=callback)

print("* recording")

start_time = time.time()
while stream.is_active():
    time.sleep(0.1)
    elapsed_time = time.time() - start_time
    if elapsed_time > RECORDING_DURATION:
        break
    
print("* done recording")

stop = True
time.sleep(1)
wf.close()
stream.stop_stream()
stream.close()
p.terminate()
