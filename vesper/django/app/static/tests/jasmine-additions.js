/*
 * Adds a near-equality matcher to Jasmine.
 *
 * The near-equality matcher compares two numbers or two numeric arrays
 * (possibly nested) for near-equality. It is invoked like:
 *
 *     expect(x).toAlmostEqual(y);
 *
 * If either of two numbers is zero, they are considered nearly equal
 * if the magnitude of their difference is at most 1e-7. Otherwise,
 * they are considered nearly equal if their relative difference
 * (abs(x - y) / max(abs(x), abs(y))) is at most 1e-7.
 *
 * Note that this file uses the `assertAlmostEqual` function defined in
 * assert-utils.js.
 */
function addAlmostEqualMatcher() {

    jasmine.addMatchers({
        toAlmostEqual: function(util, customEqualityTesters) {
            return {
                compare: function(actual, expected) {
                    const result = {
                        pass: _almostEqual(actual, expected)
                    }
                    if (!result.pass) {
                        // TODO: Implement a reasonable string representation
                        // of arrays, including nested arrays, and use it here.
                        // JavaScript's representation seems lacking. For
                        // example, JavaScript represents [] as "", [0] as "0",
                        // and [[1, 2], [3, 4]] as "1,2,3,4".
                        result.message =
                            `Expected ${actual} to almost equal ${expected}.`;
                    }
                    return result;
                }
            }
        }
    });

}


function _almostEqual(x, y) {
    try {
        assertAlmostEqual(x, y);
    } catch (e) {
        return false;
    }
    return true;
}


function _toString(x) {


}
