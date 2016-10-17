/**
 * the display width in seconds.
 */
const displayWidth = 10;

/**
 * the display height in rows.
 */
const displayHeight = 2;

/**
 * the clip spacing as percent of display width.
 */
const clipSpacing = 10;


describe('ResizingVariableWidthClipLayout', () => {
	
	
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
		
		for (let [spans, expectedPages] of cases) {
					
			const clips = spans.map(_ => ({span: _}))
			
			layout = new ResizingVariableWidthClipLayout(
			    clips, displayWidth, displayHeight, clipSpacing);
				
			expect(layout.clips).toEqual(clips);
			expect(layout.displayWidth).toBe(displayWidth);
			expect(layout.displayHeight).toBe(displayHeight);
			expect(layout.clipSpacing).toBe(clipSpacing);
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
