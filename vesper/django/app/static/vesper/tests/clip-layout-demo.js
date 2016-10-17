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
let layout = null;
let pageNum = null;


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

		clips[i] = {span: span};
		
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
			clips, clipsDiv, s.displayWidth, s.displayHeight, s.clipSpacing);
		
	} else {
		
		const s = nonresizableVariableWidthSettings;
		layout = new NonresizingVariableWidthClipLayout(
			clips, clipsDiv, s.pageSize, s.clipWidthScale, s.clipHeight,
			s.clipSpacing);
		
    }
	
	layout.layOutClips(pageNum);
	
	updateTitle();
	
}


function updateTitle() {
	const title = document.getElementById('title');
	const [startIndex, endIndex] = layout.getPageIndexBounds(pageNum);
	const numClips = clips.length;
	title.innerHTML =
		`Clips ${startIndex + 1} to ${endIndex} of ${numClips}`;
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


window.onload = onLoad;
document.onkeypress = onKeyPress;
