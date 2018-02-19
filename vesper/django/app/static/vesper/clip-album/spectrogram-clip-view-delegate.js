'use strict'


import { ClipViewDelegate } from './clip-view-delegate.js';
import { Spectrogram } from '../signal/spectrogram.js';
import { DataWindow } from '../signal/data-window.js';
import { TimeFrequencyUtils } from './time-frequency-utils.js';


export class SpectrogramClipViewDelegate extends ClipViewDelegate {

    // TODO: Update view in response to settings changes, recomputing
	// as little as possible.

	onClipSamplesChanged() {

        const clip = this.clipView.clip;

        if (clip.samples !== null) {
            // have clip samples

//            console.log(
//                `computing and drawing spectrogram for clip ${clip.num}...`);

            const settings = this.settings.spectrogram;

            _augmentSpectrogramSettings(settings, clip.sampleRate);

            // Compute spectrogram, offscreen spectrogram canvas, and
            // spectrogram image data and put image data to canvas. The
            // spectrogram canvas and the spectrogram image data have the
		    // same size as the spectrogram.
            this._spectrogram = _computeSpectrogram(clip.samples, settings);
            this._spectrogramCanvas =
                _createSpectrogramCanvas(this._spectrogram, settings);
            this._spectrogramImageData =
                _createSpectrogramImageData(this._spectrogramCanvas);
		    _computeSpectrogramImage(
                this._spectrogram, this._spectrogramCanvas,
                this._spectrogramImageData, settings);

		    // Draw spectrogram image.
            const canvas = this.clipView.canvas;
            _drawSpectrogramImage(
                clip, this._spectrogramCanvas, canvas, settings);

        } else {
            // do not have clip samples

//            console.log(
//                `freeing spectrogram memory for clip ${clip.num}...`);

            this._spectrogram = null;
            this._spectrogramCanvas = null;
            this._spectrogramImageData = null;

        }

    }


	render() {

		// For the time being we do nothing here, since apparently
		// an HTML canvas can resize images that have been drawn to
		// it automatically. We will need to do something here (or
		// somewhere, anyway) eventually to handle view settings
		// changes, for example changes to spectrogram settings
		// or color map settings.

	}


	getMouseText(event, name) {

		const x = event.clientX;
		const y = event.clientY;

	    // The sides of the bounding client rectangle of an HTML element
		// can have non-integer coordinates. We bump them to the nearest
		// integers for comparison to the integer mouse coordinates, and
		// assign time zero to the resulting left coordinate, the clip
		// duration to the right coordinate, the low view frequency to
		// the bottom coordinate, and the high view frequency to the top
		// coordinate.
		const r = this.clipView.div.getBoundingClientRect();
		const left = Math.ceil(r.left);
		const right = Math.floor(r.right);
		const top = Math.ceil(r.top);
		const bottom = Math.floor(r.bottom);

		if (x < left || x > right || y < top || y > bottom)
			// mouse outside view

			// The mouse is outside of the view for mouseleave events, and
			// (for some reason) even for some mousemove events.

			return null;

		else {
			// mouse inside view

			const clip = this.clipView.clip;

			const time = (x - left) / (right - left) * clip.span;

			const settings = this.settings.spectrogram;
			const [lowFreq, highFreq] =
			    TimeFrequencyUtils.getFreqRange(settings, clip.sampleRate / 2);
			const deltaFreq = highFreq - lowFreq;
			const freq = highFreq - (y - top) / (bottom - top) * deltaFreq;

			return `${time.toFixed(3)} s  ${freq.toFixed(1)} Hz`;

		}

	}


}


function _showAudioBufferInfo(b) {
	const samples = b.getChannelData(0);
    const [min, max] = _getExtrema(samples);
    console.log(
        'AudioBuffer', b.numberOfChannels, b.length, b.sampleRate, b.duration,
        min, max);
}


function _getExtrema(samples) {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const s of samples) {
    	if (s < min) min = s;
        if (s > max) max = s;
    }
    return [min, max];
}


function _scaleSamples(samples, factor) {
    for (let i = 0; i < samples.length; i++)
    	samples[i] *= factor;
}


function _augmentSpectrogramSettings(settings, sampleRate) {
    const windowSize = Math.round(settings.windowDuration * sampleRate);
    settings.window = DataWindow.createWindow('Hann', windowSize);
    settings.hopSize = Math.round(settings.hopDuration * sampleRate);
    settings.dftSize = _computeDftSize(
        windowSize, settings.dftSizeExponentIncrement);
}


function _computeDftSize(windowSize, exponentIncrement) {

    const exponent = Math.ceil(Math.log2(windowSize))

    if (exponentIncrement === undefined || exponentIncrement < 0)
        exponentIncrement = 0;

    return Math.pow(2, exponent + exponentIncrement);

}


