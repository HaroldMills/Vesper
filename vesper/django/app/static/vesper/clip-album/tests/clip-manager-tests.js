'use strict'


import { CLIP_LOAD_STATUS } from '/static/vesper/clip-album/clip.js';
import { PreloadingClipManager }
    from '/static/vesper/clip-album/clip-manager.js';
import * as ArrayUtils from '/static/vesper/util/array-utils.js';


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

	loadClip(clip) {
		clip.status = CLIP_LOAD_STATUS.LOADED;
	}

	unloadClip(clip) {
		clip.status = CLIP_LOAD_STATUS.UNLOADED;
	}

}


describe('PreloadingClipManager', () => {


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

		const nums = ArrayUtils.rangeArray(16);
		const clips = nums.map(num => new _TestClip(num));

		const pageStartClipNums = [0, 1, 3, 7, 9, 12, 14, 16];

		const loader = new _TestClipLoader();

		const manager = new PreloadingClipManager(
			settings, clips, pageStartClipNums, 0, loader);

		expect(manager.clips).toEqual(clips);
		expect(manager.pageStartClipNums).toEqual(pageStartClipNums);
		expect(manager.settings).toEqual(settings);

		// Should initially be at page 0 with pages 0-2 loaded.
		expectState(manager, 0, ArrayUtils.rangeArray(7));

		// Advance to page 1. Afterwards, pages 0-3 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 1, ArrayUtils.rangeArray(0, 9));

		// Advance to page 2. Afterwards, pages 0-4 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 2, ArrayUtils.rangeArray(0, 12));

		// Advance to page 3. Afterwards, pages 2-5 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 3, ArrayUtils.rangeArray(3, 14));

		// Advance to page 4. Afterwards, pages 3-6 should be loaded.
		manager.pageNum += 1;
		expectState(manager, 4, ArrayUtils.rangeArray(7, 16));

		// Advance to page 5. This should not load or unload any clips.
		manager.pageNum += 1;
		expectState(manager, 5, ArrayUtils.rangeArray(7, 16));

		// Advance to page 6. This should not load or unload any clips.
		manager.pageNum += 1;
		expectState(manager, 6, ArrayUtils.rangeArray(7, 16));

		// Return to page 0. Afterwards, pages 0-4 should be loaded.
		manager.pageNum = 0;
		expectState(manager, 0, ArrayUtils.rangeArray(12));

		// Go to page 3. Afterwards, pages 2-5 should be loaded.
		// Advance to page 3. Afterwards, pages 2-5 should be loaded.
		manager.pageNum = 3;
		expectState(manager, 3, ArrayUtils.rangeArray(3, 14));

		// Repaginate to two clips per page and nagivate to page 4.
		// Afterwards, pages 2 through 6 should be loaded.
		manager.update([0, 2, 4, 6, 8, 10, 12, 14, 16], 4);
		expectState(manager, 4, ArrayUtils.rangeArray(4, 14));

		// Advance to page 5. Afterwards, pages 2 through 7 should be loaded.
		manager.pageNum = 5;
		expectState(manager, 5, ArrayUtils.rangeArray(4, 16));

		// Go to page 2. Afterwards, pages 1 through 6 should be loaded.
		manager.pageNum = 2;
		expectState(manager, 2, ArrayUtils.rangeArray(2, 14));

	});


	it('discontinuous loaded clip ranges', () => {

		const settings = {
			'maxNumClips': 4,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 1
		};

		const nums = ArrayUtils.rangeArray(8);
		const clips = nums.map(num => new _TestClip(num));

		const pageStartClipNums = ArrayUtils.rangeArray(9);

		const loader = new _TestClipLoader();

		const manager = new PreloadingClipManager(
			settings, clips, pageStartClipNums, 0, loader);

		expect(manager.clips).toEqual(clips);
		expect(manager.pageStartClipNums).toEqual(pageStartClipNums);
		expect(manager.settings).toEqual(settings);

		// Should initially be at page 0 with pages 0-1 loaded.
		expectState(manager, 0, ArrayUtils.rangeArray(2));

		// Go to page 7. Afterwards, pages 0-1 and 6-7 should be loaded.
		manager.pageNum = 7;
		expectState(manager, 7, [0, 1, 6, 7]);

		// Go to page 4. Afterwards, pages 3-6 should be loaded.
		manager.pageNum = 4;
		expectState(manager, 4, ArrayUtils.rangeArray(3, 7));

	});


});


function _getLoadedClipNums(clips) {
	return clips.filter(
		c => c.status === CLIP_LOAD_STATUS.LOADED).map(c => c.num);
}
