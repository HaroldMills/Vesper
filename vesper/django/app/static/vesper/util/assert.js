"use strict"


function assert(v, message = null) {
	
	if (!v) {
		
		if (message === null)
			message = "Assertion failed.";
		
		throw new Error(message);
		
	}
	
}


function assertArraysEqual(a, b) {
	
	assertArrayLengthsEqual(a, b);
	
	for (let i = 0; i < a.length; i++)
		assert(
			a[i] === b[i],
			`Array elements differ at index ${i}.`);

}


function assertArrayLengthsEqual(...arrays) {
	
	if (arrays.length < 2)
		return true;
		
	const n = arrays[0].length;
	
	for (let a of arrays.slice(1))
		assert(
			a.length === n,
			`Array lengths $(n) and $(a.length) differ.`);

}


function assertArraysAlmostEqual(a, b, tolerance = null) {
	
	assertArrayLengthsEqual(a, b);

    for (let i = 0; i < a.length; i++)
    	assert(
    	    numbersAlmostEqual(a[i], b[i], tolerance),
    	    `Array elements differ at index ${i}.`);
	
}


function numbersAlmostEqual(a, b, tolerance = null) {
	if (tolerance === null)
		tolerance = 1e-6;
	return Math.abs(a - b) <= tolerance;
}


function assertNumbersAlmostEqual(a, b, tolerance = null) {
	assert(
		numbersAlmostEqual(a, b, tolerance),
		`Numbers ${a} and ${b} are not almost equal.`);
}
