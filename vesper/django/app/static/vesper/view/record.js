/*

A client creates a recording on the server by submitting a sequence of
HTTP POST requests to certain URLs. The URLs and the actions the
server takes in response to the requests are as follows:

    URL                   Action
    ---                   ------
    /record               Create a new recording.
    /recordings/<id>      Append data to a recording
    
A POST request to /record has a JSON body that provides recording
metadata. The server uses the metadata to add the recording to the
database. The response to the request has a JSON body that includes
an ID for the new recording.

A POST request to /recordings/<id> either appends data to a recording
or indicates that the recording is complete. The request has
a binary body that starts with a four-byte *command* that is either
zero or one, with zero signifying "append" and one signifying "stop".
An append command is followed by an eight-byte start index, a
four-byte sample frame count, and the indicated number of sample
frames. A stop command is not followed by any additional data.

*/


// Set up Axios for XSRF protection.
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';


// The audio input stream settings we can work with, in order of preference.
// Each pair comprises a sample rate in Hertz and a channel count.
const _ACCEPTABLE_INPUT_SETTINGS = [
    [48000, 1],
    [48000, 2]
];

const _REQUIRED_SAMPLE_SIZE = 16;
const _REQUIRED_AUTO_GAIN_CONTROL = false;
const _REQUIRED_ECHO_CANCELLATION = false;
const _REQUIRED_NOISE_SUPPRESSION = false;

const _RING_BUFFER_PROCESSOR_PATH =
    '/static/vesper/audio/ring-buffer-processor.js';
    
const _SAMPLE_CHUNK_DURATION = 1;
const _SAMPLE_SCALE_FACTOR = 32767;

const _platformIsLittleEndian = (() => {
    
    // Create two-byte array with first byte 1 and second byte 0.
    const array8 = new Int8Array([1, 0]);
    
    // Interpret the two-byte array as a 16-bit integer. The integer
    // will be 1 on a little-endian platform and 256 on a big-endian
    // platform.
    const array16 = new Int16Array(array8.buffer);
    
    return array16[0] == 1;
    
})();


let _audioInputDevices = null;
let _usableInputDeviceSettings = new Map();
let _recording = false;
let _recordingId = null;
let _recordingLength = null;
let _resampler = null;
let _chunker = null;
let _audioContext = null;


const _resamplerBufferCapacity = 1000;
const _decimationFactor = 2;
const _lowpassFilter = new Float64Array([0, 0, 1, 0, 0]);


/*

RESUME:

* Eliminate `_SlidingSampleBuffer.initialSize` constructor argument.

* Add `appendZeros` method to `_SlidingSampleBuffer`.
  
* Figure out how processing will end. We need to append zeros to resampler
  input then and process them.
  
* Implement resampler process method.

*/


class _SlidingSampleBuffer {
    
    
    constructor(capacity, initialSize = 0) {
        this._buffer = new Float32Array(capacity);
        this._bufferStartIndex = -initialSize;
        this._contentsStartOffset = 0;
        this._contentsEndOffset = initialSize;
    }
    
    
    get capacity() {
        return this._buffer.length;
    }
    
    
    get startIndex() {
        return this._bufferStartIndex + this._contentsStartOffset;
    }
    
    
    get endIndex() {
        return this._bufferStartIndex + this._contentsEndOffset;
    }
    
    
    get size() {
        return this._contentsEndOffset - this._contentsStartOffset;
    }
    
    
    get contents() {
        return this._buffer.subarray(
            this._contentsStartOffset, this._contentsEndOffset);
    }
    
    
    append(samples) {
        
        const length = samples.length;
        
        if (this.size + length > this.capacity)
            throw new Error('_SlidingSampleBuffer overflow');
        
        // Move contents to beginning of buffer if needed to make room
        // for new samples.
        if (this._contentsEndOffset + length > this.capacity) {
            
            this._buffer.copyWithin(
                0, this._contentsStartOffset, this._contentsEndOffset);
                
            this._bufferStartIndex += this._contentsStartOffset;
            this._contentsEndOffset -= this._contentsStartOffset;
            this._contentsStartOffset = 0
            
        }
        
        // Copy new samples into buffer.
        let j = this._contentsEndOffset;
        for (let i = 0; i != length; i++)
            this._buffer[j++] = samples[i];
            
        // Update window end offset.
        this._contentsEndOffset += length;
        
    }
    
    
    discard(sampleCount) {
        
        if (sampleCount > this.size)
            throw new Error('_SlidingSampleBuffer underflow');
            
        this._contentsStartOffset += sampleCount;
        
    }
    
    
}


