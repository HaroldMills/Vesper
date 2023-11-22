# This script demonstrates an issue with the `sounddevice` Python package.
#
# The script first calls `sd.check_input_settings` to see if some input
# settings are supported, and then, if they are (i.e. if
# `sd.check_input_settings` does not raise an exception) records for one
# second with those settings.
#
# When I run the script on my 2019 MacBook Pro with a sample rate of 44100,
# it completes without issue. However, if I run it with various other sample
# rates, such as 22050, 24000, or 48000, `sd.check_input_settings` returns
# as though the sample rates are supported, but the script then terminates
# inside the call to `sd.rec` with the message:
#
#     libc++abi: terminating
#
# on the console. So it appears that `sd.check_input_settings` indicates
# that some settings are supported when in fact they are not.

import sounddevice as sd

settings = {'device': 1, 'channels': 1, 'samplerate': 48000, 'dtype': 'int16'}
sd.check_input_settings(**settings)
sd.rec(frames=settings['samplerate'], blocking=True, **settings)
