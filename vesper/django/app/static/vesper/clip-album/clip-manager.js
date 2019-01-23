import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { CLIP_LOAD_STATUS } from '/static/vesper/clip-album/clip.js';


// TODO: Make this a static ClipManager class property?
export const PAGE_LOAD_STATUS = {
    UNLOADED: 0,
    PARTIALLY_LOADED: 1,
    LOADED: 2
};


// Set this `true` to load clips in batches, or `false` to load them one
// at a time. We originally loaded clips one at a time, and have retained
// that capability at least for the time being for comparison to the newer
// and faster batch loading.
const _BATCH_LOADS_ENABLED = true;

// Maximum clip samples batch size, in clips. When batch loads are enabled,
// the clip loader loads the samples of the clips of a clip album page in
// batches of this size, except possibly for the last batch.
const _MAX_CLIP_SAMPLES_BATCH_SIZE = 50;

// Maximum clip annotations batch size, in clips. When batch loads are
// enabled, the clip loader loads the annotations of the clips of a clip
// album page in batches of this size, except possibly for the last batch.
const _MAX_CLIP_ANNOTATIONS_BATCH_SIZE = 50;

// Set this `true` to randomly simulate load errors for both clip batches
// and individual clips.
//
// If you set this `true`, also make sure that the calls to
// `_ClipLoader._throwRandomTestError` below are also uncommented.
//
// When both test errors and batch loads are enabled, a simulated load
// failure for the annotations of any clip of a batch causes no annotations
// to be loaded for the entire batch. This means that you probably won't
// see any annotations at all unless you've made the annotations batch
// size and the test error probability sufficiently small that all
// annotations load successfully for some batches.
const _TEST_ERRORS_ENABLED = false;

// The probability that a call to the `_ClipLoader._throwRandomTestError`
// method will throw an error.
const _TEST_ERROR_PROBABILITY = .2;


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
//
// Several methods of the default clip loader were made asynchronous so it
// could guarantee that the clips of the current page would be loaded before
// clips of other pages. This, in turn, made it necessary to make several
// clip manager methods asynchronous to make them testable. Since the
// constructor of a JavaScript class cannot be asynchronous (since it
// cannot return a promise), the clip manager constructor does not load
// any clips, and it initializes the current page number to `null`. The
// page number must be initialized after construction, for example to zero.
export class ClipManager {


