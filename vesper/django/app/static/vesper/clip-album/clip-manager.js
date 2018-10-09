import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { CLIP_LOAD_STATUS } from '/static/vesper/clip-album/clip.js';


// TODO: Make this a static ClipManager class property?
export const PAGE_LOAD_STATUS = {
    UNLOADED: 0,
    PARTIALLY_LOADED: 1,
    LOADED: 2
}


/*
Testing in May, 2018 revealed several limitations of the current
Safari Web Audio implementation :

1. One must use "webkitAudioContext" and "webkitOfflineAudioContext"
   instead of "AudioContext" and "OfflineAudioContext". See
   https://github.com/cwilso/AudioContext-MonkeyPatch/blob/gh-pages/
   AudioContextMonkeyPatch.js for some JavaScript that remedies this
   (as well as other problems: perhaps we can implement our own, simpler
   remedy).

2. An offline audio context cannot have a sample rate of 22050 hertz.
   Trying to create one results in the error message:

       SyntaxError: The string did not match the expected pattern.

   An offline audio context can have a sample rate of 44100, 48000, or
   96000 hertz, and perhaps other rates that I didn't try.

3. Safari's implementation of the "decodeAudioData" method is not
   promises-based, requiring a single argument, but instead requires
   three arguments: the audio data, a success handler, and a failure
   handler. See https://stackoverflow.com/questions/48597747/
   how-to-play-a-sound-file-safari-with-web-audio-api.

Limitations 1 and 3 are straightforward to work around. Limitation 2
is not so easy. On Safari we can use Web Audio to decode, say, 22050
hertz audio to 44100 hertz, but we will use twice the storage for our
audio data than we would if the data were left at the lower rate.
Another option would be to not use Web Audio to decode data sent from
the server, and implement our own decoder instead. That decoder would
necessarily support fewer formats, in fact probably just one
uncompressed format. Hopefully we could still use Web Audio to play
clips from whatever their native rate, though this should be tested.
*/


// Loads and unloads clip samples and annotations on behalf of a clip album.
//
// Different clip managers may load clip data according to different policies.
// For example, one manager may load data for clip pages as they are displayed,
// requesting data from the server one clip at a time. Another manager may load
// the data for the clips of a page in bulk, obtaining all of the data from
// the server in a single request. Yet other managers may load data for all
// the clips of an album greedily, regardless of which pages have or have not
// been displayed.
export class ClipManager {


	constructor(
		    settings, clips, pageStartClipNums, pageNum = 0,
		    clipLoader = null) {

		this._settings = settings;
		this._clips = clips;
		this._pageStartClipNums = null;
		this._pageNum = null;
		this._clipLoader = clipLoader === null ? new _ClipLoader() : clipLoader;

		this._loadedPageNums = new Set();
		this._numLoadedClips = 0;

		this.update(pageStartClipNums, pageNum);

	}


	get clips() {
		return this._clips;
	}


	get settings() {
		return this._settings;
	}


	get pageStartClipNums() {
		return this._pageStartClipNums;
	}


	get pageNum() {
		return this._pageNum;
	}


	set pageNum(pageNum) {
		if (pageNum != this.pageNum) {
		    this.update(this.pageStartClipNums, pageNum);
		}
	}


	/**
	 * Updates this clip manager for the specified pagination and
	 * page number.
	 *
	 * `pageStartClipNums` is a nonempty, increasing array of clip numbers.
	 * `pageNum` is a page number in [0, `pageStartClipNums.length`).
	 */
	update(pageStartClipNums, pageNum) {

		// We assume that while `this._pageStartClipNums` and `this._pageNum`
		// are both initialized to `null` in the constructor, this method
		// is never invoked with a `null` argument: `pageStartClipNums`
		// is always a nonempty, increasing array of numbers and `pageNum`
		// is always a number.

		if (this.pageStartClipNums === null ||
				!ArrayUtils.arraysEqual(
					pageStartClipNums, this.pageStartClipNums)) {
			// pagination will change

			this._updatePagination(pageStartClipNums, pageNum);
			this._updatePageNum(pageNum);

	    } else if (pageNum !== this.pageNum) {
	    	// pagination will not change, but page number will

	    	this._updatePageNum(pageNum);

	    }

	}


