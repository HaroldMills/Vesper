import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { Dft } from '/static/vesper/signal/dft.js';


describe('Dft', () => {


    beforeEach(() => addAlmostEqualMatcher());


    it('computeRealForwardDft', () => {

	    const dftSizes = [1, 2, 4, 8, 16];

		for (const dftSize of dftSizes) {

			for (let freq = 0; freq < Math.floor(dftSize / 2) + 1; freq++) {

                testSinusoidDft(dftSize, freq, 'cosine');
                testSinusoidDft(dftSize, freq, 'sine');

			}

		}

	});


	it('bitReverseArrayElements', () => {

		const cases = [

            [1, [0]],
            [2, [0, 1]],
            [4, [0, 2, 1, 3]],
            [8, [0, 4, 2, 6, 1, 5, 3, 7]],
            [16, [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]]

        ]

        for (let [length, expected] of cases) {

            expected = new Float64Array(expected);

            const input = new Float64Array(length);
            for (let i = 0; i < length; i++)
                input[i] = i;

            const output = new Float64Array(length);

            Dft.bitReverseArrayElements(input, output);

            // console.log(output.length, output);

            expect(output).toEqual(expected);

        }

	});


});


function testSinusoidDft(dftSize, freq, funcName) {
    const x = createSinusoid(dftSize, freq, funcName);
    const X = new Float64Array(dftSize);
    Dft.computeRealForwardDft(x, X);
    // showDft(dftSize, freq, funcName, x, X);
    expect(arrayNorm(x)).toAlmostEqual(realDftNorm(X));
    const expected = getExpectedSinusoidDft(x, dftSize, freq, funcName);
    expect(X).toAlmostEqual(expected);
}


function createSinusoid(length, freq, funcName) {
    const func = (funcName === 'cosine' ? Math.cos : Math.sin);
	const x = new Float64Array(length);
	const f = 2 * Math.PI * freq / length;
	for (let i = 0; i < length; i++)
		x[i] = func(f * i);
	return x;
}


function showDft(dftSize, freq, funcName, x, X) {
	const xNorm = arrayNorm(x);
	const XNorm = realDftNorm(X);
	console.log(
        `${dftSize} ${freq} ${funcName} ${xNorm} ${XNorm}`);
	for (let i = 0; i < X.length; i++)
	    console.log(i, X[i]);
	console.log("\n");
}


function arrayNorm(x) {
    const n = x.length;
	let sum = 0;
	for (let i = 0; i < n; ++i)
		sum += x[i] * x[i];
	return Math.sqrt(sum);
}


function realDftNorm(x) {

    const n = x.length;
	let sum = x[0] * x[0];

    if (n > 1) {

    	for (let i = 1; i < n / 2; i++) {
    		const re = x[i];
    		const im = x[n - i];
    		sum += 2 * (re * re + im * im);
    	}

        sum += x[n / 2] * x[n / 2];

    }

	return Math.sqrt(sum);

}


function getExpectedSinusoidDft(x, dftSize, freq, funcName) {

	const X = new Float64Array(dftSize);

	const norm = arrayNorm(x);

	if (funcName === 'cosine')

		if (freq === 0 || freq === dftSize / 2)
		    X[freq] = norm;
		else
			X[freq] = norm / Math.sqrt(2);

	else
		// input is sine

		if (freq === 0 || freq === dftSize / 2)
			X[freq] = 0;
		else
			X[dftSize - freq] = -norm / Math.sqrt(2);

	return X;

}
