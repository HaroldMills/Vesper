import { CallsCleanupOverlay }
    from '/static/vesper/clip-album/calls-cleanup-overlay.js';
import { ClipView }
    from '/static/vesper/clip-album/clip-view.js';
import { TimeFrequencyPointOverlay }
    from '/static/vesper/clip-album/time-frequency-point-overlay.js';
import { TimeFrequencyUtils }
    from '/static/vesper/clip-album/time-frequency-utils.js';
import { TimePointOverlay }
    from '/static/vesper/clip-album/time-point-overlay.js';
import { Spectrogram } from '/static/vesper/signal/spectrogram.js';
import { DataWindow } from '/static/vesper/signal/data-window.js';


const _OVERLAY_CLASSES = {
    'Calls Cleanup Overlay': CallsCleanupOverlay,
    'Time-Frequency Point Overlay': TimeFrequencyPointOverlay,
    'Time Point Overlay': TimePointOverlay
}


const _DEFAULT_SPECTRAL_INTERPOLATION_FACTOR = 1;
const _DEFAULT_REFERENCE_POWER = 1e-10;
const _DEFAULT_NORMALIZE_BACKGROUND = false;
const _DEFAULT_FREQUENCY_RANGE = [0, 11025];
const _DEFAULT_COLORMAP = 'Gray';
const _DEFAULT_REVERSE_COLORMAP = true;


export class SpectrogramClipView extends ClipView {


    // TODO: Handle setting changes.


    constructor(clipAlbum, clip, settings) {

        settings = _updateSettingsIfNeeded(settings, clip.sampleRate);
        
        super(clipAlbum, clip, settings);

        const overlays = this._createOverlays(settings);
        this._overlays = overlays.concat(this._overlays);

    }


    _createOverlays(settings) {

        const overlays = [];

        const overlaySettings = settings.spectrogram.overlays;

        if (overlaySettings !== undefined) {

            for (const s of overlaySettings) {

                const overlayClass = _OVERLAY_CLASSES[s.type];

                if (overlayClass === undefined)
                    console.log(
                        `Unrecognized spectrogram view overlay type ` +
                        `"${s.type}".`);

                else
                    overlays.push(new overlayClass(this, s));

            }

        }

        return overlays;

    }


    // Since we override the settings setter, we must also override
    // the getter.
    get settings() {
        return super.settings;
    }

    
    set settings(settings) {
        settings = _updateSettingsIfNeeded(settings, this.clip.sampleRate);
        super.settings = settings;
    }
    
    
    get commandableName() {
		return 'Spectrogram Clip View';
	}