	_updatePagination(pageStartClipNums, pageNum) {

		const oldPageStartClipNums = this._pageStartClipNums;

		this._pageStartClipNums = pageStartClipNums

		if (oldPageStartClipNums !== null) {
			// may have pages loaded according to the old pagination

			const numAlbumPages = this.pageStartClipNums.length - 1;

			const requiredPageNums =
				new Set(this._getRequiredPageNums(pageNum));

			this._loadedPageNums = new Set();
			this._numLoadedClips = 0;

			for (let i = 0; i < numAlbumPages; i++) {

				const status = this._getPageStatus(i);

				if (status === PAGE_LOAD_STATUS.LOADED) {

					this._loadedPageNums.add(i);
					this._numLoadedClips += this._getNumPageClips(i);

				} else if (status === PAGE_LOAD_STATUS.PARTIALLY_LOADED) {

					if (requiredPageNums.has(i))
						// page required under new pagination

						// Load entire page.
						this._loadPage(i);

					else
						// page not required under new pagination

						// Unload part of page that is loaded.
					    this._unloadPartiallyLoadedPage(i);

				}

			}

		}

	}


	/**
	 * Gets the numbers of the pages that this clip manager should
	 * definitely load for the current pagination and the specified
	 * page number. The page numbers are returned in an array in the
	 * order in which the pages should be loaded.
	 */
	_getRequiredPageNums(pageNum) {
		throw new Error('_ClipManager._getRequiredPageNums not implemented');
	}


	_getPageStatus(pageNum) {

		let hasUnloadedClips = false;
		let hasLoadedClips = false;

		const start = this.pageStartClipNums[pageNum];
		const end = this.pageStartClipNums[pageNum + 1];

		for (let i = start; i < end; i++) {

			if (this._clipLoader.isClipUnloaded(this.clips[i])) {

				if (hasLoadedClips)
					return PAGE_LOAD_STATUS.PARTIALLY_LOADED;
				else
					hasUnloadedClips = true;

			} else {

				if (hasUnloadedClips)
					return PAGE_LOAD_STATUS.PARTIALLY_LOADED;
				else
					hasLoadedClips = true;

			}

		}

		// If we get here, either all of the clips of the page were
		// unloaded or all were not unloaded.
		return hasLoadedClips ?
            PAGE_LOAD_STATUS.LOADED : PAGE_LOAD_STATUS.UNLOADED;

	}


	_getNumPageClips(pageNum) {
		return this._getNumPageRangeClips(pageNum, 1);
	}


	_getNumPageRangeClips(pageNum, numPages) {
		const clipNums = this.pageStartClipNums;
	    return clipNums[pageNum + numPages] - clipNums[pageNum];
	}


	_loadPage(pageNum) {

    	if (!this._loadedPageNums.has(pageNum)) {

    		// console.log(`clip manager loading page ${pageNum}...`);

			const start = this.pageStartClipNums[pageNum];
			const end = this.pageStartClipNums[pageNum + 1];

			this._clipLoader.loadClips(this.clips, start, end);

    		this._loadedPageNums.add(pageNum);
    		this._numLoadedClips += this._getNumPageClips(pageNum);

    	}

	}


	_unloadPartiallyLoadedPage(pageNum) {

		// console.log(
		// 	`clip manager unloading partially loaded page ${pageNum}...`);

		const start = this.pageStartClipNums[pageNum];
		const end = this.pageStartClipNums[pageNum + 1];
        this._clipLoader.unloadClips(this.clips, start, end);

	}


