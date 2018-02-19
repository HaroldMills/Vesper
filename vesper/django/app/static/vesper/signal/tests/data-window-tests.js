import { DataWindow } from '/static/vesper/signal/data-window.js';


describe('DataWindow', () => {


    beforeEach(() => addAlmostEqualMatcher());


    it('createRectangularWindow', () => {

        function ones(n) {
            const result = new Float64Array(n);
            for (let i = 0; i < n; i++)
                result[i] = 1;
            return result;
        }

        for (let size = 0; size < 5; size++) {

            const expected = ones(size);

            // default `symmetric` argument
            let window = DataWindow.createRectangularWindow(size);
            expect(window).toEqual(expected);

            // `symmetric` argument `true`
            window = DataWindow.createRectangularWindow(size, true);
            expect(window).toEqual(expected);

            // `symmetric` argument `false`
            window = DataWindow.createRectangularWindow(size, false);
            expect(window).toEqual(expected);

        }

	});


    it('createHannWindow', () => {

        const cases = [
            [],
            [0],
            [0, 0],
    	    [0, 1, 0],
    	    [0, .75, .75, 0],
    	    [0, .5, 1, .5, 0]
    	];

        for (let size = 0; size < cases.length; size++) {

            // default `symmetric` argument
            let window = DataWindow.createHannWindow(size);
            expect(window).toAlmostEqual(cases[size]);

            // `symmetric` argument `true`
            window = DataWindow.createHannWindow(size, true);
            expect(window).toAlmostEqual(cases[size]);

            // `symmetric` argument `false`
            if (size < cases.length - 1) {
                window = DataWindow.createHannWindow(size, false);
                const expected = cases[size + 1].slice(0, size);
                expect(window).toAlmostEqual(expected);
            }

        }

	});


    it('createWindow', () => {

        const cases = [

    	    [['Rectangular', 0], []],
    	    [['Rectangular', 1], [1]],
    	    [['Rectangular', 2], [1, 1]],
    	    [['Rectangular', 3], [1, 1, 1]],
            [['Rectangular', 4], [1, 1, 1, 1]],
            [['Rectangular', 5], [1, 1, 1, 1, 1]],

            [['Hann', 0], []],
            [['Hann', 1], [0]],
            [['Hann', 2], [0, 0]],
    	    [['Hann', 3], [0, 1, 0]],
    	    [['Hann', 4], [0, .75, .75, 0]],
    	    [['Hann', 5], [0, .5, 1, .5, 0]]

    	];

    	for (const [args, expected] of cases) {
    		const window = DataWindow.createWindow(...args);
            expect(window).toAlmostEqual(expected);
    	}

    });


});
