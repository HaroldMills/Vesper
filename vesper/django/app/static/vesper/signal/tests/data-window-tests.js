import { DataWindow } from '/static/vesper/signal/data-window.js';


describe('DataWindow', () => {


    beforeEach(() => addAlmostEqualMatcher());


    it('createRectangularWindow', () => {

        const cases = [
    	    [0, []],
    	    [1, [1]],
    	    [2, [1, 1]],
    	    [3, [1, 1, 1]]
    	];

    	for (let [size, expected] of cases) {
    		const window = DataWindow.createRectangularWindow(size);
            expect(window).toAlmostEqual(expected);
    	}

	});


    it('createHannWindow', () => {

        const cases = [
    	    [2, [0, 1]],
    	    [3, [0, .75, .75]],
    	    [4, [0, .5, 1, .5]]
    	];

    	for (const [size, expected] of cases) {
    		const window = DataWindow.createHannWindow(size);
            expect(window).toAlmostEqual(expected);
    	}

	});


    it('createWindow', () => {

        const cases = [

    	    [['Rectangular', 0], []],
    	    [['Rectangular', 1], [1]],
    	    [['Rectangular', 2], [1, 1]],
    	    [['Rectangular', 3], [1, 1, 1]],

    	    [['Hann', 2], [0, 1]],
    	    [['Hann', 3], [0, .75, .75]],
    	    [['Hann', 4], [0, .5, 1, .5]]

    	];

    	for (const [args, expected] of cases) {
    		const window = DataWindow.createWindow(...args);
            expect(window).toAlmostEqual(expected);
    	}

    });


});
