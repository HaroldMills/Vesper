/*
 * Test functions for dft.js.
 */


import { Dft } from '../dft.js';


function testRealFftSpeed() {

	console.log("DFT sizes and times in microseconds:");

	for (let i = 5; i < 13; i++) {

		const numTrials = Math.round(100000 / i);

		const dftSize = Math.pow(2, i);

		const x = createSinusoid(dftSize, 1, Math.cos);
		const X = new Float64Array(dftSize);

		const startTime = Date.now();

		for (let j = 0; j < numTrials; j++)
		    Dft.realFft(x, X);

		const endTime = Date.now();

		const usPerDft = (endTime - startTime) / numTrials * 1000;

		console.log(dftSize, usPerDft);

	}

}


function createSinusoid(length, freq, func) {
	const x = new Float64Array(length);
	const f = 2 * Math.PI * freq / length;
	for (let i = 0; i < length; i++)
		x[i] = func(f * i);
	return x;
}


window.onload = testRealFftSpeed;
