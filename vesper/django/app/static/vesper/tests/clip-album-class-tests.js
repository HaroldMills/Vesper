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
			
			// num pages
			const numStartClipNums = expectedPageStartClipNums.length;
			const numPages = numStartClipNums === 0 ? 0 : numStartClipNums - 1
			expect(layout.numPages).toBe(numPages);
			
			// page start clip nums
			expect(layout.pageStartClipNums).toEqual(expectedPageStartClipNums);

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


describe('_Clip', () => {
	
	
	it('construction and properties', () => {

		const num = 23;
		const id = 24;
		const length = 1000;
		const sampleRate = 22050.;
		const startTime = "2017-05-18 10:19:00 EDT";
		const clip = new _Clip(num, id, length, sampleRate, startTime);
		
		expect(clip.num).toBe(num);
		expect(clip.id).toBe(id);
		expect(clip.length).toBe(length);
		expect(clip.sampleRate).toBe(sampleRate);
		expect(clip.startTime).toBe(startTime);
		
		expect(clip.url).toBe('/clips/24/');
		expect(clip.wavFileUrl).toBe('/clips/24/wav/');
		expect(clip.annotationsUrl).toBe('/clips/24/annotations/');
		expect(clip.annotationsJsonUrl).toBe('/clips/24/annotations/json/');
		expect(clip.getAnnotationUrl('bobo')).toBe(
			'/clips/24/annotations/bobo/');
		
		expect(clip.samples).toBe(null);
		clip.samples = [];
		expect(clip.samples.length).toBe(0);
		
		expect(clip.annotations).toBe(null);
		clip.annotations = new Map();
		expect(clip.annotations.size).toBe(0);
		clip.annotations.set('Classification', 'Call');
		expect(clip.annotations.size).toBe(1);
		expect(clip.annotations.get('Classification')).toBe('Call');
		clip.annotations = new Map([['one', 1], ['two', 2]]);
		expect(clip.annotations.size).toBe(2);
		expect(clip.annotations.get('one')).toBe(1);
		
	});

	
});


class _TestClip {
	
	constructor(num) {
		this.num = num;
		this.status = _CLIP_STATUS.UNLOADED;
	}
	
}


class _TestClipLoader {
	
	isClipUnloaded(clip) {
		return clip.status === _CLIP_STATUS.UNLOADED;
	}
	
	loadClip(clip) {
		clip.status = _CLIP_STATUS.LOADED;
	}
	
	unloadClip(clip) {
		clip.status = _CLIP_STATUS.UNLOADED;
	}
	
}


describe('_PreloadingClipManager', () => {
	
	
	function expectLoadedClipNums(clips, nums) {
		expect(_getLoadedClipNums(clips)).toEqual(nums);
	}
	
	
	function expectState(manager, pageNum, clipNums) {
		expect(manager.pageNum).toBe(pageNum);
		expectLoadedClipNums(manager.clips, clipNums);
	}
	
	
	it('continuous loaded clip ranges', () => {

		const settings = {
			'maxNumClips': 12,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 2
		};
		
		const nums = rangeArray(16);
		const clips = nums.map(num => new _TestClip(num));
		
		const pageStartClipNums = [0, 1, 3, 7, 9, 12, 14, 16];

		const loader = new _TestClipLoader();
		
		const manager = new _PreloadingClipManager(
			settings, clips, pageStartClipNums, 0, loader);
		
		expect(manager.clips).toEqual(clips);
		expect(manager.pageStartClipNums).toEqual(pageStartClipNums);
		expect(manager.settings).toEqual(settings);
		
		// Should initially be at page 0 with pages 0-2 loaded.
		expectState(manager, 0, rangeArray(7));
		
		// Advance to page 1. Afterwards, pages 0-3 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 1, rangeArray(0, 9));
		
		// Advance to page 2. Afterwards, pages 0-4 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 2, rangeArray(0, 12));
		
		// Advance to page 3. Afterwards, pages 2-5 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 3, rangeArray(3, 14));
		
		// Advance to page 4. Afterwards, pages 3-6 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 4, rangeArray(7, 16));
		
		// Advance to page 5. This should not load or unload any clips.
		manager.pageNum += 1;
		expectState(manager, 5, rangeArray(7, 16));
		
		// Advance to page 6. This should not load or unload any clips.
		manager.pageNum += 1;
		expectState(manager, 6, rangeArray(7, 16));
		
		// Return to page 0. Afterwards, pages 0-4 should be loaded.
		manager.pageNum = 0;
		expectState(manager, 0, rangeArray(12));
		
		// Go to page 3. Afterwards, pages 2-5 should be loaded.
		// Advance to page 3. Afterwards, pages 2-5 should be loaded.
		manager.pageNum = 3;
		expectState(manager, 3, rangeArray(3, 14));
		
		// Repaginate to two clips per page and nagivate to page 4.
		// Afterwards, pages 2 through 6 should be loaded.
		manager.update([0, 2, 4, 6, 8, 10, 12, 14, 16], 4);
		expectState(manager, 4, rangeArray(4, 14));
		
		// Advance to page 5. Afterwards, pages 2 through 7 should be loaded.
		manager.pageNum = 5;
		expectState(manager, 5, rangeArray(4, 16));
		
		// Go to page 2. Afterwards, pages 1 through 6 should be loaded.
		manager.pageNum = 2;
		expectState(manager, 2, rangeArray(2, 14));
		
	});

	
	it('discontinuous loaded clip ranges', () => {

		const settings = {
			'maxNumClips': 4,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 1
		};
		
		const nums = rangeArray(8);
		const clips = nums.map(num => new _TestClip(num));
		
		const pageStartClipNums = rangeArray(9);

		const loader = new _TestClipLoader();
		
		const manager = new _PreloadingClipManager(
			settings, clips, pageStartClipNums, 0, loader);
		
		expect(manager.clips).toEqual(clips);
		expect(manager.pageStartClipNums).toEqual(pageStartClipNums);
		expect(manager.settings).toEqual(settings);
		
		// Should initially be at page 0 with pages 0-1 loaded.
		expectState(manager, 0, rangeArray(2));
		
		// Go to page 7. Afterwards, pages 0-1 and 6-7 should be loaded.
		manager.pageNum = 7;
		expectState(manager, 7, [0, 1, 6, 7]);
		
		// Go to page 4. Afterwards, pages 3-6 should be loaded.
		manager.pageNum = 4;
		expectState(manager, 4, rangeArray(3, 7));
		
	});

	
});


function _getLoadedClipNums(clips) {
	return clips.filter(c => c.status === _CLIP_STATUS.LOADED).map(c => c.num);
}
