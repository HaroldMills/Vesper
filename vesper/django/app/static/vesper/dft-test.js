/*
 * Test functions for dft.js.
 */


function testDft() {
	testRealFft();
	testRealFftSpeed();
	console.log("DFT tests complete");
}


function testRealFft() {
	for (let dftSize of [4, 8, 16]) {
		for (let freq = 0; freq < Math.floor(dftSize / 2) + 1; freq++) {
			testRealFftAux(dftSize, freq, "cosine");
			testRealFftAux(dftSize, freq, "sine");
		}
	}
	console.log("realFft tests passed")
}


const EPSILON = 1e-9;


function testRealFftAux(dftSize, freq, name) {
	
	const func = (name === "cosine" ? Math.cos : Math.sin);
	const x = createSinusoid(dftSize, freq, func);
	
	const X = new Float64Array(dftSize)
	
	realFft(x, X);
	// showFft(dftSize, freq, name, x, X);
	checkFft(X, x, dftSize, freq, name);
	
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
	checkOutput(X, expected, dftSize, freq, name);
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
		if (Math.abs(X[i] - expected[i]) > EPSILON)
			throw new Error(
				`Computed DFT element ${i} value differs from expected ` +
				`one: ${X[i]} ${expected[i]} ${dftSize} ${freq} ${name}`);
	}	
}


function testRealFftSpeed() {

	console.log("DFT sizes and times in microseconds:");
	
	for (let i = 5; i < 13; i++) {
		
		const numTrials = Math.round(100000 / i);
		
		const dftSize = Math.pow(2, i);
		
		const x = createSinusoid(dftSize, 1, Math.cos);
		const X = new Float64Array(dftSize);
		
		const startTime = Date.now();
	
		for (let j = 0; j < numTrials; j++)
		    realFft(x, X);
		
		const endTime = Date.now();
		
		const usPerDft = (endTime - startTime) / numTrials * 1000;
		
		console.log(dftSize, usPerDft);
		
	}
	
}