function _testSampleBuffer() {
    
    const b = new _SlidingSampleBuffer(8, 4);
    
    if (b.capacity !== 8)
    _assertEquals(b.capacity, 8, 'buffer capacity');
    
    _assertBuffer(b, -4, [0, 0, 0, 0])
    
    b.append([1, 2]);
    _assertBuffer(b, -4, [0, 0, 0, 0, 1, 2]);
    
    b.discard(3);
    _assertBuffer(b, -1, [0, 1, 2]);
    
    b.append([3, 4, 5, 6, 7]);
    _assertBuffer(b, -1, [0, 1, 2, 3, 4, 5, 6, 7]);
    
    b.discard(2);
    _assertBuffer(b, 1, [2, 3, 4, 5, 6, 7]);
    
    _assertThrows(_ => b.append([1, 2, 3]), 'Buffer append');
    
    _assertThrows(_ => b.discard(10), 'Buffer discard');
    
    console.log('SlidingSampleBuffer tests succeeded.');
    
}


function _assertEquals(actual, expected, description) {
    if (actual !== expected)
        _handleTestError(actual, expected, description);
}


function _handleTestError(actual, expected, description) {
    throw new Error(
        `Test error: expected ${description} of ${expected} ` +
        `but found ${actual}.`);
}


function _assertBuffer(b, expectedStartIndex, expectedContents) {
    
    _assertEquals(b.startIndex, expectedStartIndex, 'start index');
            
    _assertArraysEqual(b.contents, expectedContents);
                   
    const expectedSize = expectedContents.length;
    _assertEquals(b.size, expectedSize, 'size');
    
    const expectedEndIndex = expectedStartIndex + expectedSize;
    _assertEquals(b.endIndex, expectedEndIndex, 'end index');

}


function _assertArraysEqual(actual, expected, description) {
    
    _assertEquals(actual.length, expected.length, description);
            
    for (let i = 0; i < actual.length; i++)
        if (actual[i] !== expected[i])
            _handleTestError(expectedContents, actualContents, description);

}


function _assertThrows(f, description) {
    
    try {
        
        f();
        
    } catch (error) {
        
        console.log(
            `${description} failed as expected with message: ` +
            `${error.message}`);
            
        return;
            
    }
    
    throw new Error(`${description} did not fail as expected.`);
    
}


// _testSampleBuffer();


/*
class _SlidingWindowBuffer {
    
    
    constructor(maxWindowSize, initialPadding=0) {
        this._buffer = new Float32Array(maxWindowSize);
        this._bufferStartIndex = -initialPadding;
        this._windowStartOffset = 0;
        this._windowEndOffset = initialPadding;
    }
    
    
    get maxWindowSize() {
        return this._buffer.length;
    }
    
    
    get windowStartIndex() {
        return this._bufferStartIndex + this._windowStartOffset;
    }
    
    
    get windowEndIndex() {
        return this._bufferStartIndex + this._windowEndOffset;
    }
    
    
    get windowSize() {
        return this._windowEndOffset - this._windowStartOffset;
    }
    
    
    get window() {
        return this._buffer.subarray(
            this._windowStartOffset, this._windowEndOffset);
    }
    
    
    pushSamples(samples) {
        
        const length = samples.length;
        
        if (this.windowSize + length > this.maxWindowSize)
            throw new Error('_SlidingWindowBuffer overflow');
        
        // Slide window to beginning of buffer if needed to make room
        // for new samples.
        if (this._windowEndOffset + length > this.maxWindowSize) {
            this.copyWithin(0, this._windowStartOffset, this._windowEndOffset);
            this._windowEndOffset -= this._windowStartOffset;
            this._windowStartOffset = 0
        }
        
        // Copy new samples into buffer.
        let j = this._windowEndOffset;
        for (let i = 0; i != length; i++)
            this._buffer[j++] = samples[i];
            
        // Update window end offset.
        this._windowEndOffset += length;
        
    }
    
    
    popSamples(sample_count) {
        
        if (sample_count > this.windowSize)
            throw new Error('_SlidingWindowBuffer underflow');
            
        this._windowStartOffset += sample_count;
        
    }
    
    
}
*/


