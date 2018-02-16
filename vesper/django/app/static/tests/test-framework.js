/*
 * Simple unit test framework for Vesper JavaScript code.
 *
 * The framework runs tests expressed with a subset of the syntax supported
 * by Jasmine. Unlike with Jasmine, the tests are run serially, in a
 * repeatable order.
 *
 * Note that this file uses assertion functions defined in assert-utils.js.
 */


function describe(name, f) {
	console.log(`${name}`);
	f();
}


// Some of our Jasmine tests use `beforeEach` to add a custom matcher.
// We don't need to do that when using our test framework, so our
// `beforeEach` function does nothing.
function beforeEach(f) { }


function it(name, f) {
	console.log(`    ${name}`);
	try {
	    f();
	} catch (e) {
		console.log('        >>>>>>>>>> FAILED <<<<<<<<<<');
		console.log('        Message was:');
		console.log(`            ${e.message}`);
		return;
	}
}


class _Expect {


	constructor(x) {
		this.x = x;
	}


    toBe(y) {
		assert(this.x === y, `${this.x} is not ${y}.`);
	}


	toEqual(y) {
        assertEqual(this.x, y, `${this.x} does not equal ${y}.`);
	}


	toAlmostEqual(y) {
		assertAlmostEqual(this.x, y, `${this.x} does not almost equal ${y}.`);
	}


	toBeLessThanOrEqual(y) {
		assert(this.x <= y, `${this.x} is not less than or equal to ${y}.`);
	}


	toThrowError() {

		try {
			this.x()
		} catch (e) {
            return;
		}

		assert(false, 'Function did not throw expected error.');

	}


}


function expect(x) {
	return new _Expect(x);
}
