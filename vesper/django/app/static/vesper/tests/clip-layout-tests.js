'use strict'


const settings = {
		
	page: {
		width: 10,       // seconds
		height: 2        // rows
	},
	
	clipView: {
		xSpacing: 10,    // percent of page width
		ySpacing: 10,    // percent of page width
	}
	
}


describe('NonuniformResizingClipViewsLayout', () => {
	
	
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
		
		for (let [durations, expectedPages] of cases) {
					
			const clipViews = durations.map(d => ({duration: d}));
			const layout = new NonuniformResizingClipViewsLayout(
				null, clipViews, settings);

			expect(layout.div).toBe(null);
			expect(layout.clipViews).toEqual(clipViews);
			expect(layout.settings).toEqual(settings);
			
			expect(layout.numPages).toBe(expectedPages.length);
			
			// page index bounds and row start indices
			for (let i = 0; i < layout.numPages; i++) {
				
				const expectedPage = expectedPages[i];
				const numRows = expectedPage.length - 1;
				
				const bounds = layout.getPageIndexBounds(i);
				const expectedBounds = [expectedPage[0], expectedPage[numRows]];
				expect(bounds).toEqual(expectedBounds);
				
				expect(layout._pages[i]).toEqual(expectedPage);
				
			}
			
		}
			
	});
	
	
});