class _Resampler {
    
    
    constructor() {
        
        const initialSize = -(_lowpassFilter.length - 1) / 2;
        
        this._buffer = new SlidingSampleBuffer(
            _resamplerBufferCapacity, initialSize);
        
    }
    
    
    process(samples) {
        
        this._buffer.append(samples);
        buffer = this._buffer.contents;
        
        
    }
    
    
}


/*
Sample chunker.

A `Chunker` partitions a stream of samples into fixed-size chunks.
The chunks are of type `Int16Array`. A `Chunker` optionally scales the
samples as it collects them.

A `Chunker` allocates each new chunk afresh, and relies on JavaScript
to garbage collect the allocated chunks when they are no longer needed.
A more storage-efficient approach would reuse chunks from a fixed-size
pool, but that would require chunk consumers to explicitly free chunks
when they were done with them.
 */
class _Chunker {
    
    constructor(chunkSize, scaleFactor = null) {
        
        this._chunkSize = chunkSize;
        this._scaleFactor = scaleFactor;
        
        this._chunk = new Int16Array(chunkSize);
        this._writeIndex = 0;
        
    }
    
    get chunkSize() {
        return this._chunkSize;
    }
    
    get scaleFactor() {
        return this._scaleFactor;
    }
    
    chunk(samples) {
        
        let sampleCount = samples.length;
        let readIndex = 0;
        const scaleFactor = this.scaleFactor;
        
        const chunks = [];
        let chunk = this._chunk;
        let writeIndex = this._writeIndex;
        
        while (sampleCount !== 0) {
            
            const freeSize = this.chunkSize - writeIndex;
            const copySize = Math.min(sampleCount, freeSize);
            
            if (this._scaleFactor !== null) {
                // scaling enabled
                
                for (let i = 0; i < copySize; i++)
                    chunk[writeIndex++] =
                        Math.round(scaleFactor * samples[readIndex++]);
                
            } else {
                // scaling disabled
                
                for (let i = 0; i < copySize; i++)
                    chunk[writeIndex++] = Math.round(samples[readIndex++]);
                        
            }
            
            sampleCount -= copySize;
            
            if (writeIndex === this.chunkSize) {
                // finished this chunk
                
                // Append chunk to chunks array.
                chunks.push(chunk);
                
                // Allocate a new chunk.
                chunk = new Int16Array(this.chunkSize);
                writeIndex = 0;
                
            }

        }
        
        // Save current chunk state.
        this._chunk = chunk;
        this._writeIndex = writeIndex;
        
        return chunks;
        
    }
    
}


function _testChunker() {
    
    console.log('Testing Chunker:');
    
    const chunker = new _Chunker(3, 2);
    const writeSize = 5;
    const samples = new Float32Array(writeSize);
    
    let k = 0;
    
    for (let i = 0; i < 10; i++) {
        
        for (let j = 0; j < writeSize; j++)
            samples[j] = k++;
            
        chunks = chunker.chunk(samples);
        
        console.log(i, chunks);
        
    }
    
}


async function _main() {

    // _testChunker();
    
    _audioInputDevices = await _getAudioInputDevices();

    _populateDevicesSelect();
    _initializeRecordButton();

    // _showDevices(_audioInputDevices);

}


async function _getAudioInputDevices() {

    try {

        // Try to get an audio input stream to trigger browser's permission
        // dialog if we don't already have permission to record audio. We
        // won't actually use the input stream: we just want to make sure
        // we have permission to record audio before we enumerate devices.
        // If we enumerate devices without permission to record audio we
        // won't get the devices' labels (i.e. their names), only their IDs.
        await navigator.mediaDevices.getUserMedia({audio: true});

        const allDevices = await navigator.mediaDevices.enumerateDevices();

        const audioInputDevices = allDevices.filter(
            device => device.kind === 'audioinput');
            
        const deviceUsabilities = await Promise.all(
            audioInputDevices.map(device => _isUsableInputDevice(device)));
            
        const usableInputDevices = [];
        for (const [i, device] of audioInputDevices.entries())
            if (deviceUsabilities[i])
                usableInputDevices.push(device);
                
        return usableInputDevices;

    } catch (error) {

        console.log(
            `Error getting audio input devices: ${error.name}: ` +
            `${error.message}`);

        return [];

    }

}