	_updatePageNum(pageNum) {

	    // console.log(`clip manager updating for page ${pageNum}...`);

		const [unloadPageNums, loadPageNums] = this._getUpdatePlan(pageNum);

		for (const pageNum of unloadPageNums)
			this._unloadPage(pageNum);

		for (const pageNum of loadPageNums)
			this._loadPage(pageNum);

		this._pageNum = pageNum;

		const pageNums = Array.from(this._loadedPageNums)
	    pageNums.sort((a, b) => a - b);
		// console.log(`clip manager loaded pages: [${pageNums.join(', ')}]`);
		// console.log(`clip manager num loaded clips ${this._numLoadedClips}`);

	}


	/**
	 * Returns an array `[unloadPageNums, loadPageNums]` containing two
	 * arrays of page numbers. `unloadPageNums` contains the numbers of
	 * loaded pages that should be unloaded, and `loadPageNums` contains
	 * the numbers of unloaded pages that should be loaded.
	 */
	_getUpdatePlan(pageNum) {
		throw new Error('_ClipManager._getUpdatePlan not implemented');
	}


	_unloadPage(pageNum) {

    	if (this._loadedPageNums.has(pageNum)) {

    		// console.log(`clip manager unloading page ${pageNum}...`);

			const start = this.pageStartClipNums[pageNum];
			const end = this.pageStartClipNums[pageNum + 1];

			this._clipLoader.unloadClips(this.clips, start, end);

    		this._loadedPageNums.delete(pageNum);
    		this._numLoadedClips -= this._getNumPageClips(pageNum);

    	}

	}


}


export class SimpleClipManager extends ClipManager {


	_getRequiredPageNums(pageNum) {
		return [pageNum];
	}


	_getUpdatePlan(pageNum) {
		return [[this.pageNum], [pageNum]];
	}


}


export class PreloadingClipManager extends ClipManager {


	/**
	 * The settings used by this class are:
	 *
	 *     maxNumClips - maximum number of clips kept in memory.
	 *     numPrecedingPreloadedPages - number of preceding pages to preload.
	 *     numFollowingPreloadedPages - number of following pages to preload.
	 */


	_getRequiredPageNums(pageNum) {

		const pageNums = [pageNum];

		const numAlbumPages = this.pageStartClipNums.length - 1;
		for (let i = 0; i < this.settings.numFollowingPreloadedPages; i++) {
			const j = pageNum + i + 1;
			if (j >= numAlbumPages)
				break;
			pageNums.push(j);
		}

		for (let i = 0; i < this.settings.numPrecedingPreloadedPages; i++) {
			const j = pageNum - i - 1;
			if (j < 0)
				break;
			pageNums.push(j);
		}

		return pageNums;

	}


	_getUpdatePlan(pageNum) {
		const requiredPageNums = this._getRequiredPageNums(pageNum);
		const loadPageNums = this._getLoadPageNums(requiredPageNums);
        const unloadPageNums =
        	this._getUnloadPageNums(requiredPageNums, loadPageNums);
        return [unloadPageNums, loadPageNums];
	}


	_getLoadPageNums(requiredPageNums) {
		const not_loaded = i => !this._loadedPageNums.has(i);
		return requiredPageNums.filter(not_loaded);
	}


	_getUnloadPageNums(requiredPageNums, loadPageNums) {

		const numAlbumPages = this.pageStartClipNums.length - 1;
		const min = (a, b) => Math.min(a, b);
		const minPageNum = requiredPageNums.reduce(min, numAlbumPages);
		const max = (a, b) => Math.max(a, b);
		const maxPageNum = requiredPageNums.reduce(max, 0);

		const numClipsToLoad = this._getNumClipsInPages(loadPageNums)
		const numClipsToUnload = Math.max(
			this._numLoadedClips + numClipsToLoad - this.settings.maxNumClips,
			0);

		const pageNums = new Set(this._loadedPageNums);
		const unloadPageNums = [];
		let numClipsUnloaded = 0;

		while (numClipsUnloaded < numClipsToUnload) {

			const i = this._findMostDistantLoadedPageNum(
				pageNums, minPageNum, maxPageNum);

			if (i === null)
				// no more pages that can be unloaded

				break;

			pageNums.delete(i);
			unloadPageNums.push(i);
			numClipsUnloaded += this._getNumPageClips(i);

		}

		return unloadPageNums;

	}


