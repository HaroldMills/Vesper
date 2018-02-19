import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { Spectrogram } from '/static/vesper/signal/spectrogram.js';
import { DataWindow } from '/static/vesper/signal/data-window.js';


/*
 * TODO: Use Python to create spectrogram test cases for a chirp signal,
 * including cases with various windows, overlap, zero padding, and both
 * linear and logarithmic output.
 */


describe('Spectrogram', () => {


    beforeEach(() => addAlmostEqualMatcher());


    it('getNumSpectra', () => {

        const cases = [

    	    /* hop size equal to block size */
    	    [[10, 5, 5], 2],
    	    [[10, 4, 4], 2],
    	    [[10, 3, 3], 3],
    	    [[10, 2, 2], 5],
    	    [[10, 1, 1], 10],

    	    /* hop size less than block size */
    	    [[10, 5, 4], 2],
    	    [[10, 5, 3], 2],
    	    [[10, 5, 2], 3],
    	    [[10, 5, 1], 6],

    	    /* hop size greater than block size */
    	    [[10, 2, 3], 3],
    	    [[10, 2, 4], 3],
    	    [[10, 2, 5], 2],
    	    [[10, 2, 6], 2],
    	    [[10, 2, 8], 2],
    	    [[10, 2, 9], 1],

    	    /* block size equal to number of samples */
    	    [[10, 10, 1], 1],

    	    /* block size greater than number of samples */
    	    [[10, 11, 1], 0]

    	];

    	for (const [args, expected] of cases) {
    		const numSpectra = Spectrogram.getNumSpectra(...args);
            expect(numSpectra).toBe(expected);
    	}

    });


    it('allocateSpectrogramStorage', () => {

        const inputLength = 10;
    	const params = { "window": [1, 1, 1, 1], "hopSize": 2, "dftSize": 8 }
    	const expected = 20;

    	const x = Spectrogram.allocateSpectrogramStorage(inputLength, params);
        expect(x.length).toBe(expected);

    });


    it('computeSpectrogram with rectangular window', () => {

        const x = createSpectrogramTestSignal();

    	const params = {
    		"window": DataWindow.createRectangularWindow(8),
    		"hopSize": 4,
    		"dftSize": 8,
    		"referencePower": null
    	};

        const y = Spectrogram.allocateSpectrogramStorage(x.length, params);

        Spectrogram.computeSpectrogram(x, params, y);

        expect(y.length).toBe(15);
        expect(y.slice(0, 5)).toAlmostEqual([0, 4, 0, 0, 0]);
        expect(y.slice(10, 15)).toAlmostEqual([0, 0, 4, 0, 0]);

    	// showSpectrogram(y, params.dftSize / 2 + 1);

    });


    it('computeSpectrogram with Hann window', () => {

        const x = createSpectrogramTestSignal();

    	const params = {
    		"window": DataWindow.createHannWindow(8),
    		"hopSize": 4,
    		"dftSize": 8,
    		"referencePower": null
    	};

        const y = Spectrogram.allocateSpectrogramStorage(x.length, params);

        Spectrogram.computeSpectrogram(x, params, y);

        expect(y.length).toBe(15);
        expect(y.slice(0, 5)).toAlmostEqual([.5, 1, .25, 0, 0]);
        expect(y.slice(10, 15)).toAlmostEqual([0, .25, 1, .25, 0]);

    	// showSpectrogram(y, params.dftSize / 2 + 1);

    });


    it('computeSpectrogram with Hann window and zero padding', () => {

        const x = createCosine(16, 4);

    	const params = {
    		"window": DataWindow.createHannWindow(8),
    		"hopSize": 4,
    		"dftSize": 16,
    		"referencePower": null
    	};

        const y = Spectrogram.allocateSpectrogramStorage(x.length, params);

        Spectrogram.computeSpectrogram(x, params, y);

        expect(y.length).toBe(27);

    	// We rely on manual inspection of the spectrogram values for this test.
    	// showSpectrogram(y, params.dftSize / 2 + 1);

    });


    it('computeDbValues', () => {

        const v = 17;
    	const cases = [
    	    [[0, 1, 10, 100, v], 4, 10, [-1000, -10, 0, 10, v]],
    	];

    	for (let [x, length, referencePower, expected] of cases) {
    		Spectrogram.computeDbValues(x, length, referencePower);
            expect(x).toAlmostEqual(expected);
    	}

    });


});


function createSpectrogramTestSignal() {
	const x1 = createCosine(8, 1);
	const x2 = createCosine(8, 2);
	const a = Array(...x1, ...x2);
	return new Float32Array(a);
}


function createCosine(length, freq) {

	const x = new Float32Array(length);
	const f = 2 * Math.PI * freq / length;

	for (let i = 0; i < length; i++)
		x[i] = Math.cos(f * i);

	return x;

}


function showSpectrogram(X, m) {
	for (let i = 0; i < X.length; i++) {
		console.log(X[i]);
		if (i % m === m - 1)
		    console.log("\n");
	}
}
