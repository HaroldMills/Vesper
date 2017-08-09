'use strict'


describe('Multiselection class', () => {
	
	
	it('constructor', () => {
		
		const s = new Multiselection(10, 20);
		expect(s.minIndex).toBe(10);
		expect(s.maxIndex).toBe(20);
		expect(s.anchorIndex).toBe(null);
		expect(s.selectedIntervals).toEqual([]);
		expect(s.selectedIndices).toEqual([]);
		expect(s.size).toBe(0);
		
	})
	
	
	it('select', () => {
		
		_testCases([
			[[s(10), s(20), s(15)], [[[15, 15]], 15]]
		]);
		
	})
	
	
	it('extend', () => {
		
	    _testCases([
            
	    	// extend with no anchor
	        [[e(15)], [[[10, 15]], 10]],
	        
	        // extend to after anchor
	        [ [s(15), e(18)], [[[15, 18]], 15]],
	        
	        // extend to before anchor
	        [[s(15), e(12)], [[[12, 15]], 15]],
	        
	        // extend to after and then to before anchor
	        [[s(15), e(18), e(12)], [[[12, 15]], 15]]
	                      
	    ]);

	})
	
	
	it('toggle', () => {
		
		_testCases([
			
			// single toggle
	        [[t(15)], [[[15, 15]], 15]],
	        
	        // double toggle
	        [[t(15), t(15)], [[], null]],
	        
	        // detoggle of first of two singletons
	        [[t(14), t(16), t(14)], [[[16, 16]], 16]],
	             
	        // detoggle of second of two singletons
	        [[t(14), t(16), t(16)], [[[14, 14]], 14]],
	             
	        // toggle at beginning of selected interval
	        [[s(15), e(18), t(15)], [[[16, 18]], 16]],
	            
	        // toggle at end of selected interval
	        [[s(15), e(18), t(18)], [[[15, 17]], 17]],
	             
	        // toggle inside selected interval
	        [[s(15), e(18), t(16)], [[[15, 15], [17, 18]], 17]],
	                
	        // toggle just before selected interval
	        [[s(15), e(18), t(14)], [[[14, 18]], 14]],
	                 
	        // toggle just after selected interval
	        [[s(15), e(18), t(19)], [[[15, 19]], 19]],
	                
	        // toggle and extend
	        [[t(15), e(18)], [[[15, 18]], 15]],
	        
	        // two-interval toggle and extend
	        [[s(10), e(12), t(15), e(18)], [[[10, 12], [15, 18]], 15]],
	               
	        // extend to after anchor resulting from toggle
	        [[s(15), e(18), t(16), e(19)], [[[15, 15], [17, 19]], 17]],
	                      
	        // extend to before anchor resulting from toggle
	        [[s(15), e(18), t(16), e(14)], [[[14, 17]], 17]],
	                 
	        // extend across multiple selected intervals
	        [[t(13), t(15), t(19), t(17), e(12)], [[[12, 17], [19, 19]], 17]],
	                
	        // another extend across multiple selected intervals
	        [[s(11), e(12), t(14), e(15), t(20), t(17), e(10)],
	         [[[10, 17], [20, 20]], 17]]

	    ]);
		
	})
	
	
	it('selectedIndices', () => {
		
		const cases = [
			[[s(13), e(14), t(16), e(18), t(20)],
			 [[13, 14, 16, 17, 18, 20], 20]]
		];
		
		for (const [ops, [selectedIndices, anchorIndex]] of cases) {
			const s = new Multiselection(10, 20);
			ops.forEach(_performOp, s);
			expect(s.selectedIndices).toEqual(selectedIndices);
			expect(s.anchorIndex).toBe(anchorIndex)
			
		}
		
	})
	
	
})


function _testCases(cases) {
	for (const c of cases)
		_testCase(...c);
}


function _testCase(ops, expected) {
	const s = new Multiselection(10, 20);
	ops.forEach(_performOp, s);
	_assertSelection(s, expected);
}


function _performOp(op) {
	
	const [methodName, index] = op;
	
	switch (methodName) {
	
	case 'select':
		this.select(index);
		break;
		
	case 'extend':
		this.extend(index);
		break;
		
	case 'toggle':
		this.toggle(index);
		break;
		
	default:
		console.log(`Unrecognized Multiselection method name "${methodName}".`);
	
	}
		
}


function _assertSelection(s, expected) {
	const [intervals, anchorIndex] = expected;
	expect(s.selectedIntervals).toEqual(intervals);
	expect(s.anchorIndex).toBe(anchorIndex)
}


function s(i) {
    return ['select', i];
}


function e(i) {
    return ['extend', i];
}


function t(i) {
    return ['toggle', i];
}
