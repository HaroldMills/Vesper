'use strict'


class LazyClipCellManager {
	
	
	constructor(document, cellClass) {
		this._document = document;
		this._cellClass = cellClass;
		this._clips = [];
		this._initCells();
	}
	
	
	_initCells() {
		this._cells = new Array(this.clips.length);
		this._cells.fill(null);
	}
	
	
	get document() {
		return this._document;
	}
	
	
	set document(document) {
		this._document = document;
		this._initCells();
	}
	
	
	get cellClass() {
		return this._cellClass;
	}
	
	
	set cellClass(cellClass) {
		this._cellClass = cellClass;
		this._initCells();
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	set clips(clips) {
		this._clips = clips;
		this._initCells();
	}
	
	
	getCell(i) {
		
		if (this._cells[i] === null)
			this._cells[i] = new this.cellClass(this.clips[i], this.document);
		
		return this._cells[i];
		
	}
	
	
}
