function expectArraysAlmostEqual(x, y, tolerance = 1e-7) {

    expect(x.length).toBe(y.length);

    for (let i = 0; i < x.length; i++) {
        expectNumbersAlmostEqual(x[i], y[i], tolerance);
    }

}


function expectNumbersAlmostEqual(x, y, tolerance = 1e-7) {

    let diff = Math.abs(x - y);

    // When neither number is zero, we compare their relative difference
    // to the tolerance rather than their difference.
    if (x != 0 && y != 0)
        diff /= Math.max(Math.abs(x), Math.abs(y));

    expect(diff).toBeLessThanOrEqual(tolerance);

}


export const TestUtils = {
    'expectArraysAlmostEqual': expectArraysAlmostEqual,
    'expectNumbersAlmostEqual': expectNumbersAlmostEqual
}
