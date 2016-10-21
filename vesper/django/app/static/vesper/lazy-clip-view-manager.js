'use strict'


class LazyClipViewManager {
	
	
	constructor(document, clipViewClass) {
		this._document = document;
		this._clipViewClass = clipViewClass;
		this._clips = [];
		this._initClipViews();
	}
	
	
	_initClipViews() {
		this._clipViews = new Array(this.clips.length);
		this._clipViews.fill(null);
	}
	
	
	get document() {
		return this._document;
	}
	
	
	set document(document) {
		this._document = document;
		this._initClipViews();
	}
	
	
	get clipViewClass() {
		return this._clipViewClass;
	}
	
	
	set clipViewClass(clipViewClass) {
		this._clipViewClass = clipViewClass;
		this._initClipViews();
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	set clips(clips) {
		this._clips = clips;
		this._initClipViews();
	}
	
	
	getClipView(i) {
		
		if (this._clipViews[i] === null)
			this._clipViews[i] =
				new this.clipViewClass(this.clips[i], this.document);
		
		return this._clipViews[i];
		
	}
	
	
}
