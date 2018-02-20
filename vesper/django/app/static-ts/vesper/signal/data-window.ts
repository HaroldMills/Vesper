/*
 * Data windows for digital signal processing.
 *
 * The supported window types are:
 *
 *    Blackman
 *    Hamming
 *    Hann
 *    Nuttall
 *    Rectangular
 *
 * Both symmetric (for filtering) and non-symmetric (for spectral analysis)
 * windows are supported. To create a window, call the
 * `DataWindow.createWindow` function with appropriate arguments. For example,
 * to create a non-symmetric Hann window of size 100:
 *
 *     window = DataWindow.createWindow('Hann', 100, false);
 *
 * and to create a symmetric Hamming window of size 101:
 *
 *     window = DataWindow.createWindow('Hamming', 101, true);
 */


// TODO: Add Gaussian, Kaiser, and Slepian windows.


export namespace DataWindow {


	// Sum-of-cosines window weights, from scipy.signal.windows module.
	// Odd-indexed weights are negated compared to corresponding SciPy
	// values since we sum cosines starting at zero radians rather than
	// -pi radians.
	const _BLACKMAN_WEIGHTS = new Float64Array([0.42, -0.50, 0.08]);
	const _HAMMING_WEIGHTS = new Float64Array([.54, -.46]);
	const _HANN_WEIGHTS = new Float64Array([.5, -.5]);
	const _NUTTALL_WEIGHTS =
	    new Float64Array([0.3635819, -0.4891775, 0.1365995, -0.0106411]);


    const _windowFunctions = new Map([
		['Blackman', createBlackmanWindow],
		['Hamming', createHammingWindow],
		['Hann', createHannWindow],
		['Nuttall', createNuttallWindow],
		['Rectangular', createRectangularWindow]
	]);


	export function createBlackmanWindow(
		size: number, symmetric = true
	): Float64Array {
        return createSumOfCosinesWindow(size, _BLACKMAN_WEIGHTS, symmetric);
	}


	export function createSumOfCosinesWindow(
		size: number,
		weights: Float64Array,
		symmetric = true
	): Float64Array {

		_checkWindowSize(size);

		const window = new Float64Array(size);

        if (size > 1) {

			const period = symmetric ? size - 1 : size;
			for (let i = 0; i < weights.length; i++) {
				const weight = weights[i];
				const phaseFactor = i * 2 * Math.PI / period;
				for (let j = 0; j < size; j++)
				    window[j] += weight * Math.cos(phaseFactor * j);
			}

		} else if (size === 1) {

            // Single window coefficient is sum of weights.
		    for (let i = 0; i < weights.length; i++)
			    window[0] += weights[i];

		}

		return window;

	}


	function _checkWindowSize(size: number) {
		if (size < 0)
		    throw new Error('Window size must be nonnegative.');
		else if (Math.floor(size) !== size)
		    throw new Error('Window size must be an integer.');
	}


	export function createRectangularWindow(
		size: number, symmetric = true
	): Float64Array {

        _checkWindowSize(size);

		const window = new Float64Array(size);

		for (let i = 0; i < size; i++)
			window[i] = 1;

		return window;

	}


	export function createHammingWindow(
		size: number, symmetric = true
	): Float64Array {
        return createSumOfCosinesWindow(size, _HAMMING_WEIGHTS, symmetric)
	}


	export function createHannWindow(
		size: number, symmetric = true
	): Float64Array {
        return createSumOfCosinesWindow(size, _HANN_WEIGHTS, symmetric)
	}


	export function createNuttallWindow(
		size: number, symmetric = true
	): Float64Array {
        return createSumOfCosinesWindow(size, _NUTTALL_WEIGHTS, symmetric)
	}


	export function createWindow(
		name: string, size: number, symmetric = true
	): Float64Array {

        const windowFunction = _windowFunctions.get(name);

		if (windowFunction === undefined)
		    throw `Unrecognized window type "${name}".`;

		else
		    return windowFunction(size, symmetric);

	}


}
