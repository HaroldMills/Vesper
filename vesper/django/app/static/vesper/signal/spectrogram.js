import { Dft } from '/static/vesper/signal/dft.js';


function createDataWindow(name, size) {

	if (name === "Rectangular")
		return createRectangularWindow(size);

	else if (name === "Hann")
		return createHannWindow(size);

	else
		throw `Unrecognized window type "${name}".`;

}


function createRectangularWindow(size) {
	const w = new Float64Array(size);
	for (let i = 0; i < size; i++)
		w[i] = 1;
	return w;
}


function createHannWindow(size) {
	const w = new Float64Array(size);
	const f = Math.PI / size;
	for (let i = 0; i < size; i++) {
		const sine = Math.sin(f * i);
		w[i] = sine * sine;
	}
	return w;
}


function allocateSpectrogramStorage(inputLength, params) {
	const p = params;
	const spectrumSize = p.dftSize / 2 + 1;
	return _allocateOutputSampleArrays(
		inputLength, p.window.length, p.hopSize, spectrumSize)
}


function _allocateOutputSampleArrays(
	    inputLength, inputBlockSize, inputHopSize, outputSampleArraySize) {
	const numBlocks =
		_getNumInputBlocks(inputLength, inputBlockSize, inputHopSize);
	return new Float32Array(numBlocks * outputSampleArraySize);
}


function _getNumInputBlocks(inputLength, inputBlockSize, inputHopSize) {
	if (inputLength < inputBlockSize)
		return 0;
	else
		return 1 + Math.floor((inputLength - inputBlockSize) / inputHopSize);
}


function computeSpectrogram(x, params, X) {

	const p = params;

	const window = p.window;
	const windowSize = window.length;
	const hopSize = p.hopSize;
	const dftSize = p.dftSize;
	const inputLength = x.length;
	const numSpectra = _getNumInputBlocks(inputLength, windowSize, hopSize);
	const spectrumSize = dftSize / 2 + 1;

	// Allocate storage for windowed and zero padded DFT input.
    const xx = new Float64Array(dftSize);

    // Allocate storage for DFT output.
    const XX = new Float64Array(dftSize);

	let inputStart = 0;
	let inputEnd = inputStart + windowSize;
	let i = 0;
	let j = 0;
	let k = 0;
	const m = spectrumSize - 1;

	while (inputEnd <= inputLength) {

		// Get next input block and apply window.
		j = inputStart;
		for (i = 0; i < windowSize; i++)
			xx[i] = x[j++] * window[i];

		// Compute DFT.
		Dft.realFft(xx, XX);

		// Compute DFT magnitude squared. We double the values in the
		// non-DC and non-Fs/2 bins to include energy from the negative
		// frequency DFT bins.
		X[k++] = XX[0] * XX[0];
		i = 1;
		j = dftSize - 1;
		while (i < m) {
			const re = XX[i++];
		    const im = XX[j--];
			X[k++] = 2 * (re * re + im * im);
		}
		X[k++] = XX[m] * XX[m];

		inputStart += hopSize;
		inputEnd += hopSize;

	}

	if (p.referencePower !== null) {
        const outputLength = numSpectra * spectrumSize;
        _computeDbValues(X, outputLength, p.referencePower);
	}

	return X;

}


function _computeDbValues(X, length, referencePower) {

	/*
	 * We clip ratios to a minimum value before taking logs to avoid
	 * winding up with -Infinity values in the output. These would
	 * otherwise occur for any ratio smaller than about 1e-324, including
	 * of course zero. Having large negative values in the output is
	 * preferable to having -Infinity values since the latter may not
	 * play well with other numbers in subsequent arithmetic. For
	 * example, 0 times -Infinity is NaN.
	 */
	const minRatio = 1e-100;
	const minDbValue = 10 * Math.log10(minRatio);

	for (let i = 0; i < length; i++) {

		let r = X[i] / referencePower;

		if (r < minRatio)
			X[i] = minDbValue;
		else
		    X[i] = 10 * Math.log10(r);

	}

}


export const Spectrogram = {
    'createDataWindow': createDataWindow,
    'createRectangularWindow': createRectangularWindow,
    'createHannWindow': createHannWindow,
    'allocateSpectrogramStorage': allocateSpectrogramStorage,
    'computeSpectrogram': computeSpectrogram
};