	_getNumClipsInPages(pageNums) {
		const numPageClips = pageNums.map(i => this._getNumPageClips(i));
		return numPageClips.reduce((a, v) => a + v, 0);
	}


	_findMostDistantLoadedPageNum(pageNums, minPageNum, maxPageNum) {

		let mostDistantPageNum = null;
		let maxDistance = 0;
		let distance;

		for (const i of pageNums) {

			if (i < minPageNum)
				distance = minPageNum - i;
			else if (i > maxPageNum)
				distance = i - maxPageNum;
			else
				distance = 0;

			if (distance > maxDistance) {
				mostDistantPageNum = i;
				maxDistance = distance;
			}

		}

		return mostDistantPageNum;

	}


}


class _ClipLoader {


	constructor() {

		// We use Web Audio `OfflineAudioContext` objects to decode clip
		// audio buffers that arrive from the server. For some reason,
		// it appears that different contexts are required for different
		// sample rates. We allocate the contexts as needed, storing them
		// in a `Map` from sample rates to contexts.
		this._audioContexts = new Map();

	}


    isClipUnloaded(clip) {
		return clip.samplesStatus === CLIP_LOAD_STATUS.UNLOADED;
    }


    loadClips(clips, start, end) {
        for (let i = start; i < end; i++)
            this.loadClip(clips[i]);
    }
    
    
	loadClip(clip) {

		if (clip.samplesStatus === CLIP_LOAD_STATUS.UNLOADED)
			this._loadClipSamples(clip);

		if (clip.annotationsStatus === CLIP_LOAD_STATUS.UNLOADED)
			this._loadClipAnnotations(clip);

	}


//	async _loadClipSamples(clip) {
//	    
//        clip.samplesStatus = CLIP_LOAD_STATUS.LOADING;
//        
//	    try {
//	        
//	        const result = await fetch(clip.wavFileUrl);
//	        const arrayBuffer = await result.arrayBuffer();
//	        const audioBuffer = await this._decodeAudioData(arrayBuffer, clip);
//	        this._onLoadClipSamplesSuccess(audioBuffer, clip);
//	        
//	    } catch(error) {
//	        
//	        this._onLoadClipSamplesFailure(error, clip);
//	        
//	    }
//	    
//	}
	
	
	_loadClipSamples(clip) {
	    
        clip.samplesStatus = CLIP_LOAD_STATUS.LOADING;

        fetch(clip.wavFileUrl)
        .then(r => r.arrayBuffer())
        .then(b => this._decodeAudioData(b, clip))
        .then(b => this._onLoadClipSamplesSuccess(b, clip))
        .catch(e => this._onLoadClipSamplesFailure(e, clip));

	}
	
	
	_decodeAudioData(response, clip) {
	    
        const sampleRate = clip.sampleRate;

        let context = this._audioContexts.get(sampleRate);

        if (context === undefined) {
            // no context for this sample rate in cache

            // console.log(
            //  `creating audio context for sample rate ${sampleRate}...`);

            // Create context for this sample rate and add to cache.
            context = new OfflineAudioContext(1, 1, sampleRate);
            this._audioContexts.set(sampleRate, context);

        }

        // As of October, 2018, Safari does not support the single-argument
        // promises version of `decodeAudioData` used here. Instead, it
        // supports only an older, three-argument, non-promises version
        // of the function. I believe the three-argument version can be
        // wrapped in a straightforward way to create a one-argument
        // version if needed (see https://developer.mozilla.org/en-US/
        // docs/Web/JavaScript/Guide/Using_promises#
        // Creating_a_Promise_around_an_old_callback_API). Safari has
        // other audio-related issues, however (see comment toward the
        // top of this file for details), so we just don't support it
        // for now.
        return context.decodeAudioData(response);
        
	}
	
	
    _onLoadClipSamplesSuccess(audioBuffer, clip) {
        
        // A samples load operation can be canceled while in progress
        // by changing `clip.samplesStatus` from `CLIP_LOAD_STATUS.LOADING`
        // to `CLIP_LOAD_STATUS_UNLOADED`. In this case we ignore the
        // results of the operation.
        
        if (clip.samplesStatus === CLIP_LOAD_STATUS.LOADING) {

            clip.audioBuffer = audioBuffer;
            clip.samples = audioBuffer.getChannelData(0);
            clip.samplesStatus = CLIP_LOAD_STATUS.LOADED;

            clip.view.onClipSamplesChanged();

        }
        
    }
    
    
    _onLoadClipSamplesFailure(error, clip) {
        
        // A samples load operation can be canceled while in progress by
        // changing `clip.samplesStatus` from `CLIP_LOAD_STATUS.LOADING`
        // to `CLIP_LOAD_STATUS_UNLOADED`. In this case we ignore the
        // results of the operation.
        
        if (clip.samplesStatus === CLIP_LOAD_STATUS.LOADING) {

            // TODO: Notify user of errors.
            console.error(
                `Load of clip ${clip.num} samples failed. ` +
                `Error message was: ${error}.`);
            
            clip.samplesStatus = CLIP_LOAD_STATUS.UNLOADED;

            clip.view.onClipSamplesChanged();

        }
        
    }
    
    
    _loadClipAnnotations(clip) {

        clip.annotationsStatus = CLIP_LOAD_STATUS.LOADING;

        fetch(clip.annotationsJsonUrl)
        .then(r => r.json())
        .then(a => this._onLoadClipAnnotationsSuccess(a, clip))
        .catch(e => this._onLoadClipAnnotationsFailure(e, clip));

    }
    
    
    _onLoadClipAnnotationsSuccess(annotations, clip) {
        
        // An annotations load operation can be canceled while in progress
        // by changing `clip.annotationsStatus` from
        // `CLIP_LOAD_STATUS.LOADING` to `CLIP_LOAD_STATUS_UNLOADED`.
        // In this case we ignore the results of the operation.

        if (clip.annotationsStatus === CLIP_LOAD_STATUS.LOADING) {
            
            clip.annotations = annotations;
            clip.annotationsStatus = CLIP_LOAD_STATUS.LOADED;
            clip.view.onClipAnnotationsChanged();
            
        }
        
    }
    
    
    _onLoadClipAnnotationsFailure(error, clip) {
        
        // An annotations load operation can be canceled while in progress
        // by changing `clip.annotationsStatus` from
        // `CLIP_LOAD_STATUS.LOADING` to `CLIP_LOAD_STATUS_UNLOADED`.
        // In this case we ignore the results of the operation.
        
        if (clip.annotationsStatus === CLIP_LOAD_STATUS.LOADING) {
            
            // TODO: Notify user of errors.
            console.error(
                `Load of clip ${clip.num} annotations failed. ` +
                `Error message was: ${error}.`);
            
            clip.annotations = null;
            clip.annotationsStatus = CLIP_LOAD_STATUS.UNLOADED;
            
            clip.view.onClipAnnotationsChanged();
            
        }
        
    }


    unloadClips(clips, start, end) {
        for (let i = start; i < end; i++)
            this.unloadClip(this.clips[i]);        
    }
    
    
    unloadClip(clip) {

		clip.audioBuffer = null;
		clip.samples = null;
		clip.samplesStatus = CLIP_LOAD_STATUS.UNLOADED;

		clip.view.onClipSamplesChanged();

	}


}