    _updateCanvas() {
        
        const clip = this.clip;

        if (clip.samples !== null) {
            // have clip samples

//            console.log(
//                `computing and drawing spectrogram for clip ${clip.num}...`);

            const settings = {};
            settings.high = this.settings.spectrogram.computation;
			settings.low = _getLowLevelSpectrogramSettings(
				settings.high, clip.sampleRate);
			settings.display = this.settings.spectrogram.display;


			// Compute spectrogram, offscreen spectrogram canvas, and
			// spectrogram image data. The spectrogram canvas and the
            // spectrogram image data have the same size as the
            // spectrogram.
            
			this._spectrogram = _computeSpectrogram(clip.samples, settings);

            // For investigating GitHub issue 197
            // (https://github.com/HaroldMills/Vesper/issues/197).
            if (this._spectrogram.length === 0) {

                console.log(
                    'Spectrogram length is zero in ' +
                    'spectrogram-clip-view._updateCanvas. ');

                console.log('Clip info:');
                console.log(`    num: ${clip.num}`);
                console.log(`    id: ${clip.id}`);
                console.log(`    startIndex: ${clip.startIndex}`);
                console.log(`    length: ${clip.length}`);
                console.log(`    sampleRate: ${clip.sampleRate}`);
                console.log(`    startTime: ${clip.startTime}`);
                console.log(`    sample array length: ${clip.samples.length}`);
                    
                return;
        
            }
            
            // _showSpectrogramStats(this._spectrogram, settings);
            
            if (settings.low.normalizeBackground)
                this._spectrogram = _normalizeSpectrogramBackground(
                    this._spectrogram, settings);
            
			this._spectrogramCanvas =
				_createSpectrogramCanvas(this._spectrogram, settings);
                
			this._spectrogramImageData =
				_createSpectrogramImageData(this._spectrogramCanvas);
                
			_computeSpectrogramImage(
				this._spectrogram, this._spectrogramCanvas,
				this._spectrogramImageData, settings);
                

			// Draw spectrogram image.
			const canvas = this.canvas;
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


    _render() {

        // TODO: Don't we need to re-render in case canvas size has changed?

		// For the time being we do nothing here, since apparently
		// an HTML canvas can resize images that have been drawn to
		// it automatically. We will need to do something here (or
		// somewhere, anyway) eventually to handle view settings
		// changes, for example changes to spectrogram settings
		// or color map settings.

	}


    getMouseText(event) {

        const tf = this.getMouseTimeAndFrequency(event);

        if (tf === null)
            return null;

        else {
            const [time, freq] = tf;
            return `${time.toFixed(3)} s  ${freq.toFixed(1)} Hz`;
        }

    }


    getMouseTimeAndFrequency(event) {

        const x = event.clientX;
        const y = event.clientY;
    
        // The sides of the bounding client rectangle of an HTML element
        // can have non-integer coordinates, but the mouse position has
        // integer coordinates. We nudge the bounding rectangle coordinates
        // to the nearest integers inside the rectangle for time-frequency
        // computations so that the mouse position can attain the expected
        // extremal times and frequencies. That is, we assign time zero
        // to the leftmost mouse coordinate that is inside the rectangle,
        // the clip duration to the righmost coordinate, the low view
        // frequency to the bottommost coordinate, and the high view
        // frequency to the topmost coordinate.
        const r = this.div.getBoundingClientRect();
        const left = Math.ceil(r.left);
        const right = Math.floor(r.right);
        const top = Math.ceil(r.top);
        const bottom = Math.floor(r.bottom);
    
		const clip = this.clip;

		const time = (x - left) / (right - left) * clip.span;

		const [lowFreq, highFreq] = TimeFrequencyUtils.getFreqRange(
            this.settings.spectrogram.display, clip.sampleRate / 2);
		const deltaFreq = highFreq - lowFreq;
		const freq = highFreq - (y - top) / (bottom - top) * deltaFreq;

		return [time, freq];

	}


}


/**
 * Updates spectrogram clip view settings if needed.
 * 
 * This function provides a certain amount of backwards compatibility
 * with older settings presets.
 */
function _updateSettingsIfNeeded(settings, sampleRate) {
    
    if (settings.spectrogram.computation === undefined) {

        const old = settings.spectrogram;
    
        settings.spectrogram = {
    
            'computation': {
                'window': {
                    'type': 'Hann',
                    'size': old.windowSize / sampleRate
                },
                'hopSize': 100 * old.hopSize / old.windowSize,
                'spectralInterpolationFactor':
                    old.dftSize === undefined ? 1 :
                        old.dftSize / _getPowerOfTwoCeil(old.windowSize),
                'referencePower':
                    old.referencePower === undefined ?
                        _DEFAULT_REFERENCE_POWER : old.referencePower
            },
    
            'display': {
                'frequencyRange': _DEFAULT_FREQUENCY_RANGE,
                'powerRange': [old.lowPower, old.highPower],
                'colormap': _DEFAULT_COLORMAP,
                'reverseColormap': _DEFAULT_REVERSE_COLORMAP,
                'smoothImage':
                    old.smoothingEnabled === undefined ? true :
                        old.smoothingEnabled,
                'timeStretchEnabled':
                    old.timePaddingEnabled === undefined ? false :
                        !old.timePaddingEnabled
            },
    
            'overlays': []
    
        }
        
    }
    
    return settings;

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


function _getLowLevelSpectrogramSettings(settings, sampleRate) {

	const s = settings;
    const floatWindowSize = _getWindowSize(s.window.size, sampleRate);
    const windowSize = Math.round(floatWindowSize);
    const window = DataWindow.createWindow(s.window.type, windowSize);
    const hopSize = _getHopSize(s.hopSize, sampleRate, floatWindowSize);
    const dftSize = _getDftSize(windowSize, s);
	const referencePower = _getReferencePower(s.referencePower);
    const normalizeBackground = _getNormalizeBackground(s.normalizeBackground);

	return {
		window: window,
		hopSize: hopSize,
		dftSize: dftSize,
		referencePower: referencePower,
        normalizeBackground: normalizeBackground
	};

}


function _getWindowSize(size, sampleRate) {

    // TODO: Add support for a variety of size units, for example:
    //     100
    //     100 samples
    //     .005 s
    //     .005 seconds
    //     5 ms
    //     5 milliseconds

    return size * sampleRate;

}


function _getHopSize(size, sampleRate, windowSize) {

    // TODO: Add support for a variety of size units, for example:
    //     50
    //     50 samples
    //     .0025 s
    //     .0025 seconds
    //     2.5 ms
    //     2.5 milliseconds
    //     50%
    //     50 %
    //     50 percent

    return Math.round(size / 100 * windowSize);

}


function _getDftSize(windowSize, settings) {

    const interpFactor =
        settings.spectralInterpolationFactor |
        _DEFAULT_SPECTRAL_INTERPOLATION_FACTOR;

    const powerOfTwoCeil = _getPowerOfTwoCeil(windowSize);

    if (Math.floor(interpFactor) !== interpFactor ||
			interpFactor <= 1 ||
		    !_isPowerOfTwo(interpFactor))

        return powerOfTwoCeil;

	else
	    return powerOfTwoCeil * interpFactor;

}


// Returns the smallest, positive, integer power of two that is at least `x`.
function _getPowerOfTwoCeil(x) {
    if (x <= 0)
        return 1;
    else
        return Math.pow(2, Math.ceil(Math.log2(x)));
}


function _isPowerOfTwo(n) {
	const log = Math.log2(n);
	return Math.floor(log) === log;
}


function _getReferencePower(referencePower) {
    return referencePower || _DEFAULT_REFERENCE_POWER;
}


function _getNormalizeBackground(normalizeBackground) {
    return normalizeBackground || _DEFAULT_NORMALIZE_BACKGROUND;
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


// This is similar to the other normalizing function in that it
// subtracts an estimate of the background and then applies an
// affine transformation to the result. The only difference is
// the affine transformation. The one here aims to leave signal
// bins more or less alone, and uses a scale factor of one. The
// other puts the background at zero dB and scales by something
// other than one to put the signal roughly in the range [50, 100].
function _normalizeSpectrogramBackgroundX(spectrogram, settings) {
    
    const percentile = 30;
    const gain = 1;
    
    const numBins = settings.low.dftSize / 2 + 1;
    const numSpectra = spectrogram.length / numBins;
    
    const backgroundSpectrum = _getSpectrogramBackgroundSpectrum(
        spectrogram, numBins, numSpectra, percentile);
    
    const backgroundSpectrumMedian =
        _getArrayPercentileValue(backgroundSpectrum, 50);
    
    const normalizedSpectrogram = new Float64Array(spectrogram.length);
    
    for (let i = 0; i < numBins; i++) {
        
        const offset =
            gain * (backgroundSpectrumMedian - backgroundSpectrum[i])
            
        let k = i;
        
        for (let j = 0; j < numSpectra; j++) {
            normalizedSpectrogram[k] = spectrogram[k] + offset;
            k += numBins;
        }
        
    }
    
    return normalizedSpectrogram;
    
}


function _normalizeSpectrogramBackground(spectrogram, settings) {
    
    const percentile = 30;
    const gain = 1;
    const scaleFactor = 1.5;
    const offset = 10;
    // const scaleFactor = 1;
    // const offset = 0;
    
    const numBins = settings.low.dftSize / 2 + 1;
    const numSpectra = spectrogram.length / numBins;
    
    const backgroundSpectrum = _getSpectrogramBackgroundSpectrum(
        spectrogram, numBins, numSpectra, percentile);
    
    const normalizedSpectrogram = new Float64Array(spectrogram.length);
    
    for (let i = 0; i < numBins; i++) {
        
        let k = i;
        
        for (let j = 0; j < numSpectra; j++) {
            
            normalizedSpectrogram[k] =
                scaleFactor * (spectrogram[k] - gain * backgroundSpectrum[i]) +
                offset;
                
            k += numBins;
        }
        
    }
    
    return normalizedSpectrogram;
    
}


function _getSpectrogramBackgroundSpectrum(
        spectrogram, numBins, numSpectra, percentile) {
    
    const spectrum = new Float64Array(numBins);
    
    for (let i = 0; i < numBins; i++)
        spectrum[i] = _getSpectrogramBackgroundBinValue(
            spectrogram, i, numBins, numSpectra, percentile);
                 
    return spectrum;

}


function _getSpectrogramBackgroundBinValue(
        spectrogram, binNum, numBins, numSpectra, percentile) {
    
    const histogramStartValue = 0;
    const histogramEndValue = 100;
    const histogram = new Uint32Array(histogramEndValue - histogramStartValue);
    
    let k = binNum;
    
    for (let i = 0; i < numSpectra; i++) {
        
        const binNum = _getHistogramBinNum(
            spectrogram[k], histogramStartValue, histogramEndValue);
        
        histogram[binNum] += 1;
        
        k += numBins;
        
    }
    
    const threshold = Math.round(numSpectra * percentile / 100.);
    
    let cumulativeValueCount = 0;
    
    for (let i = 0; i < histogram.length; i++) {
        
        cumulativeValueCount += histogram[i];
        
        if (cumulativeValueCount >= threshold)
            return histogramStartValue + i;
        
    }
    
}


function _getArrayPercentileValue(x, percentile) {
    const temp = x.slice();
    temp.sort((a, b) => a - b);
    const i = Math.round(percentile / 100. * (temp.length - 1));
    return temp[i];
}


function _showSpectrogramStats(spectrogram, settings) {
    
    const histogramStartValue = 0;
    const histogramEndValue = 100;
    const histogramLength = histogramEndValue - histogramStartValue;
    const histogram = new Uint32Array(histogramLength);
    
    let minValue = 1000000;
    let maxValue = -1000000;
    
    for (let i = 0; i < spectrogram.length; i++) {
        
        const value = spectrogram[i];
        
        if (value < minValue)
            minValue = value;
            
        if (value > maxValue)
            maxValue = value;
            
        const binNum = _getHistogramBinNum(
            value, histogramStartValue, histogramEndValue);
            
        histogram[binNum] += 1;
    
    }
    
    console.log(`spectogram min ${minValue} max ${maxValue}`);
    
    for (let i = 0; i < histogram.length; i++)
        console.log(`${histogramStartValue + i} ${histogram[i]}`);
    
}


function _getHistogramBinNum(value, startValue, endValue) {
    
    if (value < startValue)
        return 0;
        
    else if (value >= endValue)
        return endValue - startValue - 1;
        
    else
        return Math.floor(value);
    
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

    // The idea of the following was to allow the user to specify a
    // portion of a color map to use, rather than having to use the
    // whole thing. I'm not sure that would actually be very useful,
    // though, and it's one more thing for a user to learn about, so
    // for the time being at least I've removed it.
    // let [startColor, endColor] = settings.colorRange;

    let [startColor, endColor] = [0, 1];

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

    if (settings.display.timeStretchEnabled) {
        // spectrogram should be stretched to fill canvas width
	
	 	return [0, canvasWidth];
	
    } else {
        // spectrogram should not be stretched to fill canvas width

		const sampleRate = clip.sampleRate;
		const startTime = settings.low.window.length / 2 / sampleRate;
		const spectrumPeriod = settings.low.hopSize / sampleRate;
		const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
		const span = (clip.length - 1) / sampleRate;
		const pixelPeriod = span / canvasWidth;
		const x = startTime / pixelPeriod;
		const width = (endTime - startTime) / pixelPeriod;
		return [x, width];

    }

}
