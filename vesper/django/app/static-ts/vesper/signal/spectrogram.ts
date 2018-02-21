import { Dft } from './dft.js';


export namespace Spectrogram {


	export function allocateSpectrogramStorage(
		inputLength: number, settings: any
	): Float32Array {
		const s = settings;
		const spectrumSize = s.dftSize / 2 + 1;
		const numSpectra =
		    getNumSpectra(inputLength, s.window.length, s.hopSize);
		return new Float32Array(numSpectra * spectrumSize);
	}


	export function getNumSpectra(
		inputLength: number, recordSize: number, hopSize: number
	): number {
		if (inputLength < recordSize)
			return 0;
		else
			return 1 + Math.floor((inputLength - recordSize) / hopSize);
	}


	export function computeSpectrogram(
		x: Float32Array, settings: any, y: Float32Array
	): Float32Array {

		const s = settings;

		const window = s.window;
		const windowSize = window.length;
		const hopSize = s.hopSize;
		const dftSize = s.dftSize;
		const inputLength = x.length;
		const numSpectra = getNumSpectra(inputLength, windowSize, hopSize);
		const spectrumSize = dftSize / 2 + 1;

		// Allocate storage for windowed and zero padded DFT input.
	    const xx = new Float64Array(dftSize);

	    // Allocate storage for DFT output.
	    const yy = new Float64Array(dftSize);

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
			Dft.computeRealForwardDft(xx, yy);

			// Compute DFT magnitude squared. We double the values in the
			// non-DC and non-Fs/2 bins to include energy from the negative
			// frequency DFT bins.
			y[k++] = yy[0] * yy[0];
			i = 1;
			j = dftSize - 1;
			while (i < m) {
				const re = yy[i++];
			    const im = yy[j--];
				y[k++] = 2 * (re * re + im * im);
			}
			y[k++] = yy[m] * yy[m];

			inputStart += hopSize;
			inputEnd += hopSize;

		}

		if (s.referencePower !== null) {
	        const outputLength = numSpectra * spectrumSize;
	        computeDbValues(y, outputLength, s.referencePower);
		}

		return y;

	}


	export function computeDbValues(
		x: Float32Array, length: number, referencePower: number
	) {

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

			let r = x[i] / referencePower;

			if (r < minRatio)
				x[i] = minDbValue;
			else
			    x[i] = 10 * Math.log10(r);

		}

	}


}
