// TODO: Make this a static Clip class property?
export const CLIP_LOAD_STATUS = {
    UNLOADED: 0,
    LOADING: 1,
    LOADED: 2
};


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
		this._annotationsStatus = CLIP_LOAD_STATUS.UNLOADED;

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


	get annotationsStatus() {
		return this._annotationsStatus;
	}


	set annotationsStatus(status) {
		this._annotationsStatus = status;
	}


	get url() {
		return `/clips/${this.id}/`;
	}


	get wavFileUrl() {
    	return `${this.url}wav/`;
	}


	get annotations() {
		return this._annotations;
	}


	set annotations(annotations) {
		this._annotations = annotations;
	}


	get annotationsUrl() {
		return `${this.url}annotations/`;
	}


	get annotationsJsonUrl() {
		return `${this.annotationsUrl}json/`;
	}


	getAnnotationUrl(name) {
		return `${this.annotationsUrl}${name}/`;
	}


}
