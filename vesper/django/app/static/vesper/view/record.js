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


import { DecimatingFirFilter }
    from '/static/vesper/signal/decimating-fir-filter.js';
import { recorderFilterCoefficients } from './recorder-filter-coefficients.js';
import { SampleChunker } from '/static/vesper/signal/sample-chunker.js';


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


const _decimationFactor = 2;


async function _main() {

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
        
    _resampler = new DecimatingFirFilter(
        recorderFilterCoefficients, _decimationFactor);
        
    _chunker = _createChunker(sampleRate / _decimationFactor);
    
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
    return new SampleChunker(chunkSize, scaleFactor);
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
