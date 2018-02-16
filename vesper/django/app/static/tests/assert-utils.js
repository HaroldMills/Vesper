function assert(x, message = '') {
	if (!x) {
		throw Error(message);
	}
}


function assertEqual(x, y, message = '') {
    // In this function, `x` and `y` can be of any type, numeric or not.
	if (_isArray(x) && _isArray(y))
		_assertArraysEqual(x, y, message);
	else
		assert(x == y);
}


const _ARRAY_TYPES = [
	Array, Float32Array, Float64Array, Int8Array, Int16Array, Int32Array,
	Uint8Array, Uint8ClampedArray, Uint16Array, Uint32Array
];


function _isArray(x) {
	for (const t of _ARRAY_TYPES)
	    if (x instanceof t)
		    return true;
	return false;
}


function _assertArraysEqual(a, b, message = '') {
    assert(a.length === b.length, message);
    for (let i = 0; i < a.length; i++)
	    assertEqual(a[i], b[i], message);
}


function assertAlmostEqual(x, y, message = '') {
    // This function assumes that `x` and `y` are either numbers
    // or (possibly nested) arrays of numbers.
    if (typeof x === 'number' && typeof y === 'number')
        _assertNumbersAlmostEqual(x, y, message);
    else
        _assertArraysAlmostEqual(x, y, message);
}


function _assertNumbersAlmostEqual(x, y, message = '', tolerance = 1e-7) {

    let diff = Math.abs(x - y);

    // When neither number is zero, we compare their relative difference
    // to the tolerance rather than their difference.
    if (x != 0 && y != 0)
        diff /= Math.max(Math.abs(x), Math.abs(y));

    assert(diff <= tolerance, message);

}


function _assertArraysAlmostEqual(x, y, message = '', tolerance = 1e-7) {
    assert(x.length === y.length);
    for (let i = 0; i < x.length; i++)
        assertAlmostEqual(x[i], y[i], message);
}