    constructor(settings, clips, pageStartClipNums, clipLoader = null) {

        this._settings = settings;
        this._clips = clips;
        this._pageStartClipNums = pageStartClipNums;
        this._pageNum = null;
        this._clipLoader =
            clipLoader === null ? new _ClipLoader() : clipLoader;

        this._loadedPageNums = new Set();
        this._numLoadedClips = 0;

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


    // This is very similar to the `setPageNum` method below. It is not
    // an `async` method (a setter cannot be an `async` method since it
    // does not return a value), but if you don't care about that,
    // invoking it is a little nicer syntactically.
    set pageNum(pageNum) {
        if (pageNum != this.pageNum)
            this.update(this.pageStartClipNums, pageNum);
    }


    // This is very similar to the `pageNum` setter above, but you can
    // await it.
    async setPageNum(pageNum) {
        if (pageNum != this.pageNum)
            return this.update(this.pageStartClipNums, pageNum);
    }


    async incrementPageNum(increment) {
        return this.setPageNum(this.pageNum + increment);
    }


    /**
     * Updates this clip manager for the specified pagination and
     * page number.
     *
     * `pageStartClipNums` is a nonempty, increasing array of clip numbers.
     * `pageNum` is a page number in [0, `pageStartClipNums.length`).
     */
    async update(pageStartClipNums, pageNum) {

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
            return this._updatePageNum(pageNum);

        } else if (pageNum !== this.pageNum) {
            // pagination will not change, but page number will

            return this._updatePageNum(pageNum);

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


    _unloadPartiallyLoadedPage(pageNum) {

        // console.log(
        // 	`clip manager unloading partially loaded page ${pageNum}...`);

        const start = this.pageStartClipNums[pageNum];
        const end = this.pageStartClipNums[pageNum + 1];
        this._clipLoader.unloadClips(this.clips, start, end);

    }


    async _updatePageNum(pageNum) {

        // console.log(`clip manager updating for page ${pageNum}...`);

        const [unloadPageNums, loadPageNums] = this._getUpdatePlan(pageNum);

        for (const pageNum of unloadPageNums)
            this._unloadPage(pageNum);

        await this._loadPages(loadPageNums);

        this._pageNum = pageNum;

        // const pageNums = Array.from(this._loadedPageNums)
        // pageNums.sort((a, b) => a - b);
        // console.log(`clip manager loaded pages: [${pageNums.join(', ')}]`);
        // console.log(`clip manager num loaded clips ${this._numLoadedClips}`);

    }


    /**
     * Loads the specified pages of clips.
     *
     * The pages are loaded one at a time, waiting for all requests to the
     * server for one page to complete before initiating the requests for
     * the next page. This helps ensure that the earlier pages load as
     * quickly as possible.
     */
    async _loadPages(pageNums) {
        for (const pageNum of pageNums)
            await this._loadPage(pageNum);
    }


    async _loadPage(pageNum) {

        if (!this._loadedPageNums.has(pageNum)) {

            // console.log(`clip manager loading page ${pageNum}...`);

            const start = this.pageStartClipNums[pageNum];
            const end = this.pageStartClipNums[pageNum + 1];

            await this._clipLoader.loadClips(this.clips, start, end);

            this._loadedPageNums.add(pageNum);
            this._numLoadedClips += this._getNumPageClips(pageNum);

        }

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
        return [
            [this.pageNum],
            [pageNum]
        ];
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


    async loadClips(clips, start, end) {

        if (_BATCH_LOADS_ENABLED) {
            // load clips in batches

            return Promise.all([
                this._batchLoadClipSamples(clips, start, end),
                this._batchLoadClipAnnotations(clips, start, end)
            ]);

        } else {
            // load clips one at a time

            return Promise.all([
                this._loadClipSamples(clips, start, end),
                this._loadClipAnnotations(clips, start, end)
            ]);

        }

    }


    async _batchLoadClipSamples(clips, start, end) {

        const batches = this._getClipBatches(
            clips, start, end, _MAX_CLIP_SAMPLES_BATCH_SIZE);

        return Promise.all(
            batches.map(b => this._loadClipBatchSamples(b)));

    }


    _getClipBatches(clips, start, end, max_batch_size) {

        const batches = [];
        let batch = [];

        for (let i = start; i < end; i++) {

            batch.push(clips[i]);

            if (batch.length === max_batch_size) {
                batches.push(batch);
                batch = [];
            }

        }

        if (batch.length !== 0)
            batches.push(batch);

        return batches;

    }


    async _loadClipBatchSamples(clips) {

        // Work only with clips for which samples are unloaded.
        clips = clips.filter(
            clip => clip.samplesStatus === CLIP_LOAD_STATUS.UNLOADED);

        if (clips.length > 0) {
            // some clips need loading

            // Update clip load statuses.
            this._setClipBatchSamplesStatuses(
                clips, CLIP_LOAD_STATUS.LOADING);

            try {

                const result = await this._fetchClipBatchAudios(clips);
                const arrayBuffer = await result.arrayBuffer();
                return this._decodeClipBatchAudios(clips, arrayBuffer);

            } catch (error) {

                this._onClipBatchSamplesLoadError(clips, error);

            }

        }

    }


    _setClipBatchSamplesStatuses(clips, status) {
        for (const clip of clips)
            this._setClipSamplesStatus(clip, status);
    }


    _setClipSamplesStatus(clip, status) {

        if (status !== clip.samplesStatus) {
            // status will change

            clip.samplesStatus = status;

            if (status === CLIP_LOAD_STATUS.LOADED) {

                clip.view.onClipSamplesChanged();

            } else if (status === CLIP_LOAD_STATUS.UNLOADED) {

                // Forget samples so we won't prevent garbage collection.
                clip.audioBuffer = null;
                clip.samples = null;

                clip.view.onClipSamplesChanged();

            }

        }

    }


    async _fetchClipBatchAudios(clips) {

        const clipIds = clips.map(clip => clip.id);

        return fetch('/batch/read/clip-audios/', {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify({
                'clip_ids': clipIds
            })
        });

    }


    async _decodeClipBatchAudios(clips, arrayBuffer) {


        // Get array of clip audios from buffer. Audios are stored one
        // after the other, with each prefixed with its size in bytes
        // in a 32-bit little-endian integer.

        const audios = [];
        const dataView = new DataView(arrayBuffer);
        let offset = 0;

        while (offset < arrayBuffer.byteLength) {

            // Get audio size, a 32-bit little-endian integer.
            const size = dataView.getUint32(offset, true);
            offset += 4;

            // Get audio.
            //
            // Note that the ArrayBuffer.prototype.slice method
            // copies a specified portion of an existing ArrayBuffer
            // into a new ArrayBuffer. There does not appear to be
            // a way to create a new ArrayBuffer that is just a view
            // of a portion of an existing ArrayBuffer, i.e. without
            // copying the contents of the new ArrayBuffer.
            const audio = arrayBuffer.slice(offset, offset + size);
            offset += size;

            audios.push(audio);

        }


        // Get promises for individual clip audio decodes.
        const promises = [];
        for (let i = 0; i < audios.length; i++) {
            const promise = this._decodeClipAudio(clips[i], audios[i]);
            promises.push(promise);
        }

        return Promise.all(promises);

    }


    async _decodeClipAudio(clip, arrayBuffer) {

        const context = this._getAudioContext(clip.sampleRate);

        try {

            // As of October, 2018, Safari does not support the
            // single-argument promises version of `decodeAudioData` used
            // here. Instead, it supports only an older, three-argument,
            // non-promises version of the function. If needed, it would
            // be pretty straightforward to wrap the three-argument
            // version to make a standin for the single-argument version
            // (see https://developer.mozilla.org/en-US/docs/Web/
            // JavaScript/Guide/Using_promises#
            // Creating_a_Promise_around_an_old_callback_API). Safari has
            // other audio-related issues, however (see comment toward the
            // top of this file for details), so we just don't support it
            // for now.
            const audioBuffer = await context.decodeAudioData(arrayBuffer);

            this._setClipSamples(clip, audioBuffer);

        } catch (error) {

            this._onClipSamplesLoadError(clip, error);
        }

    }


    _getAudioContext(sampleRate) {

        let context = this._audioContexts.get(sampleRate);

        if (context === undefined) {
            // no context for this sample rate in cache

            // console.log(
            //     `creating audio context for sample rate ${sampleRate}...`);

            // Create context for this sample rate and add to cache.
            context = new OfflineAudioContext(1, 1, sampleRate);
            this._audioContexts.set(sampleRate, context);

        }

        return context;

    }


    _setClipSamples(clip, audioBuffer) {

        // A samples load operation can be canceled while in progress
        // by changing `clip.samplesStatus` from `CLIP_LOAD_STATUS.LOADING`
        // to `CLIP_LOAD_STATUS_UNLOADED`. In this case we ignore the
        // results of the operation.

        if (clip.samplesStatus === CLIP_LOAD_STATUS.LOADING) {

            //            this._throwRandomTestError(
            //                'A random test error was thrown from _setClipSamples.');

            clip.audioBuffer = audioBuffer;
            clip.samples = audioBuffer.getChannelData(0);

            this._setClipSamplesStatus(clip, CLIP_LOAD_STATUS.LOADED);

        }

    }


    _throwRandomTestError(message) {
        if (_TEST_ERRORS_ENABLED && Math.random() <= _TEST_ERROR_PROBABILITY)
            throw Error(message);
    }


    _onClipSamplesLoadError(clip, error) {

        // A samples load operation can be canceled while in progress by
        // changing `clip.samplesStatus` from `CLIP_LOAD_STATUS.LOADING`
        // to `CLIP_LOAD_STATUS_UNLOADED`. In this case we ignore the
        // results of the operation.

        if (clip.samplesStatus === CLIP_LOAD_STATUS.LOADING) {

            this._handleError(
                `Load of clip ${clip.num} samples failed.`, error);

            this._setClipSamplesStatus(clip, CLIP_LOAD_STATUS.UNLOADED);

        }

    }


    // TODO: Figure out a better way to notify user of errors.
    // Error notification should be more visible than a console message,
    // but less intrusive than a modal dialog.
    _handleError(message, error) {
        console.error(`${message} Error message was: ${error}`);
    }


    _onClipBatchSamplesLoadError(clips, error) {
        this._handleError('Load of clip batch samples failed.', error);
        this._setClipBatchSamplesStatuses(clips, CLIP_LOAD_STATUS.UNLOADED);
    }


    async _batchLoadClipAnnotations(clips, start, end) {

        const batches = this._getClipBatches(
            clips, start, end, _MAX_CLIP_ANNOTATIONS_BATCH_SIZE);

        return Promise.all(
            batches.map(b => this._loadClipBatchAnnotations(b)));

    }


    async _loadClipBatchAnnotations(clips) {

        // Work only with clips for which annotations are unloaded.
        clips = clips.filter(
            clip => clip.annotationsStatus === CLIP_LOAD_STATUS.UNLOADED);

        if (clips.length > 0) {
            // some clips need loading

            // Update clip load statuses.
            this._setClipBatchAnnotationsStatuses(
                clips, CLIP_LOAD_STATUS.LOADING);


            // Load annotations.

            try {

                const result = await this._fetchClipBatchAnnotations(clips);
                const annotations = await result.json();
                this._setClipBatchAnnotations(clips, annotations);

            } catch (error) {

                this._onClipBatchAnnotationsLoadError(clips, error);

            }


        }

    }


    _setClipBatchAnnotationsStatuses(clips, status) {
        for (const clip of clips)
            this._setClipAnnotationsStatus(clip, status);
    }


    _setClipAnnotationsStatus(clip, status) {

        if (status !== clip.annotationsStatus) {
            // status will change

            clip.annotationsStatus = status;

            if (status === CLIP_LOAD_STATUS.LOADED) {

                clip.view.onClipAnnotationsChanged();

            } else if (status == CLIP_LOAD_STATUS.UNLOADED) {

                // Forget annotations so we won't prevent garbage collection.
                clip.annotations = null;

                clip.view.onClipAnnotationsChanged();

            }

        }

    }


    async _fetchClipBatchAnnotations(clips) {

        const clipIds = clips.map(clip => clip.id);

        return fetch('/batch/read/clip-annotations/', {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            method: 'POST',
            body: JSON.stringify({
                'clip_ids': clipIds
            })
        });

    }


    _setClipBatchAnnotations(clips, annotations) {
        for (const clip of clips)
            this._setClipAnnotations(clip, annotations[clip.id]);
    }


    _setClipAnnotations(clip, annotations) {

        // An annotations load operation can be canceled while in progress
        // by changing `clip.annotationsStatus` from
        // `CLIP_LOAD_STATUS.LOADING` to `CLIP_LOAD_STATUS_UNLOADED`.
        // In this case we ignore the results of the operation.

        if (clip.annotationsStatus === CLIP_LOAD_STATUS.LOADING) {

            //            this._throwRandomTestError(
            //                'A random test error was thrown from _setClipAnnotations.');

            clip.annotations = annotations;

            this._setClipAnnotationsStatus(clip, CLIP_LOAD_STATUS.LOADED);

        }

    }


    _onClipBatchAnnotationsLoadError(clips, error) {

        this._handleError('Batch load of clip annotations failed.', error);

        this._setClipBatchAnnotationsStatuses(
            clips, CLIP_LOAD_STATUS.UNLOADED);

    }


    async _loadClipSamples(clips, start, end) {

        clips = clips.slice(start, end);

        // Work only with clips for which samples are unloaded.
        clips = clips.filter(
            clip => clip.samplesStatus === CLIP_LOAD_STATUS.UNLOADED);

        if (clips.length > 0)
            // some clips need loading

            return Promise.all(
                clips.map(c => this._loadClipSamplesAux(c)));

    }


    async _loadClipSamplesAux(clip) {

        clip.samplesStatus = CLIP_LOAD_STATUS.LOADING;

        try {

            const response = await fetch(clip.wavFileUrl);
            const arrayBuffer = await response.arrayBuffer();
            return this._decodeClipAudio(clip, arrayBuffer);

        } catch (error) {

            this._onClipSamplesLoadError(clip, error);

        }

    }


    async _loadClipAnnotations(clips, start, end) {

        clips = clips.slice(start, end);

        // Work only with clips for which annotations are unloaded.
        clips = clips.filter(
            clip => clip.annotationsStatus === CLIP_LOAD_STATUS.UNLOADED);

        if (clips.length > 0)
            // some clips need loading

            return Promise.all(
                clips.map(c => this._loadClipAnnotationsAux(c)));

    }


    async _loadClipAnnotationsAux(clip) {

        clip.annotationsStatus = CLIP_LOAD_STATUS.LOADING;

        try {

            const response = await fetch(clip.annotationsJsonUrl);
            const annotations = await response.json();
            this._setClipAnnotations(clip, annotations);

        } catch (error) {

            this._onClipAnnotationsLoadError(clip, error);

        }

    }


    _onClipAnnotationsLoadError(clip, error) {

        // An annotations load operation can be canceled while in progress
        // by changing `clip.annotationsStatus` from
        // `CLIP_LOAD_STATUS.LOADING` to `CLIP_LOAD_STATUS_UNLOADED`.
        // In this case we ignore the results of the operation.

        if (clip.annotationsStatus === CLIP_LOAD_STATUS.LOADING) {

            this._handleError(
                `Load of clip ${clip.num} annotations failed.`, error);

            clip.annotations = null;

            this._setClipAnnotationsStatus(clip, CLIP_LOAD_STATUS.UNLOADED);

        }

    }


    unloadClips(clips, start, end) {
        // console.log('unloadClips', start, end);
        clips = clips.slice(start, end);
        const status = CLIP_LOAD_STATUS.UNLOADED
        this._setClipBatchSamplesStatuses(clips, status);
        this._setClipBatchAnnotationsStatuses(clips, status);
    }


}
