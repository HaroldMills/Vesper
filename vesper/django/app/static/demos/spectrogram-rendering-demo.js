import { Spectrogram } from '../signal/spectrogram.js';
import { Window } from '../signal/window.js';


const sampleRate = 22050;
let samples = null;


function testSpectrogramRendering() {

    samples = createTestSignal();

	const fileInput = document.getElementById('file-input');
	fileInput.addEventListener('change', onFileInputChange);

	const slider = document.getElementById('window-size-slider');
	slider.addEventListener('input', updateSpectrogram);

	const canvas = document.getElementById('test-canvas');
	canvas.width = 1500;
	canvas.height = 800;

	updateSpectrogram();

}


function createTestSignal() {

	const duration = 1;
	const n = Math.round(duration * sampleRate);
	const x = new Int16Array(n);

	const amplitude = 32767;
	const startFreq = 1000;
	const endFreq = 10000;
	const twoPi = 2 * Math.PI;
	const a = startFreq;
	const b = (endFreq - startFreq) / (2 * duration);
	for (let i = 0; i < n; i++) {
		const t = i / sampleRate;
		const phi = twoPi * (a * t + b * t * t);
		x[i] = Math.round(amplitude * Math.sin(phi));
	}

	return x;

}


function onFileInputChange(e) {
	const input = e.target;
	const file = input.files[0];
	console.log('file type "' + file.type + '"');
	updateSpectrogramForFile(file);
}


function updateSpectrogramForFile(file) {

	// In this function, if the sample rate of the file to be
	// read differs from the sample rate of the created
	// OfflineAudioContext, the file will be resampled.

	const context = new OfflineAudioContext(1, 1, 22050);
	const url = window.URL.createObjectURL(file);
	const request = new XMLHttpRequest();
	request.open('GET', url, true);
	request.responseType = 'arraybuffer';
	request.onload = () => {
		window.URL.revokeObjectURL(file);
		context.decodeAudioData(request.response).then(
			updateSpectrogramForAudioBuffer);
	}
	request.send();
}


function updateSpectrogramForAudioBuffer(audioBuffer) {
	const b = audioBuffer;
    console.log(
    	'decoded audio data', b.sampleRate, b.length, b.duration,
    	b.numberOfChannels);
    samples = b.getChannelData(0);
    for (let i = 0; i < samples.length; i++)
    	samples[i] *= 32767;
    updateSpectrogram();
}


function updateSpectrogramForFile2(file) {

	// This function doesn't seem to work: it yields all zero samples.
	// It also requires that we know the length of the file we're
	// reading in advance, and it resamples the file if its sample
	// rate differs from the one specified for the OfflineAudioContext.

	const url = window.URL.createObjectURL(file);
	const audio = new Audio();
	audio.src = url;
	document.body.appendChild(audio);

	const context = new OfflineAudioContext(1, 9081, 22050);
	const source = context.createMediaElementSource(audio);
	source.connect(context.destination);
    context.startRendering().then(audioBuffer => {
    	window.URL.revokeObjectURL(file);
    	updateSpectrogramForAudioBuffer(audioBuffer);
    });

}


function updateSpectrogram() {

	const settings = getSpectrogramSettings();
	const gram =
        Spectrogram.allocateSpectrogramStorage(samples.length, settings);
	Spectrogram.computeSpectrogram(samples, settings, gram);

	const canvas = document.getElementById('test-canvas');
	renderSpectrogram(gram, settings, canvas);

}


function getSpectrogramSettings() {

	const windowSize = getWindowSize();
	const hopSize = Math.round(windowSize * .25);
	const dftSize = Math.pow(2, Math.ceil(Math.log2(windowSize)));

	return {
		'window': Window.createWindow('Hann', windowSize),
		'hopSize': hopSize,
		'dftSize': dftSize,
		'referencePower': 1,
		'lowPower': 10,
		'highPower': 100,
		'smoothingEnabled': true,
		'timePaddingEnabled': true
	};

}


function getWindowSize() {
	const slider = document.getElementById('window-size-slider');
	return Math.round(Math.pow(2, slider.value));
}


function renderSpectrogram(gram, settings, canvas) {

	const numBins = settings.dftSize / 2 + 1;
	const numSpectra = gram.length / numBins;

	const gramCanvas = document.createElement('canvas');
	gramCanvas.width = numSpectra;
	gramCanvas.height = numBins;

	const gramCtx = gramCanvas.getContext('2d');

	const imageData = gramCtx.createImageData(numSpectra, numBins);
	const data = imageData.data;
	let spectrumNum = 0;
	let spectrumStride = numBins;
	let m = 0;
	const delta = settings.highPower - settings.lowPower
	const a = 255 / delta;
	const b = -255 * settings.lowPower / delta;
	for (let i = 0; i < numBins; i++) {
		let k = numBins - 1 - i
	    for (let j = 0; j < numSpectra; j++) {
			const v = 255 - a * gram[k] + b;
			data[m++] = v;
			data[m++] = v;
			data[m++] = v;
			data[m++] = 255;
			k += spectrumStride;
		}
	}

	gramCtx.putImageData(imageData, 0, 0);

	const ctx = canvas.getContext('2d');
	ctx.fillStyle = 'gray';
	ctx.fillRect(0, 0, canvas.width, canvas.height);
	ctx.imageSmoothingEnabled = settings.smoothingEnabled;

	if (settings.timePaddingEnabled) {
		let [x, width] = getSpectrogramXExtent(
			settings, numSpectra, samples.length, canvas.width);
		ctx.drawImage(gramCanvas, x, 0, width, canvas.height);
	} else {
		ctx.drawImage(gramCanvas, 0, 0, canvas.width, canvas.height);
	}

}


function getSpectrogramXExtent(settings, numSpectra, numSamples, canvasWidth) {
    const startTime = settings.window.length / 2 / sampleRate;
    const spectrumPeriod = settings.hopSize / sampleRate;
    const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
    const span = (numSamples - 1) / sampleRate;
    const pixelPeriod = span / canvasWidth;
    const x = startTime / pixelPeriod;
    const width = (endTime - startTime) / pixelPeriod;
    return [x, width];
}


window.onload = testSpectrogramRendering;
