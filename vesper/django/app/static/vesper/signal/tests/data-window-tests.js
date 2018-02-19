import { DataWindow } from '/static/vesper/signal/data-window.js';


const _TEST_CASES = new Map([

    ['Rectangular', [DataWindow.createRectangularWindow, [
        [],
        [1],
        [1, 1],
        [1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1, 1]
    ]]],

    ['Hann', [DataWindow.createHannWindow, [
        [],
        [0],
        [0, 0],
        [0, 1, 0],
        [0, .75, .75, 0],
        [0, .5, 1, .5, 0]
    ]]]

]);


function _testWindow(name) {
    const [windowFunction, expectedWindows] = _TEST_CASES.get(name);
    _testWindowFunction(windowFunction, expectedWindows);
}


function _testWindowFunction(windowFunction, expectedWindows) {

    for (const expectedWindow of expectedWindows) {

        const size = expectedWindow.length;

        // default `symmetric` argument (`true`)
        let window = windowFunction(size);
        expect(window).toAlmostEqual(expectedWindow);

        // `symmetric` argument `true`
        window = windowFunction(size, true);
        expect(window).toAlmostEqual(expectedWindow);

        // `symmetric` argument `false`
        if (size !== 0) {
            window = windowFunction(size - 1, false);
            expect(window).toAlmostEqual(expectedWindow.slice(0, size - 1));
        }

    }

}


function _createWindowFunction(name) {
    return function(size, symmetric = true) {
        return DataWindow.createWindow(name, size, symmetric);
    }
}


describe('DataWindow', () => {

    beforeEach(() => addAlmostEqualMatcher());

    for (const windowName of _TEST_CASES.keys()) {
        it(`create${windowName}Window`, () => {
            _testWindow(windowName);
        })
    }

    it('createWindow', () => {
        for (const [name, [_, expectedWindows]] of _TEST_CASES) {
            const windowFunction = _createWindowFunction(name);
            _testWindowFunction(windowFunction, expectedWindows);
        }
    });

});
