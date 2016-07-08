"use strict"


/*
 * TODO: Use Python to create spectrogram test cases for a chirp signal,
 * including cases with various windows, overlap, zero padding, and both
 * linear and logarithmic output.
 */


function testSpectrogram() {
	testCreateRectangularWindow();
	testCreateHannWindow();
	testCreateDataWindow();
	testGetNumInputBlocks();
	testAllocateSpectrogramStorage();
	testRectangularWindowSpectrogram();
	testHannWindowSpectrogram();
	testSpectrogramZeroPadding();
	testComputeDbValues();
	console.log("All tests passed.");
}


function testCreateRectangularWindow() {
	
	const cases = [
	    [0, []],
	    [1, [1]],
	    [2, [1, 1]],
	    [3, [1, 1, 1]]
	];
	
	for (let [size, expected] of cases) {
		const window = createRectangularWindow(size);
		assertArraysEqual(window, expected);
	}
	
	console.log("testCreateRectangularWindow passed...");
	
}


function testCreateHannWindow() {
	
	const cases = [
	    [2, [0, 1]],
	    [3, [0, .75, .75]],
	    [4, [0, .5, 1, .5]]
	];
	
	for (let [size, expected] of cases) {
		const window = createHannWindow(size);
		assertArraysAlmostEqual(window, expected);
	}
	
	console.log("testCreateHannWindow passed...");
	
}


function testCreateDataWindow() {
	
	const cases = [
	               
	    [["Rectangular", 0], []],
	    [["Rectangular", 1], [1]],
	    [["Rectangular", 2], [1, 1]],
	    [["Rectangular", 3], [1, 1, 1]],
	       	    
	    [["Hann", 2], [0, 1]],
	    [["Hann", 3], [0, .75, .75]],
	    [["Hann", 4], [0, .5, 1, .5]]
	       	    
	];
	
	for (let [args, expected] of cases) {
		const window = createDataWindow(...args);
		assertArraysAlmostEqual(window, expected);
	}
	
	console.log("testCreateDataWindow passed...")
	
}


function testGetNumInputBlocks() {
	
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
	
	for (let [args, expected] of cases) {
		const numBlocks = _getNumInputBlocks(...args);
		assert(
			numBlocks === expected,
			`Number of input blocks ${numBlocks} differs from ` +
			    `expected ${expected}.`);
	}
	
	console.log("testGetNumInputBlocks passed...");
	
}


function testAllocateSpectrogramStorage() {
	
	const inputLength = 10;
	const params = { "window": [1, 1, 1, 1], "hopSize": 2, "dftSize": 8 }
	const expected = 20;
	
	const X = allocateSpectrogramStorage(inputLength, params);
	assert(
		X.length === expected,
		`Allocated array length ${X.length} differs from expected ` +
		    `${expected}.`);
	
	console.log("testAllocateSpectrogramStorage passed...");
	
}


function testRectangularWindowSpectrogram() {
	
	const x = createSpectrogramTestSignal();
	
	const params = {
		"window": createRectangularWindow(8),
		"hopSize": 4,
		"dftSize": 8,
		"referencePower": null
	};
		
    const X = allocateSpectrogramStorage(x.length, params);
    
    computeSpectrogram(x, params, X);
    
	assert(X.length === 15);
	assertArraysAlmostEqual(X.slice(0, 5), [0, 4, 0, 0, 0]);
	assertArraysAlmostEqual(X.slice(10, 15), [0, 0, 4, 0, 0]);
	
	// showSpectrogram(X, params.dftSize / 2 + 1);
	
	console.log("testRectangularWindowSpectrogram passed...");
		
}


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


function testHannWindowSpectrogram() {
	
	const x = createSpectrogramTestSignal();
	
	const params = {
		"window": createHannWindow(8),
		"hopSize": 4,
		"dftSize": 8,
		"referencePower": null
	};
		
    const X = allocateSpectrogramStorage(x.length, params);
    
    computeSpectrogram(x, params, X);
    
	assert(X.length === 15);
	assertArraysAlmostEqual(X.slice(0, 5), [.5, 1, .25, 0, 0]);
	assertArraysAlmostEqual(X.slice(10, 15), [0, .25, 1, .25, 0]);
	
	// showSpectrogram(X, params.dftSize / 2 + 1);
	
	console.log("testHannWindowSpectrogram passed...");
		
}


function testSpectrogramZeroPadding() {
	
	const x = createCosine(16, 4);
	
	const params = {
		"window": createHannWindow(8),
		"hopSize": 4,
		"dftSize": 16,
		"referencePower": null
	};
		
    const X = allocateSpectrogramStorage(x.length, params);
    
    computeSpectrogram(x, params, X);
    
	assert(X.length === 27);
	
	// We rely on manual inspection of the spectrogram for this test.
	showSpectrogram(X, params.dftSize / 2 + 1);
	
	console.log("testSpectrogramZeroPadding passed...");
		
}


function createOnes() {
	const x = new Float64Array(16);
	for (let i = 0; i < 16; i++)
		x[i] = 1;
	return x;
}


function testComputeDbValues() {
	
	const v = 17;
	const cases = [
	    [[0, 1, 10, 100, v], 4, 10, [-1000, -10, 0, 10, v]],
	];
	
	for (let [X, length, referencePower, expected] of cases) {
		_computeDbValues(X, length, referencePower);
		assertArraysEqual(X, expected);
	}
	
	console.log("testComputeDbValues passed...");
	
}


function testDftScaling() {
	
	for (let n of [4]) {
		
		const freqs = [0, 1, 2];
		
		const sinusoids = freqs.map(f => createCosine(n, f));
		
		const dft = new Dft(n);
		const dfts = sinusoids.map(s => dft.forward(s));
		
		for (let i = 0; i < sinusoids.length; i++)
			showTransformData(n, i, sinusoids[i], dfts[i]);
		
	}
	
}