function _computeSpectrogram(samples, settings) {
	const spectrogram = Spectrogram.allocateSpectrogramStorage(
        samples.length, settings);
	Spectrogram.computeSpectrogram(samples, settings, spectrogram);
	return spectrogram;
}


function _createSpectrogramCanvas(spectrogram, settings) {

	const numBins = settings.dftSize / 2 + 1;
	const numSpectra = spectrogram.length / numBins;

	const canvas = document.createElement('canvas');
	canvas.width = numSpectra;
	canvas.height = numBins;

	return canvas;

}


function _createSpectrogramImageData(canvas) {

	const numSpectra = canvas.width;
	const numBins = canvas.height;

	const context = canvas.getContext('2d');
	return context.createImageData(numSpectra, numBins);

}


function _computeSpectrogramImage(spectrogram, canvas, imageData, settings) {

	const numSpectra = canvas.width;
	const numBins = canvas.height;
	const data = imageData.data;

	// Get scale factor and offset for mapping the range
	// [settings.lowPower, settings.highPower] into the range [255, 0].
	const delta = settings.highPower - settings.lowPower
	const a = -255 / delta;
	const b = 255 * (1. - settings.lowPower / delta);

	// Map spectrogram values to pixel values.
	let m = 0;
	for (let i = 0; i < numBins; i++) {
		let k = numBins - 1 - i;
	    for (let j = 0; j < numSpectra; j++) {
			const v = a * spectrogram[k] + b;
			data[m++] = v;
			data[m++] = v;
			data[m++] = v;
			data[m++] = 255;
			k += numBins;
		}
	}

	// Write pixel values to spectrogram canvas.
	const context = canvas.getContext('2d');
	context.putImageData(imageData, 0, 0);

}


function _drawSpectrogramImage(clip, spectrogramCanvas, canvas, settings) {

	// Make sure clip view canvas has same size as spectrogram.
	const gramCanvas = spectrogramCanvas;
	if (canvas.width != gramCanvas.width)
	    canvas.width = gramCanvas.width;
	if (canvas.height != gramCanvas.height)
	    canvas.height = gramCanvas.height;

	const context = canvas.getContext('2d');

	// Draw gray background rectangle.
	context.fillStyle = 'gray';
	context.fillRect(0, 0, canvas.width, canvas.height);


	// Draw spectrogram from clip spectrogram canvas, stretching as needed.

    context.imageSmoothingEnabled = settings.smoothingEnabled;

    const numSpectra = gramCanvas.width;
    const numBins = gramCanvas.height;
    const halfSampleRate = clip.sampleRate / 2.;

    // Always draw entire spectrogram duration.
    const sX = 0;
    const sWidth = numSpectra;

    const [dX, dWidth] = _getSpectrogramXExtent(
            settings, numSpectra, clip, canvas.width);

    // Get view frequency range.
    const [startFreq, endFreq] =
	    TimeFrequencyUtils.getFreqRange(settings, halfSampleRate);

    if (startFreq >= halfSampleRate)
        // view frequency range is above that of spectrogram, so no
        // part of spectrogram will be visible

        return;

    const sStartFreq = startFreq;
    const sEndFreq = Math.min(endFreq, halfSampleRate);

    const sStartFreqY =
	    TimeFrequencyUtils.freqToGramY(sStartFreq, halfSampleRate, numBins);
    const sEndFreqY =
	    TimeFrequencyUtils.freqToGramY(sEndFreq, halfSampleRate, numBins);

    // The roles of sStartFreqY and sEndFreqY are reversed from what one
    // might expect in the following since frequency decreases (instead
    // of increasing) with increasing gram image y coordinate.
    const sY = sEndFreqY
    const sHeight = sStartFreqY - sEndFreqY;

    const h = canvas.height
    const dStartFreqY =
	    TimeFrequencyUtils.freqToViewY(sStartFreq, startFreq, endFreq, h);
    const dEndFreqY =
	    TimeFrequencyUtils.freqToViewY(sEndFreq, startFreq, endFreq, h);

    const dY = dEndFreqY;
    const dHeight = dStartFreqY - dEndFreqY;

    context.drawImage(
        gramCanvas, sX, sY, sWidth, sHeight, dX, dY, dWidth, dHeight);

}


function _getSpectrogramXExtent(settings, numSpectra, clip, canvasWidth) {

    if (settings.timePaddingEnabled) {

        	const sampleRate = clip.sampleRate;
        	const startTime = settings.window.length / 2 / sampleRate;
        	const spectrumPeriod = settings.hopSize / sampleRate;
        	const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
        	const span = (clip.length - 1) / sampleRate;
        	const pixelPeriod = span / canvasWidth;
        	const x = startTime / pixelPeriod;
        	const width = (endTime - startTime) / pixelPeriod;
        	return [x, width];

    } else {

        return [0, canvasWidth];

    }

}
