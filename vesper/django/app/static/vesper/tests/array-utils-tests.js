'use strict'


describe('findLastLE', () => {
	
	
	it('invocation', () => {
		
		const cases = [
		               
		    // one x
		    [[0], -2, -1],
		    [[0], -.1, -1],
		    [[0], 0, 0],
		    [[0], 1, 0],
		    
		    // two x's
		    [[0, 1], -2, -1],
		    [[0, 1], -.1, -1],
		    [[0, 1], 0, 0],
		    [[0, 1], .5, 0],
		    [[0, 1], 1, 1],
		    [[0, 1], 2, 1],
		    
		    // several x's
		    [[0, 1, 2, 3], -2, -1],
		    [[0, 1, 2, 3], -.1, -1],
		    [[0, 1, 2, 3], 0, 0],
		    [[0, 1, 2, 3], .5, 0],
		    [[0, 1, 2, 3], 1, 1],
		    [[0, 1, 2, 3], 2.5, 2],
		    [[0, 1, 2, 3], 3, 3],
		    [[0, 1, 2, 3], 4, 3]
		               
		];
		
		for (let [xs, x, expected] of cases) {
			const actual = findLastLE(xs, x);
			expect(actual).toBe(expected);
		}
		
	});
	
	
});
