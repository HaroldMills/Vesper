'use strict'


const NONRESIZING_SETTINGS = {
	
	page: {
		size: 2             // clips
	},
	
};


const RESIZING_SETTINGS = {
		
	page: {
		width: 10,          // seconds
		height: 2           // rows
	},
	
	clipView: {
		xSpacing: 10,       // percent of page width
		ySpacing: 10,       // percent of page width
	}
	
};


describe('_findLastLE', () => {
	
	
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
			const actual = _findLastLE(xs, x);
			expect(actual).toBe(expected);
		}
		
	});
	
	
});


describe('_NonuniformNonresizingClipViewsLayout', () => {
	
	
	it('getClipPageNum', () => {

		const cases = [
		    [],
		    [1],
		    [1, 2],
		    [1, 2, 3],
		    [1, 2, 3, 4, 5]
		];
		
		_testGetClipPageNum(cases, _NonuniformNonresizingClipViewsLayout);
		
	});
	
	
	it('construction and layout', () => {
		
		const cases = [
		               
		    // no clips or pages
		    [[], []],
		    
		    // one clip
		    [[1], [0, 1]],
		    
		    // two clips
		    [[1, 2], [0, 2]],
		    
		    // three clips
		    [[1, 2, 3], [0, 2, 3]],
		    
		    // several clips
		    [[1, 2, 3, 4, 5], [0, 2, 4, 5]]
		    
		];
		
		for (const [durations, expectedPageStartClipNums] of cases) {
			
			const clipViews = _createClipViews(durations)
			const layout = new _NonuniformNonresizingClipViewsLayout(
				null, clipViews, NONRESIZING_SETTINGS);
			
			expect(layout.div).toBe(null);
			expect(layout.clipViews).toEqual(clipViews);
			expect(layout.settings).toEqual(NONRESIZING_SETTINGS);
			
			const numStartClipNums = expectedPageStartClipNums.length;
			const numPages = numStartClipNums === 0 ? 0 : numStartClipNums - 1
			expect(layout.numPages).toBe(numPages);

			// page clip num range
			const clipNums = expectedPageStartClipNums;
			for (let i = 0; i < layout.numPages; i++) {
				const range = layout.getPageClipNumRange(i);
				const expectedRange = [clipNums[i], clipNums[i + 1]];
				expect(range).toEqual(expectedRange);
			}
			
		}
		
	});
	
	
});


function _testGetClipPageNum(cases, layoutClass) {
	
	for (const durations of cases) {
		
		const clipViews = _createClipViews(durations);
		const layout = new _NonuniformNonresizingClipViewsLayout(
			null, clipViews, NONRESIZING_SETTINGS);
		
		for (let i = 0; i < layout.numPages; i++) {
			
			const [startNum, endNum] = layout.getPageClipNumRange(i);
			
			if (startNum > 0)
			    expect(layout.getClipPageNum(startNum - 1)).toBe(i - 1);
			
			for (let j = startNum; j < endNum; j++) {
				expect(layout.getClipPageNum(j)).toBe(i);
			}
			
			if (endNum < clipViews.length)
			    expect(layout.getClipPageNum(endNum)).toBe(i + 1);
			
		}
		
	}
	
}


function _createClipViews(durations) {
	const entries = Array.from(durations.entries());
	return entries.map(_createClipView);
}


function _createClipView([clipNum, duration]) {
	return {
		'duration': duration,
		'clip': {
			'startTime': _createClipStartTime(clipNum)
		}
	}
}


function _createClipStartTime(clipNum) {
	const num = clipNum.toString();
	const prefix = num.length == 1 ? '0' : '';
	const minutes = prefix + num;
	return `2016-11-10 09:${minutes}:00 MDT`;
}


describe('_NonuniformResizingClipViewsLayout', () => {
	
	
	it('getClipPageNum', () => {

		const cases = [
		    
		    // no pages
		    [],
		    
		    // one page
		    [1],
		    [1, 2],
		    [1, 2, 3],
		    [1, 2, 3, 4],
		    
		    // two pages
		    [1, 2, 3, 4, 3, 1, 2, 3, 4],
		    
		    // four pages
		    [1, 2, 3, 4, 5, 2, 15, 20, 2, 3, 8]
		     
		];
		
		_testGetClipPageNum(cases, _NonuniformResizingClipViewsLayout);
		
	});

	
	it('construction and layout', () => {
		
		const cases = [
		               
		    // no clips or pages
		    [[], []],
		    
		    // one clip
		    [[1], [[0, 1]]],
		    
		    // one row of clips on one page
		    [[1, 2, 3], [[0, 3]]],
		    
		    // two rows of clips on one page
		    [[1, 2, 3, 4], [[0, 3, 4]]],
		    
		    // two pages
		    [[1, 2, 3, 4, 3, 1, 2, 3, 4], [[0, 3, 5], [5, 8, 9]]],
		    
		    // four pages, including clips longer than display width
		    [[1, 2, 3, 4, 5, 2, 15, 20, 2, 3, 8],
		     [[0, 3, 4], [4, 6, 7], [7, 8, 10], [10, 11]]]
		    
		];
		
		for (const [durations, expectedPages] of cases) {
					
			const clipViews = durations.map(d => ({duration: d}));
			const layout = new _NonuniformResizingClipViewsLayout(
				null, clipViews, RESIZING_SETTINGS);

			expect(layout.div).toBe(null);
			expect(layout.clipViews).toEqual(clipViews);
			expect(layout.settings).toEqual(RESIZING_SETTINGS);
			expect(layout.numPages).toBe(expectedPages.length);
			
			// page clip num range and row start clip nums
			for (let i = 0; i < layout.numPages; i++) {
				
				const expectedPage = expectedPages[i];
				const numRows = expectedPage.length - 1;
				
				const range = layout.getPageClipNumRange(i);
				const expectedRange = [expectedPage[0], expectedPage[numRows]];
				expect(range).toEqual(expectedRange);
				
				expect(layout._pages[i]).toEqual(expectedPage);
				
			}
			
		}
			
	});
	
	
});
