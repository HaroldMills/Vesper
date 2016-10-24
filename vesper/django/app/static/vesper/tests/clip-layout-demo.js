'use strict'


const numClips = 300;
const minClipSpan = .1;        // seconds
const maxClipSpan = .4;        // seconds


const nonuniformNonresizingSettings = {
		
	layoutType: 'Nonuniform Nonresizing Clip Views',
	
	layout: {
		
		page: {
			size: 70               // clips
		},
		
	    clipView: {
	    	timeScale: 800,        // pixels per second
	    	height: 60,            // pixels
	    	xSpacing: 20,          // pixels
	    	ySpacing: 20           // pixels
	    }
		
	},
	
	clipViewType: 'Demo',
	
	clipView: {}
	
}


const nonuniformResizingSettings = {
		
	layoutType: 'Nonuniform Resizing Clip Views',
	
	layout: {
		
		page: {
			width: 2.5,            // seconds
			height: 10             // rows
		},
		
		clipView: {
			xSpacing: 1,           // percent of display width
			ySpacing: 1            // percent of display width
		}
		
	},
	
	clipViewType: 'Demo',
	
	clipView: {}
	
}


let clipCollectionView = null;


function onLoad() {
	
	const checkbox = document.getElementById('checkbox');
	checkbox.checked = false;
	checkbox.onchange = onCheckboxChange;
	
	const pageDiv = document.getElementById('page');
	const clips = createClips(numClips, minClipSpan, maxClipSpan);
	const settings = getSettings();
	clipCollectionView = new ClipCollectionView(pageDiv, clips, settings);
	
	updateTitle();
	
}
	
	
function onCheckboxChange() {
	clipCollectionView.settings = getSettings();
	updateTitle();
}


function getSettings() {
	const checkbox = document.getElementById('checkbox');
	const checked = checkbox.checked;
	return checked ? nonuniformResizingSettings : nonuniformNonresizingSettings;
	
}


function updateTitle() {
	const title = document.getElementById('title');
	const view = clipCollectionView;
	const [startIndex, endIndex] = view.getPageIndexBounds(view.pageNum);
	const numClips = view.clips.length;
	title.innerHTML = `Clips ${startIndex + 1} to ${endIndex} of ${numClips}`;
}


function createClips(numClips, minSpan, maxSpan) {
	
	const delta = maxSpan - minSpan;
	const clips = new Array(numClips);
	
	for (let i = 0; i < numClips; i++) {
		
		let span = minSpan + delta * Math.random();
		
//		if (i === 5)
//			span = 3;

		clips[i] = {
			index: i,
			span: span
		};
		
	}
	
	return clips;
	
}


function onResize() {
	clipCollectionView.onResize();
}


function onKeyPress(e) {
	
	const view = clipCollectionView;
	const pageNum = view.pageNum;
	
	if (e.key === '>') {
		
		if (pageNum < view.numPages - 1)
			setPageNum(pageNum + 1);
		
	} else if (e.key === '<') {
		
	    if (pageNum > 0)
	    	setPageNum(pageNum - 1);
	    
	}
	
}


function setPageNum(pageNum) {
	clipCollectionView.pageNum = pageNum;
	updateTitle();
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