async function _isUsableInputDevice(device) {
    
    for (const settings of _ACCEPTABLE_INPUT_SETTINGS) {
        
        const result = await _inputDeviceSupportsSettings(device, ...settings);
        
        if (result) {
            _usableInputDeviceSettings.set(device.deviceId, settings);
            return true;
        }
            
    }
    
    return false;
    
}


async function _inputDeviceSupportsSettings(device, sampleRate, channelCount) {

    const query = [
        device.deviceId, sampleRate, channelCount, _REQUIRED_SAMPLE_SIZE,
        _REQUIRED_AUTO_GAIN_CONTROL, _REQUIRED_ECHO_CANCELLATION,
        _REQUIRED_NOISE_SUPPRESSION];

    const constraints = _createConstraints(...query);

    let stream = null;
    
    try {
        
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        
    } catch (error) {
            
/*
        const message = 
            error.name === 'OverconstrainedError'
            ? error.constraint : error.message;
            
        console.log(
            `Error querying audio input capability: ${error.name}: ` +
            `${message}`);
*/            

        return false;

    }
    
    const s = _getStreamSettings(stream);
    
    const result = [
        s.deviceId, s.sampleRate, s.channelCount, s.sampleSize,
        s.autoGainControl, s.echoCancellation, s.noiseSuppression]
    
    //_showQueryAndResult(query, result);
    
    return _arraysEqual(query, result);

}


function _showQueryAndResult(query, result) {
    console.log('\n');
    _showArray(' query', query);
    _showArray('result', result);
}


function _showArray(name, a) {
    // a[0] = _audioInputDevicesById.get(a[0]).label;
    const elements = a.map(e => `${e}`);
    console.log(`${name}: ${elements.join(',')}`);
}


function _arraysEqual(a, b) {
    
    if (a.length !== b.length) {
        
        return false;
        
    } else {
        
        for (let i = 0; i < a.length; i++)
            if (a[i] !== b[i])
                return false;
                
    }
    
    return true;

}


function _createConstraints(
        deviceId, sampleRate, channelCount,
        sampleSize = _REQUIRED_SAMPLE_SIZE,
        autoGainControl = _REQUIRED_AUTO_GAIN_CONTROL,
        echoCancellation = _REQUIRED_ECHO_CANCELLATION,
        noiseSuppression = _REQUIRED_NOISE_SUPPRESSION) {
    
    return {

        audio: {
            deviceId: { exact: deviceId },
            channelCount: { exact: channelCount },
            sampleRate: { exact: sampleRate },
            sampleSize: { exact: sampleSize },
            autoGainControl: { exact: autoGainControl },
            echoCancellation: { exact: echoCancellation },
            noiseSuppression: { exact: noiseSuppression }
        }
        
    };
    
}


function _getStreamSettings(stream) {
    
    const tracks = stream.getAudioTracks();
    
    if (tracks.length > 1)
        console.log(
            `In _getStreamSettings, stream has ${tracks.length} ` +
            `tracks instead of just one. Will return settings ` +
            `for first track.`);
            
    return tracks[0].getSettings();
    
}

function _populateDevicesSelect() {

    const select = document.getElementById('devices-select');

    for (const device of _audioInputDevices) {

        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label;
        select.add(option);

    }

}


function _initializeRecordButton() {
    const button = document.getElementById('record-button');
    button.onclick = _onRecordButtonClick;
    _updateRecordButtonText();
}


function _updateRecordButtonText() {
    const button = document.getElementById('record-button');
    button.innerHTML = _recording ? 'Stop' : 'Record';
}


function _onRecordButtonClick(e) {

    if (!_recording) {

        _startRecording();

    } else {

        _stopRecording();

    }

}


function _getSelectedDevice() {
    const select = document.getElementById('devices-select');
    return _audioInputDevices[select.selectedIndex];
}


