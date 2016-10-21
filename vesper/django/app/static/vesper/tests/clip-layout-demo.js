'use strict'


const numClips = 300;
const minClipSpan = .1;        // seconds
const maxClipSpan = .4;        // seconds


const nonuniformNonresizingSettings = {
		
	page: {
		size: 70               // clips
	},
	
    clipView: {
    	timeScale: 800,        // pixels per second
    	height: 60,            // pixels
    	xSpacing: 20,         // pixels
    	ySpacing: 20          // pixels
    }
	
}


const nonuniformResizingSettings = {
		
	page: {
		width: 2.5,            // seconds
		height: 10             // rows
	},
	
	clipView: {
		xSpacing: 1,           // percent of display width
		ySpacing: 1            // percent of display width
	}
	
}


let clips = null;
let pageDiv = null;
let pageNum = null;
let layout = null;
let clipViewManager = null;


function onLoad() {
	
	clips = createClips(numClips, minClipSpan, maxClipSpan);
	
	const checkbox = document.getElementById('checkbox');
	checkbox.onchange = onCheckboxChange;
	
	pageDiv = document.getElementById('page');
	
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
	
	const checkbox = document.getElementById('checkbox');
	
	if (checkbox.checked)
		layout = new NonuniformResizingClipViewsLayout(
			nonuniformResizingSettings);
	else
		layout = new NonuniformNonresizingClipViewsLayout(
			nonuniformNonresizingSettings);
	
	layout.clips = clips;
	
	clipViewManager = new LazyClipViewManager(document, DemoClipView);
	clipViewManager.clips = clips;
	
	layout.layOutClips(pageDiv, pageNum, clipViewManager);
	
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
	layout.handlePageResize(pageDiv, pageNum, clipViewManager);
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
		
	}
	
	
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
