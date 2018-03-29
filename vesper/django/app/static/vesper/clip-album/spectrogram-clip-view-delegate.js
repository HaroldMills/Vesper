import { ClipViewDelegate } from './clip-view-delegate.js';
import { Spectrogram } from '../signal/spectrogram.js';
import { DataWindow } from '../signal/data-window.js';
import { TimeFrequencyUtils } from './time-frequency-utils.js';


// TODO: Figure out how to share settings among the clip views of a
// clip album, and how to update views as efficiently as possible when
// settings change. Only views of the current page should update, and
// they should update as efficiently as possible. For example, if
// spectrogram computation settings do not change, spectrogram
// views should not recompute their spectrograms. Views that are
// not visible should not update, but rather should mark themselves
// as dirty so they can update later, if they are displayed.

// - TODO: Figure out why image smoothing doesn't seem to work.

// - TODO: Provide default values for missing optional settings.

// - TODO: Figure out a good default value for the reference power.

// - TODO: Brightness changes with window size. It should not.

// - TODO: Brightness changes with DFT size multiplier. It should not.

// TODO: Add some non-gray colormaps.


/*

Some ideas for Vesper clip albums:

* UI hierarchy:

    Clip Album:
        Displays a set of clips, with each clip in a clip view.

    Clip View:
        Displays information about one clip, e.g. one or more plots and
        a label.

    Clip Plot:
        Graphical representation of one clip, e.g. a waveform or spectrogram.

    Clip Plot Overlay:
        Overlay on a clip plot, usually containing graphical elements
        representing clip metadata, for example a time-frequency
        marker. An overlay may support interaction via mouse and/or key
        events, for example to edit the represented clip metadata.

* Allow keyboard commands to apply to the clip under the mouse, regardless
of the clip's selection status. This can be used for common operations like
playing a clip, but it can also be used for less common operations like
metadata creation. As an example of the latter, one might define the "m"
command to annotate a clip with the current time and frequency of the mouse,
and the "c" command to clear such an annotation. This requires two hands
(one hand on the mouse and the other on the keyboard) rather than one
(on the mouse), but provides more options (there are tens of buttons on
the keyboard, but only two on the mouse) and leaves current mouse usage
intact.

* Currently, how clip album keypresses are handled does not depend on the
mouse position. The clip album simply sends the keypress to the clip album's
command interpreter. We will want to change this so that a given command
can be handled differently depending on the mouse position. For example,
the "m" command might mark a time-frequency point when the mouse is over
a spectrogram view, mark a time point when it is over a waveform view, and
classify the selected clips otherwise. A good way to do this might be to
allow clip views and clip view overlays to have their own command
interpreters, and deliver a keypress to chains of such interpreters
depending on the mouse position. A keypress would propagate through
the relevant chain either until some element in the chain handled it
or until it came out the end. Such chains could be nested. For example,
If the mouse is over a clip view, a keypress would be offered to it
and then to the clip album. Internally, the clip view would offer
the keypress to the relevant subview, and the subview would in turn
offer it to its overlays and then to itself.

We might handle mouse events in a similar fashion. Then we would have
the option of using mouse clicks in clip views to create clip metadata
if we wanted.

I'd also like to work out how clip albums will relate to individual
clip displays. A clip album shows a set of identically-configured
clip displays, so some sharing of settings (like key bindings, for
example) might be a good idea.

* Generalize the clip view play button to a toolbar. Like the existing
play button, the toolbar only appears when the mouse is in a view, but
the toolbar can have any number of buttons on it. The toolbar might
appear in some compact form when the mouse first enters a clip view,
and then either expand to its full form if the user mouses over it
or fade away after a few seconds.

*/


/*

Overlays

A clip subview overlay can draw on the subview's overlay canvas, and also
send text to the view for display. For the time being, the view will display
the text in the view's label, but this might change in the future, for
example if we add a clip album footer.

A clip subview overlay can also listen for overlay canvas mouse events,
responding to them in various ways, for example by drawing on the overlay
canvas, sending text to the view, or editing clip metadata.

*/


