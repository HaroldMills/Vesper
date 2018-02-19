/*

Windows I'd like to offer:

Rectangular
Blackman [0.42, 0.50, 0.08]
Hamming [0.54, 0.46]
Hann [0.5, 0.5]
Nuttall [0.3635819, 0.4891775, 0.1365995, 0.0106411]
Gaussian
Kaiser
Slepian

*/


export namespace DataWindow {


	export function createWindow(
		name: string, size: number, symmetric = true
	): Float64Array {

		if (name === 'Rectangular')
			return createRectangularWindow(size, symmetric);

		else if (name === 'Hann')
			return createHannWindow(size, symmetric);

		else
			throw `Unrecognized window type "${name}".`;

	}


	export function createRectangularWindow(
		size: number, symmetric = true
	): Float64Array {

        _checkWindowSize(size);

		const w = new Float64Array(size);

		for (let i = 0; i < size; i++)
			w[i] = 1;

		return w;

	}


    function _checkWindowSize(size: number) {
		if (size < 0)
		    throw new Error('Window size must be nonnegative.');
		else if (Math.floor(size) !== size)
		    throw new Error('Window size must be an integer.');
	}


	export function createHannWindow(
		size: number, symmetric = true
	): Float64Array {

        _checkWindowSize(size);

		const w = new Float64Array(size);

		if (size >= 2) {

			const f = Math.PI / (symmetric ? size - 1 : size);

			for (let i = 0; i < size; i++) {
				const sine = Math.sin(f * i);
				w[i] = sine * sine;
			}

		}

		return w;

	}

}
