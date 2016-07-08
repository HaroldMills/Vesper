"use strict";


/*
 * See comment near bottom of RFFT.forward in dsp.js for note about bug there
 * that the output of testRfft below demonstrates.
 */


function testRfft() {
	for (let dftSize of [4, 8]) {
		const rfft = new RFFT(dftSize, 1);
		for (let freq = 0; freq != Math.floor(dftSize / 2) + 1; ++freq) {
			testRfftAux(rfft, dftSize, freq, Math.cos, "cosine");
			testRfftAux(rfft, dftSize, freq, Math.sin, "sine");
		}
	}
}


function testRfftAux(rfft, dftSize, freq, func, name) {
	let x = createSinusoid(dftSize, freq, func);
	rfft.forward(x);
	const X = rfft.spectrum;
	showFft(dftSize, freq, name, X);
}


function createSinusoid(length, freq, func) {
	const x = new Float64Array(length);
	const f = 2 * Math.PI * freq / length;
	for (let i = 0; i != length; ++i) {
		x[i] = func(f * i);
	}
	return x;
}


function showFft(dftSize, freq, name, X) {
	console.log(`${dftSize} ${freq} ${name}`);
	for (let i = 0; i != X.length; ++i)
	    console.log(i, X[i]);
	console.log("\n");	
}


function testRfftSpeed() {

	console.log("DFT sizes and times in microseconds:");
	
	for (let i = 5; i != 13; ++i) {
		
		const numTrials = Math.round(100000 / i);
		
		const dftSize = Math.pow(2, i);
		const rfft = new RFFT(dftSize, 1);		
		const x = createSinusoid(dftSize);
	
		const startTime = Date.now();
	
		for (let j = 0; j != numTrials; ++j)
		    rfft.forward(x);
		
		const endTime = Date.now();
		
		const usPerDft = (endTime - startTime) / numTrials * 1000;
		
		console.log(dftSize, usPerDft);
		
	}
	
}
