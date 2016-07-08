'use strict'


function testMultiselection() {
	testSelect();
	testExtend();
	testToggle();
	console.log('All tests passed.');
}


function testSelect() {
	console.log('Testing select...')
	_testCases([
	    ['select', [s(10), s(20), s(15)], [[[15, 15]], 15]]
	]);
}


function _testCases(cases) {
	for (let c of cases)
		_testCase(...c);
}


function _testCase(name, ops, expected) {
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
	
	_assertIntervals(s.selectedIntervals, intervals);
	
	assert(
		s.anchorIndex === anchorIndex,
		`Anchor index ${s.anchorIndex} is not expected ${anchorIndex}.`);
	
}


function _assertIntervals(intervals, expected) {
	assertArrayLengthsEqual(intervals, expected);
	for (let i = 0; i < intervals.length; i++)
		_assertInterval(intervals[i], expected[i]);
}


function _assertInterval(interval, expected) {
	const [i0, i1] = interval;
	const [e0, e1] = expected;
	assert(
	    i0 === e0 && i1 === e1,
	    `Interval [${i0}, ${i1}] differs from expected [${e0}, ${e1}].`);
}


function testExtend() {
    
	console.log('Testing extend...');
	
    self._testCases([
                      
        ['extend with no anchor', [e(15)], [[[10, 15]], 10]],
        
        ['extend after anchor', [s(15), e(18)], [[[15, 18]], 15]],
        
        ['extend before anchor', [s(15), e(12)], [[[12, 15]], 15]],
        
        ['extend after and then before anchor',
         [s(15), e(18), e(12)], [[[12, 15]], 15]]
                      
    ]);
    
}

    
function testToggle() {
    
	console.log('Testing toggle...');
	
    self._testCases([
                      
        ['single toggle', [t(15)], [[[15, 15]], 15]],
        
        ['double toggle', [t(15), t(15)], [[], null]],
        
        ['detoggle of first of two singletons',
         [t(14), t(16), t(14)], [[[16, 16]], 16]],
                      
        ['detoggle of second of two singletons',
         [t(14), t(16), t(16)], [[[14, 14]], 14]],
                      
        ['toggle at beginning of selected interval',
         [s(15), e(18), t(15)], [[[16, 18]], 16]],
                      
        ['toggle at end of selected interval',
         [s(15), e(18), t(18)], [[[15, 17]], 17]],
                      
        ['toggle inside selected interval',
         [s(15), e(18), t(16)], [[[15, 15], [17, 18]], 17]],
                      
        ['toggle just before selected interval',
         [s(15), e(18), t(14)], [[[14, 18]], 14]],
                      
        ['toggle just after selected interval',
         [s(15), e(18), t(19)], [[[15, 19]], 19]],
                      
        ['toggle and extend', [t(15), e(18)], [[[15, 18]], 15]],
        
        ['two-interval toggle and extend',
         [s(10), e(12), t(15), e(18)], [[[10, 12], [15, 18]], 15]],
                      
        ['extend after anchor resulting from toggle',
         [s(15), e(18), t(16), e(19)], [[[15, 15], [17, 19]], 17]],
                      
        ['extend before anchor resulting from toggle',
         [s(15), e(18), t(16), e(14)], [[[14, 17]], 17]],
                      
        ['extend across multiple selected intervals',
         [t(13), t(15), t(19), t(17), e(12)], [[[12, 17], [19, 19]], 17]],
                      
        ['another extend across multiple selected intervals',
         [s(11), e(12), t(14), e(15), t(20), t(17), e(10)],
         [[[10, 17], [20, 20]], 17]]
                      
    ]);
    
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