/*
class ClipViewOverlay {


    constructor(clipView) {
		this._clipView = clipView;
	}


	get clipView() {
		return this._clipView;
	}


}


class AnnotatedTimeFrequencyPointOverlay extends ClipViewOverlay {


	constructor(clipView, settings) {

        // `settings` indicates the names of time and frequency
		// annotations and time/frequency point marker display
		// attributes.

		super(clipView);

		const canvas = clipView.overlayCanvas;
		canvas.addEventListener('click', e => this._onClick(e));

	}


	_onClick(e) {
		render();
		this.clipView.startOverlayTextUpdates();
		this._sendTimeFreqTextUpdate(e);
	}


	_onMouseMove(e) {
		this._sendTimeFreqTextUpdate(e);
	}


	_onMouseLeave(e) {
		this.clipView.endOverlayTextUpdates();
	}


}


class MouseTimeFrequencyOverlay extends ClipViewOverlay {


	constructor(clipView, settings) {

        // `settings` might indicate which of several time and frequency
		// indications the overlay might render. For example, the time
		// and frequency might be rendered as text and/or as vertical
		// and horizontal lines.

		super(clipView);

		const canvas = clipView.overlayCanvas;
		canvas.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    canvas.addEventListener('mousemove', e => this._onMouseMove(e));
	    canvas.addEventListener('mouseleave', e => this._onMouseLeave(e));

	}


	_onMouseEnter(e) {
		this.clipView.startOverlayTextUpdates();
		this._sendTimeFreqTextUpdate(e);
	}


	_onMouseMove(e) {
		this._sendTimeFreqTextUpdate(e);
	}


	_onMouseLeave(e) {
		this.clipView.endOverlayTextUpdates();
	}


}
*/


const _REFERENCE_POWER = 1e-10;


export class SpectrogramClipViewDelegate extends ClipViewDelegate {


	onClipSamplesChanged() {

        const clip = this.clipView.clip;

        if (clip.samples !== null) {
            // have clip samples

//            console.log(
//                `computing and drawing spectrogram for clip ${clip.num}...`);

            const settings = {};
            settings.high = this.settings.spectrogram.computation;
			settings.low = _computeLowLevelSpectrogramSettings(
				settings.high, clip.sampleRate);
			settings.display = this.settings.spectrogram.display;

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


    // onMouseEvent(event, name) {
	// 	console.log('onMouseEvent', name, event.clientX, event.clientY);
	// }


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


function _computeLowLevelSpectrogramSettings(settings, sampleRate) {

	const s = settings;
	const floatWindowSize = s.window.duration * sampleRate;
    const windowSize = Math.round(floatWindowSize);
    const window = DataWindow.createWindow(s.window.type, windowSize);
    const hopSize = Math.round(s.hopSize / 100 * floatWindowSize);
    const dftSize = _computeDftSize(windowSize, s.dftSizeMultiplier);
	const referencePower = _REFERENCE_POWER;

	return {
		window: window,
		hopSize: hopSize,
		dftSize: dftSize,
		referencePower: referencePower
	};

}


function _computeDftSize(windowSize, dftSizeMultiplier) {

    const minDftSize = Math.pow(2, Math.ceil(Math.log2(windowSize)))

    if (Math.floor(dftSizeMultiplier) !== dftSizeMultiplier ||
			dftSizeMultiplier <= 1 ||
		    !_isPowerOfTwo(dftSizeMultiplier))

        return minDftSize;

	else
	    return minDftSize * dftSizeMultiplier;

}


function _isPowerOfTwo(n) {
	const log = Math.log2(n);
	return Math.floor(log) === log;
}


function _computeSpectrogram(samples, settings) {
	const spectrogram = Spectrogram.allocateSpectrogramStorage(
        samples.length, settings.low);
	Spectrogram.computeSpectrogram(samples, settings.low, spectrogram);
	return spectrogram;
}


function _createSpectrogramCanvas(spectrogram, settings) {

	const numBins = settings.low.dftSize / 2 + 1;
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

	// Get scale factor and offset for mapping power to color value.
	const [a, b] = _getColorCoefficients(settings.display);

	// Here is how we used to compute `a` and `b`, but the "-" in the
	// computation of `b` should have been a "+". I will keep this around
	// to help us figure out how to update settings for users as needed.
	// const delta = highPower - lowPower;
	// const a = -255 / delta;
	// const b = 255 * (1. - lowPower / delta);

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


function _getColorCoefficients(settings) {

	const [startPower, endPower] = settings.powerRange;
	const [startColor, endColor] = _getColorRange(settings);

	const a = (endColor - startColor) / (endPower - startPower);
	const b = endColor - a * endPower;

	return [a, b];

}


function _getColorRange(settings) {

	let [startColor, endColor] = settings.colorRange;

	if (settings.reverseColormap) {
		startColor = 1 - startColor;
		endColor = 1 - endColor;
	}

    startColor = 255 * startColor;
	endColor = 255 * endColor;

	return [startColor, endColor];

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

    context.imageSmoothingEnabled = settings.display.smoothImage;

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
	    TimeFrequencyUtils.getFreqRange(settings.display, halfSampleRate);

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

    // if (settings.display.timeStretchEnabled) {
	//
	// 	return [0, canvasWidth];
	//
    // } else {

		const sampleRate = clip.sampleRate;
		const startTime = settings.low.window.length / 2 / sampleRate;
		const spectrumPeriod = settings.low.hopSize / sampleRate;
		const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
		const span = (clip.length - 1) / sampleRate;
		const pixelPeriod = span / canvasWidth;
		const x = startTime / pixelPeriod;
		const width = (endTime - startTime) / pixelPeriod;
		return [x, width];

    // }

}
