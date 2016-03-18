// Web Audio recorder.


var recordButton = null;
var recording = false;
var audioRecorder = null;


window.onload = function() {
    
    recordButton = document.getElementById("recordButton");
    recordButton.onclick = onRecordButtonClick;
    updateRecordButton()

    initAudio();
    
};


function onRecordButtonClick() {
    if (recording) {
        stopRecording();
    } else {
        startRecording();
    }
}


function stopRecording() {
    console.log("stop");
    audioRecorder.stop();
    audioRecorder.getBuffer(gotBuffers);
    recording = false
    updateRecordButton();
}


function gotBuffers(buffers) {
    console.log("gotBuffers " + buffers.length + " " + buffers[0].length);
}


function startRecording() {
    console.log("record");
    name = createRecordingName();
    console.log("record " + name);
    audioRecorder.clear();
    audioRecorder.record();
    recording = true
    updateRecordButton();
}


function createRecordingName() {
	
	now = new Date();
	
	year = now.getUTCFullYear();
	month = zeroPad(now.getUTCMonth() + 1, 2);
	day = zeroPad(now.getUTCDate(), 2);
	date = [year, month, day].join('-');
	
	hour = zeroPad(now.getUTCHours(), 2);
	minute = zeroPad(now.getUTCMinutes(), 2);
	second = zeroPad(now.getUTCSeconds(), 2);
	ms = zeroPad(now.getUTCMilliseconds(), 3);
	
	time = [hour, minute, second, ms].join('.');
	
	return date + ' ' + time + ' UTC';
	
}


function zeroPad(i, n) {
	return ('00' + i).slice(-n);
}


function onPlayButtonClick() {
    console.log("play");
}


function updateRecordButton() {
    recordButton.innerHTML = recording ? "Stop" : "Record";
}


function initAudio() {
    promise = navigator.mediaDevices.getUserMedia({audio: true});
    promise.then(onGetUserMediaSuccess);
    promise.catch(onGetUserMediaFailure);    
}


function onGetUserMediaSuccess(mediaStream) {
    
    console.log("got user media");
    
    window.AudioContext = window.AudioContext || window.webkitAudioContext;

    // TODO: Can this fail?
    audioContext = new AudioContext();
    
    var audioInput = audioContext.createMediaStreamSource(mediaStream);
    audioRecorder = new Recorder(audioInput);
    
}


function onGetUserMediaFailure(error) {
    console.log(error);
}
