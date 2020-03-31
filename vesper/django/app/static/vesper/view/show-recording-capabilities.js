/*
Shows recording capabilities for one of the available audio input devices.

This code uses the `navigator.mediaDevices.enumerateDevices` function to
determine the available devices, and the `navigator.mediaDevices.getUserMedia`
function to query a device's capabilities.
*/


const _QUERY_SAMPLE_RATES = [22050, 24000, 32000, 44100, 48000];
const _QUERY_CHANNEL_COUNTS = [1, 2];
const _QUERY_SAMPLE_SIZES = [16];
const _QUERY_AUTO_GAIN_CONTROL = false;
const _QUERY_ECHO_CANCELLATION = false;
const _QUERY_NOISE_SUPPRESSION = false;


let _audioInputDevices = null;
let _audioInputDevicesById = null;
let _genericQuerySettings = null;


async function _main() {
    
    _audioInputDevices = await _getAudioInputDevices();
    
    _audioInputDevicesById =
        new Map(_audioInputDevices.map(d => [d.deviceId, d]));
        
    _populateDevicesSelect();
    
    _genericQuerySettings = _getGenericQuerySettings();
    
    await _showCapabilitiesForSelectedDevice();
    
}


async function _getAudioInputDevices() {

    // Try to get an audio input stream to trigger browser's permission
    // dialog if we don't already have permission to record audio. We
    // won't actually use the input stream: we just want to make sure
    // we have permission to record audio before we enumerate devices.
    // If we enumerate devices without permission to record audio we
    // won't get the devices' labels (i.e. their names), only their IDs.

    try {

        await navigator.mediaDevices.getUserMedia({audio: true});

        const allDevices = await navigator.mediaDevices.enumerateDevices();

        const audioInputDevices = allDevices.filter(
            device => device.kind === 'audioinput');

        return audioInputDevices;

    } catch (e) {

        console.log(
            `Error getting audio input devices: ${e.name}: ${e.message}`);

        return [];

    }

}


function _populateDevicesSelect() {

    const select = document.getElementById('devices-select');

    for (const device of _audioInputDevices) {

        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label;
        select.add(option);

    }
    
    select.onchange = _ => _showCapabilitiesForSelectedDevice();

}


function _getGenericQuerySettings() {
    
    const variableSettings = _getCartesianProduct(
        _QUERY_SAMPLE_RATES, _QUERY_CHANNEL_COUNTS, _QUERY_SAMPLE_SIZES);
        
    const constantSettings = [
        _QUERY_AUTO_GAIN_CONTROL, _QUERY_ECHO_CANCELLATION,
        _QUERY_NOISE_SUPPRESSION]
        
    return variableSettings.map(s => s.concat(constantSettings));
        
}


function _getCartesianProduct(...arrays) {
    return arrays.reduce(function(a,b){
        return a.map(function(x){
            return b.map(function(y){
                return x.concat(y);
            })
        }).reduce(function(a,b){ return a.concat(b) },[])
    }, [[]])
}


async function _showCapabilitiesForSelectedDevice() {
    const device = _getSelectedDevice();
    const settings = await _getRecordingCapabilities(device);
    _updateSettingsTable(settings);
}


function _getSelectedDevice() {
    const select = document.getElementById('devices-select');
    return _audioInputDevices[select.selectedIndex];
}


async function _getRecordingCapabilities(device) {
    
    const deviceId = device.deviceId;
    
    const queries = _getSpecificQuerySettings(deviceId);
    
    const results = await Promise.all(
        queries.map(q => _queryRecordingCapability(q)));
    
    const capabilities = [];
    
    for (const [i, query] of queries.entries()) {
    
        const result = results[i];
        
        if (result !== null) {
            
            //_showQueryAndResult(query, result);
            
            if (_arraysEqual(query, result))
                capabilities.push(query);
 
        }
        
    }
    
    return capabilities;

}


async function _showRecordingCapabilities(device) {
    
    const deviceId = device.deviceId;
    
    const querySettings = _getSpecificQuerySettings(deviceId);
    
    const resultSettings = await Promise.all(
        querySettings.map(s => _queryRecordingCapability(s)));
    
    _showSettings(querySettings, resultSettings);
    
}
            
            
function _getSpecificQuerySettings(deviceId) {
    const deviceIdArray = [deviceId];
    return _genericQuerySettings.map(s => deviceIdArray.concat(s))
}


async function _queryRecordingCapability(settings) {
    
    const constraints = _createConstraints(...settings);

    try {
        
        stream = await navigator.mediaDevices.getUserMedia(constraints);
            
    } catch (e) {
        
/*
        const message = 
            e.name === 'OverconstrainedError' ? e.constraint : e.message;
            
        console.log(
            `Error querying audio input capability: ${e.name}: ${message}`);
*/

        return null;
        
    }
    
    return _getStreamSettings(stream);
    
}


function _createConstraints(
        deviceId, sampleRate, channelCount, sampleSize, autoGainControl,
        echoCancellation, noiseSuppression) {
    
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
            
    s = tracks[0].getSettings();
    
    return [
        s.deviceId, s.sampleRate, s.channelCount, s.sampleSize,
        s.autoGainControl, s.echoCancellation, s.noiseSuppression];
    
}


function _showQueryAndResult(query, result) {
    console.log('\n');
    _showArray(' query', query);
    _showArray('result', result);
}


function _showArray(name, a) {
    a[0] = _audioInputDevicesById.get(a[0]).label;
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


function _updateSettingsTable(settings) {
    
    const table = document.getElementById('table');
    
    _removeIfPresent('table-header');
    _removeIfPresent('table-body');
    
    _appendTableHeader(table);
    _appendTableBody(table, settings);
    
}
    
   
function _removeIfPresent(id) {
    const element = document.getElementById(id);
    if (element !== null)
        element.remove();
} 


function _appendTableHeader(table) {
    
    const header = document.createElement('thead');
    header.id = 'table-header';
    
    const columnNames = ['Sample rate (Hz)', 'Channels', 'Sample size (bits)'];
    
    _appendTableRow(header, columnNames, 'th');
        
    table.appendChild(header);

}


function _appendTableRow(section, items, cellType) {
    
    const row = document.createElement('tr');
    
    for (const item of items) {
        
        const cell = document.createElement(cellType);
        const text = document.createTextNode(item);
        cell.appendChild(text);
        
        row.appendChild(cell);
    
    }
    
    section.appendChild(row);

}


function _appendTableBody(table, settings) {
    
    const body = document.createElement('tbody');
    body.id = 'table-body';
    
    for (const s of settings)
        _appendTableRow(body, s.slice(1, 4), 'td');
    
    table.appendChild(body);
        
}


_main();