async function _startRecording() {

    _recordingId = await _getNewRecordingId();
    _recordingLength = 0;
    
    console.log(`new recording ID: ${_recordingId}`);
    
    const device = _getSelectedDevice();
    
    console.log(
        `_startRecording device label "${device.label}", ` +
        `ID "${device.deviceId}"`);

    const [sampleRate, channelCount] =
        _usableInputDeviceSettings.get(device.deviceId);
        
    _chunker = _createChunker(sampleRate);
    
    const constraints = _createConstraints(
        device.deviceId, sampleRate, channelCount);
    
    let stream = null;
    
    try {
        
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        
    } catch (error) {
            
        console.log(
            `Attempt to get audio input stream failed with message: ` +
            `${error.message}`);
            
        return;
            
    }

    _showStream(stream);

    const context = new AudioContext({
        sampleRate: sampleRate
    });

    try {
        
        await context.audioWorklet.addModule(_RING_BUFFER_PROCESSOR_PATH);
        
    } catch (error) {
        
        console.log(
            `Attempt to add ring buffer audio worklet module failed ` +
             `with message: ${error.message}`);
             
        return;

    }

    const source = context.createMediaStreamSource(stream);

    const ringBuffer = new AudioWorkletNode(context, 'ring-buffer-processor');

    ringBuffer.port.onmessage = _onRingBufferProcessorMessage;

    source.connect(ringBuffer)
    ringBuffer.connect(context.destination);

    _audioContext = context;

    _recording = true;

    _updateRecordButtonText();

    console.log('Recording started!');

}


function _createChunker(sampleRate) {
    const chunkSize = Math.round(_SAMPLE_CHUNK_DURATION * sampleRate);
    const scaleFactor = _SAMPLE_SCALE_FACTOR;
    return new _Chunker(chunkSize, scaleFactor);
}


async function _onRingBufferProcessorMessage(event) {
    
    let samples = event.data.samples;
    
    if (_resampler !== null)
        samples = _resampler.process(samples);
    
    const chunks = _chunker.chunk(samples);
    
    for (const chunk of chunks) {
        await _appendSamplesToRecording(chunk);
        _recordingLength += chunk.length;
    }
    
/*
    const sampleCount = samples.length;
    console.log(
        `Ring buffer node received ${sampleCount} samples from processor.`);
*/

}


async function _getNewRecordingId() {
    
    try {
        
        const response = await axios.post('/record/');
        return response.data.recordingId;
        
    } catch (error) {
        
        console.error(`Error getting new recording ID: ${error}`);
        return null;
        
    }
        
}


async function _appendFakeSamplesToRecording() {
    
    try {
        
        const sampleCount = 10;
        const samples = new Int16Array(sampleCount);
        for (let i = 0; i <= sampleCount; i++)
            samples[i] = i;

        _appendSamplesToRecording(samples)
        
        console.log('Successfully appended samples to recording.');
        
    } catch (error) {
        
        console.error(`Error appending samples to recording: ${error}`);
        
    }
    
}


async function _appendSamplesToRecording(samples) {
    
    const headerSize = 24;
    const sampleSize = 2;
    const buffer = new ArrayBuffer(headerSize + sampleSize * samples.length);
    const view = new DataView(buffer);
    
    let offset = 0;
    
    // Set action.
    view.setUint32(offset, 0, true);
    offset += 4;
    
    // Set recording ID.
    view.setFloat64(offset, _recordingId, true);
    offset += 8;
    
    // Set start index.
    view.setFloat64(offset, _recordingLength, true);
    offset += 8;
    
    // Set sample endianness.
    view.setUint32(offset, _platformIsLittleEndian, true)
    offset += 4
    
    // Set samples.
    const samplesDest = new Int16Array(buffer, offset);
    samplesDest.set(samples);
    
    const headers = {'Content-Type': 'application/octet-stream'}
    
    await axios.post('/recordings/', buffer, headers);

}


function _showStream(stream) {

    console.log('_startRecording got stream:');
    const tracks = stream.getAudioTracks();
    for (const track of tracks) {
        console.log('    track:');
/*        const capabilities = track.getCapabilities();
        console.log('        capabilities:', capabilities);
*/        const settings = track.getSettings();
        console.log('        settings:', settings);
    }

}


function _stopRecording() {

    console.log('_stopRecording');

    _audioContext.close();
    _audioContext = null;

    _recording = false;

    _updateRecordButtonText();

}


function _showDevices(devices) {
    console.log('Audio input devices:');
    for (const device of devices)
        console.log(
            `    label "${device.label}", id "${device.deviceId}"`);
}


_main();
