// TODO: Make this a static Clip class property?
export const CLIP_LOAD_STATUS = {
    UNLOADED: 0,
    LOADING: 1,
    LOADED: 2
};


// TODO: Consider providing clip samples, annotations, and tags as
// promises. There might be `getSamples`, `getAnnotations` and `getTags`
// methods that would return promises, replacing the existing getters.
// There might also be awaitable functions for getting the samples or
// metadata of a set of clips. How would we handle setting annotations
// and tags?

// TODO: Consider how we might allow the server to push annotation
// and tag changes (and, more generally, archive changes) to clients,
// e.g. via websockets.


export class Clip {


	constructor(num, id, startIndex, length, sampleRate, startTime) {

		this._num = num;
		this._id = id;
		this._startIndex = startIndex;
		this._length = length;
		this._sampleRate = sampleRate;
		this._startTime = startTime;

		this._samples = null;
		this._samplesStatus = CLIP_LOAD_STATUS.UNLOADED;

		this._annotations = null;
        this._tags = null;
		this._metadataStatus = CLIP_LOAD_STATUS.UNLOADED;

	}


	get id() {
		return this._id;
	}


	get num() {
		return this._num;
	}


	get startIndex() {
	    return this._startIndex;
	}
	
	
	get length() {
		return this._length;
	}


	get sampleRate() {
		return this._sampleRate;
	}


	get span() {
		if (this.length === 0)
			return 0;
		else
			return (this.length - 1) / this.sampleRate;
	}


	get duration() {
		return this.length / this.sampleRate;
	}


	get startTime() {
		return this._startTime;
	}


	get samples() {
		return this._samples;
	}


	set samples(samples) {
		this._samples = samples;
	}


	get samplesStatus() {
		return this._samplesStatus;
	}


	set samplesStatus(status) {
		this._samplesStatus = status;
	}


	get annotations() {
		return this._annotations;
	}


	set annotations(annotations) {
		this._annotations = annotations;
	}


    get tags() {
        return this._tags;
    }


    set tags(tags) {
        this._tags = tags;
    }


	get metadataStatus() {
		return this._metadataStatus;
	}


	set metadataStatus(status) {
		this._metadataStatus = status;
	}


	get url() {
		return `/clips/${this.id}/`;
	}


	get audioUrl() {
    	return `${this.url}audio/`;
	}


	get metadataUrl() {
		return `${this.url}metadata/`;
	}


}
