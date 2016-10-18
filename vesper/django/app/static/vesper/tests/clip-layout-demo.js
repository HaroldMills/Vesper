"use strict"


const numClips = 300;
const minClipSpan = .1;        // seconds
const maxClipSpan = .4;        // seconds


const nonresizableVariableWidthSettings = {
	pageSize: 70,              // clips
	clipWidthScale: 800,       // pixels per second
	clipHeight: 60,            // pixels
	clipSpacing: 20            // pixels
}

const resizableVariableWidthSettings = {
	displayWidth: 2.5,         // seconds
	displayHeight: 10,         // rows
	clipSpacing: 1             // percent of display width
}


let clips = null;
let clipsDiv = null;
let pageNum = null;
let layout = null;
let clipViewManager = null;


function onLoad() {
	
	clips = createClips(numClips, minClipSpan, maxClipSpan);
	
	const checkbox = document.getElementById('resizable-checkbox');
	checkbox.onchange = onCheckboxChange;
	
	clipsDiv = document.getElementById('clips');
	
	pageNum = 0;
	
	updateDisplay();
	
}
	
	
function createClips(numClips, minSpan, maxSpan) {
	
	const delta = maxSpan - minSpan;
	const clips = new Array(numClips);
	
	for (let i = 0; i < numClips; i++) {
		
		let span = minSpan + delta * Math.random();
		
		if (i === 5)
			span = 3;

		clips[i] = {
			index: i,
			span: span
		};
		
	}
	
	return clips;
	
}


function onCheckboxChange() {
	pageNum = 0;
	updateDisplay();
}


function updateDisplay() {
	
	const checkbox = document.getElementById('resizable-checkbox');
	
	if (checkbox.checked) {
		
		const s = resizableVariableWidthSettings;
		layout = new ResizingVariableWidthClipLayout(
			clips, s.displayWidth, s.displayHeight, s.clipSpacing);
		
	} else {
		
		const s = nonresizableVariableWidthSettings;
		layout = new NonresizingVariableWidthClipLayout(
			clips, s.pageSize, s.clipWidthScale, s.clipHeight, s.clipSpacing);
		
    }
	
	clipViewManager = new DemoClipViewManager(clips, document, DemoClipView);
	
	layout.layOutClips(clipsDiv, pageNum, clipViewManager);
	
	updateTitle();
	
}


function updateTitle() {
	const title = document.getElementById('title');
	const [startIndex, endIndex] = layout.getPageIndexBounds(pageNum);
	const numClips = clips.length;
	title.innerHTML =
		`Clips ${startIndex + 1} to ${endIndex} of ${numClips}`;
}


function onResize() {
	layout.handleClipsViewResize(clipsDiv, pageNum, clipViewManager);
}


function onKeyPress(e) {
	
	if (e.key === '>') {
		
		if (pageNum < layout.numPages - 1) {
			pageNum += 1;
			updateDisplay();
		}
		
	} else if (e.key === '<') {
		
	    if (pageNum > 0) {
	    	pageNum -= 1;
	    	updateDisplay();
	    }
	    
	}
	
}


class DemoClipView {
	
	
	constructor(clip, document) {
		this.clip = clip;
		this.document = document;
		this.div = this._createDiv();
	}
	
	
	_createDiv() {
		
		const document = this.document;
		
		const div = document.createElement('div');
		
		const canvas = document.createElement('canvas');
		canvas.className = 'clip-canvas';
		div.appendChild(canvas);
		this._canvas = canvas;
		
	    const h = document.createElement('h3');
	    h.className = 'clip-label';
	    h.innerHTML = (this.clip.index + 1).toString();
	    div.appendChild(h);
	    
	    return div;

	}
	
	
	render() {
		
		const div = this.div;
		
		const canvas = this._canvas;
		const width = canvas.clientWidth;
		const height = canvas.clientHeight;
		
		canvas.width = width;
		canvas.height = height;
		
		const size = 20;
		const left = (width - size) / 2;
		const top = (height - size) / 2;
		const right = (width + size) / 2;
		const bottom = (height + size) / 2;

		const context = canvas.getContext('2d');
		context.beginPath();
		context.moveTo(left, top);
		context.lineTo(right, bottom);
		context.moveTo(right, top);
		context.lineTo(left, bottom);
		context.lineWidth = 2;
		context.stroke()
		
		console.log(
			'render', this.clip.index, div.clientWidth, div.clientHeight);
		
	}
	
	
}


class DemoClipViewManager {
	
	
	constructor(clips, document, clipViewClass) {
		
		this.clips = clips;
		this._document = document;
		this.clipViewClass = clipViewClass;
		
		this._views = new Array(clips.length);
		this._views.fill(null);
		
	}
	
	
	get document() {
		return this._document;
	}
	
	
	getClipView(i) {
		
		if (this._views[i] === null)
			this._views[i] =
				new this.clipViewClass(this.clips[i], this.document);
		
		return this._views[i];
		
	}
	
	
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
