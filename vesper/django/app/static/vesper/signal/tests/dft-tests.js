import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { Dft } from '/static/vesper/signal/dft.js';


describe('Dft', () => {


    it('realFft', () => {

	    const dftSizes = [1, 2, 4, 8, 16];

		for (const dftSize of dftSizes) {

			for (let freq = 0; freq < Math.floor(dftSize / 2) + 1; freq++) {

				expect(testRealFft(dftSize, freq, "cosine")).toBe(true);
				expect(testRealFft(dftSize, freq, "sine")).toBe(true);

			}

		}

	});


	it('_bitReverse', () => {

		const cases = [

            [1, [0]],
            [2, [0, 1]],
            [4, [0, 2, 1, 3]],
            [8, [0, 4, 2, 6, 1, 5, 3, 7]],
            [16, [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]]

        ]

        for (const [length, expected] of cases) {

            const input = new Float64Array(length);
            for (let i = 0; i < length; i++)
                input[i] = i;

            const output = new Float64Array(length);

            Dft._bitReverse(input, output);

            // console.log(output.length, output);

            expect(ArrayUtils.arraysEqual(output, expected)).toBe(true);

        }

	});


});


const EPSILON = 1e-9;


function testRealFft(dftSize, freq, name) {
	const func = (name === "cosine" ? Math.cos : Math.sin);
	const x = createSinusoid(dftSize, freq, func);
	const X = new Float64Array(dftSize)
	Dft.realFft(x, X);
	// showFft(dftSize, freq, name, x, X);
	return checkFft(X, x, dftSize, freq, name);
}


function createSinusoid(length, freq, func) {
	const x = new Float64Array(length);
	const f = 2 * Math.PI * freq / length;
	for (let i = 0; i < length; i++)
		x[i] = func(f * i);
	return x;
}


function showFft(dftSize, freq, name, x, X) {
	const xNorm = aNorm(x, dftSize);
	const XNorm = dftNorm(X, dftSize);
	console.log(`${dftSize} ${freq} ${name} ${xNorm} ${XNorm}`);
	for (let i = 0; i < X.length; i++)
	    console.log(i, X[i]);
	console.log("\n");
}


function aNorm(x, n) {
	let sum = 0;
	for (let i = 0; i < n; ++i)
		sum += x[i] * x[i];
	return Math.sqrt(sum);
}


function dftNorm(x, n) {
	let sum = x[0] * x[0] + x[n / 2] * x[n / 2];
	for (let i = 1; i < n / 2; i++) {
		const re = x[i];
		const im = x[n - i];
		sum += 2 * (re * re + im * im);
	}
	return Math.sqrt(sum);
}


function checkFft(X, x, dftSize, freq, name) {
	const expected = getExpectedOutput(x, dftSize, freq, name);
	return checkOutput(X, expected, dftSize, freq, name);
}


function getExpectedOutput(x, dftSize, freq, name) {

	const X = new Float64Array(dftSize);

	const norm = aNorm(x, dftSize);

	if (name === "cosine")

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


function checkOutput(X, expected, dftSize, freq, name) {
	for (let i = 0; i < dftSize; i++) {
		if (isNaN(X[i]) || Math.abs(X[i] - expected[i]) > EPSILON)
			throw new Error(
				`Computed DFT element ${i} value differs from expected ` +
				`one: ${X[i]} ${expected[i]} ${dftSize} ${freq} ${name}`);
	}
	return true;
}
