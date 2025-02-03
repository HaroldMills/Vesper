import { ArrayUtils } from '../../util/array-utils.js';
import { CLIP_LOAD_STATUS } from '../clip.js';
import { PreloadingClipManager } from '../clip-manager.js';


class _TestClip {

	constructor(num) {
		this.num = num;
		this.status = CLIP_LOAD_STATUS.UNLOADED;
	}

}


class _TestClipLoader {

	isClipUnloaded(clip) {
		return clip.status === CLIP_LOAD_STATUS.UNLOADED;
	}

	loadClips(clips, start, end) {
	    for (let i = start; i < end; i++)
		    clips[i].status = CLIP_LOAD_STATUS.LOADED;
	}

	unloadClips(clips, start, end) {
        for (let i = start; i < end; i++)
		    clips[i].status = CLIP_LOAD_STATUS.UNLOADED;
	}

}


describe('PreloadingClipManager', () => {


    function pause(ms) {
        return new Promise(resolve => setTimeout(() => resolve(), ms));
    }


    function expectState(manager, pageNum, pageNumRanges) {
        expect(manager.pageNum).toBe(pageNum);
        expectLoadedPageNums(manager, pageNumRanges);
    }
    
    
	function expectLoadedPageNums(manager, pageNumRanges) {
	    
	    let clipNums = getClipNums(manager, pageNumRanges);
	    
        const loadedClipNums = manager.clips.filter(
            c => c.status === CLIP_LOAD_STATUS.LOADED).map(c => c.num);
	    
        expect(loadedClipNums).toEqual(clipNums);

	}
	
	
	function getClipNums(manager, pageNumRanges) {
	    
	    if (pageNumRanges.length === 0)
	        return [];
	    
	    else if (Array.isArray(pageNumRanges[0])) {
	        // array of page num ranges
	        
	        const clipNumArrays = pageNumRanges.map(
	            r => getClipNumsAux(manager, ...r));
	        
	        return [].concat(...clipNumArrays);
	        
	    } else {
	        // one page num range
	        
	        return getClipNumsAux(manager, ...pageNumRanges);
 
	    }

	}
	
	
	function getClipNumsAux(manager, startPageNum, endPageNum) {
        const pagination = manager.pagination;
        const startClipNum = pagination[startPageNum];
        const endClipNum = pagination[endPageNum + 1];
        return ArrayUtils.rangeArray(startClipNum, endClipNum);
	}
        
   	
	it('continuous loaded clip ranges', async () => {

		const settings = {
			'maxNumClips': 12,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 2
		};

		const nums = ArrayUtils.rangeArray(16);
		const clips = nums.map(num => new _TestClip(num));

		const pagination = [0, 1, 3, 7, 9, 12, 14, 16];

		const loader = new _TestClipLoader();

		const manager = new PreloadingClipManager(
			settings, clips, pagination, loader);

		expect(manager.clips).toEqual(clips);
		expect(manager.pagination).toEqual(pagination);
		expect(manager.settings).toEqual(settings);

		// Should initially be at no page with no pages loaded.
		expectState(manager, null, []);
		
		// Set page number to 0. Afterwards, pages 0-2 should be loaded.
		await manager.setPageNum(0);
        expectState(manager, 0, [0, 2]);
		
		// Advance to page 1. Afterwards, pages 0-3 should be loaded.
		manager.pageNum += 1;
		
        // Pause to (hopefully) let the page number update complete.
		// It would be nice if there were some way to `await` the update,
        // but there is no such thing as an `async` setter.
        await pause(100);
        
		expectState(manager, 1, [0, 3]);

		// Advance to page 2. Afterwards, pages 0-4 should be loaded.
		await manager.incrementPageNum(1);
		expectState(manager, 2, [0, 4]);

		// Advance to page 3. Afterwards, pages 2-5 should be loaded.
		await manager.incrementPageNum(1);
		expectState(manager, 3, [2, 5]);

		// Advance to page 4. Afterwards, pages 3-6 should be loaded.
        await manager.incrementPageNum(1);
		expectState(manager, 4, [3, 6]);

		// Advance to page 5. This should not load or unload any clips.
        await manager.incrementPageNum(1);
		expectState(manager, 5, [3, 6]);

		// Advance to page 6. This should not load or unload any clips.
        await manager.incrementPageNum(1);
		expectState(manager, 6, [3, 6]);

		// Return to page 0. Afterwards, pages 0-4 should be loaded.
		await manager.setPageNum(0);
		expectState(manager, 0, [0, 4]);

		// Go to page 3. Afterwards, pages 2-5 should be loaded.
		await manager.setPageNum(3);
		expectState(manager, 3, [2, 5]);

		// Go to page 5. Afterwards, pages 3-6 should be loaded.
		await manager.setPageNum(5);
		expectState(manager, 5, [3, 6]);

		// Go to page 2. Afterwards, pages 1-4 should be loaded.
		await manager.setPageNum(2);
		expectState(manager, 2, [1, 4]);

	});


	it('discontinuous loaded clip ranges', async () => {

		const settings = {
			'maxNumClips': 4,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 1
		};

		const nums = ArrayUtils.rangeArray(8);
		const clips = nums.map(num => new _TestClip(num));

		const pagination = ArrayUtils.rangeArray(9);

		const loader = new _TestClipLoader();

		const manager = new PreloadingClipManager(
			settings, clips, pagination, loader);

        // Pause to (hopefully) let the asynchronous clip loads of the
        // clip manager construction complete. It would be nice if there
        // were some way to `await` the construction, but there is no such
        // thing as an `async` constructor.
        await pause(100);
        
		expect(manager.clips).toEqual(clips);
		expect(manager.pagination).toEqual(pagination);
		expect(manager.settings).toEqual(settings);

		// Go to page 0. Afterwards, pages 0-1 should be loaded.
		await manager.setPageNum(0);
		expectState(manager, 0, [0, 1]);

		// Go to page 7. Afterwards, pages 0-1 and 6-7 should be loaded.
		await manager.setPageNum(7);
		expectState(manager, 7, [[0, 1], [6, 7]]);

		// Go to page 4. Afterwards, pages 3-6 should be loaded.
		await manager.setPageNum(4);
		expectState(manager, 4, [3, 6]);

	});


});
