'use strict'


/** Class that lays out clips in nonresizable, variable width cells. */
class NonresizingVariableWidthClipLayout {
	
	
	/**
	 * Creates a layout for the specified clips.
	 * 
	 * @param {Clip[]} clips - the clips for which to create a layout.
	 * @param {number} pageSize - the page size in clips.
	 * @param {number} clipWidthScale - the clip width scale in pixels per second.
	 * @param {number} clipHeight - the clip height in pixels.
	 * @param {number} clipSpacing - the clip spacing in pixels.
	 */
	constructor(clips, pageSize, clipWidthScale, clipHeight, clipSpacing) {
		this.clips = clips;
		this.clipsDiv = clipsDiv;
		this.pageSize = pageSize;
		this.clipWidthScale = clipWidthScale;
		this.clipHeight = clipHeight;
		this.clipSpacing = clipSpacing;
		this._paginate();
	}
	
	
	/**
	 * Assigns clips to pages.
	 */
	_paginate() {
		
		const numClips = this.clips.length;
		const maxPageSize = this.pageSize;
		const numPages = Math.ceil(numClips / maxPageSize);
		
		const pageBounds = new Array(numPages);
		let startIndex = 0;
		for (let i = 0; i < numPages; i++) {
			const pageSize = Math.min(maxPageSize, numClips - startIndex);
			pageBounds[i] = [startIndex, startIndex + pageSize];
			startIndex += pageSize;
		}
		
		this.numPages = numPages;
		this._pageIndexBounds = pageBounds;
		
	}
	
	
	getPageIndexBounds(pageNum) {
		return this._pageIndexBounds[pageNum];
	}
	
	
	layOutClips(clipsDiv, pageNum, clipViewManager) {
		
		removeChildren(clipsDiv);
		
		const margin = this.clipSpacing / 2 + 'px';

		// Style the clips div. It is important to set values for pretty
		// much all of the flexbox properties here since we allow switching
		// between different layout policies for the same clips div.
		clipsDiv.className = 'clips';
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'row';
		clipsDiv.style.flexWrap = 'wrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'center';
		clipsDiv.style.alignContent = 'flex-start';
		clipsDiv.style.alignItems = 'flex-end';
		clipsDiv.style.width = 'auto';
		clipsDiv.style.margin = margin;
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		const height = this.clipHeight + 'px';
		
		for (let i = startIndex; i < endIndex; i++) {
			
			const span = this.clips[i].span;
			const width = span * this.clipWidthScale + 'px';
			
			const div = clipViewManager.getClipView(i).div;
		    div.className = 'clip';
		    div.style.position = 'relative';
		    div.style.minWidth = width;
		    div.style.width = width;
		    div.style.height = height;
		    div.style.margin = margin;
		    
		    // TODO: Draw selection outlines properly.
		    if (i === 2) {
		    	div.style.outlineWidth = '5px';
		    	div.style.outlineStyle = 'solid';
		    	div.style.outlineColor = 'orange';
		    }
			
			clipsDiv.appendChild(div);
			
		}
		
		this._renderViews(pageNum, clipViewManager);
		
	}
	
	
	_renderViews(pageNum, clipViewManager) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		for (let i = startIndex; i < endIndex; i++) {
			const view = clipViewManager.getClipView(i);
			view.render();
		}
		
	}
	
	
	handleClipsViewResize(clipsDiv, pageNum, clipViewManager) {
		console.log('handleClipsViewResize');
	}
	
	
}


/** Class that lays out clips in resizable, variable width cells. */
class ResizingVariableWidthClipLayout {
	
	
	/**
	 * Creates a layout for the specified clips.
	 * 
	 * @param {Clip[]} clips - the clips for which to create a layout.
	 * @param {number} displayWidth - the display width in seconds.
	 * @param {number} displayHeight - the display height in rows.
	 * @param {number} clipSpacing - the clip spacing as percent of display width.
	 */
	constructor(clips, displayWidth, displayHeight, clipSpacing) {
		this.clips = clips;
		this.displayWidth = displayWidth;
		this.displayHeight = displayHeight;
		this.clipSpacing = clipSpacing;
		this._paginate();
	}
	
	
	/**
	 * Assigns clips to pages and rows.
	 */
	_paginate() {
		
		const clips = this.clips;
		
		if (clips.length == 0) {
			
			this._pages = [];
			
		} else {
			
			const clipSpacing = this.clipSpacing;
			const maxRowWidth = 100. - clipSpacing;
			const widthFactor = 100. / this.displayWidth;
			
			const pages = [];
			let page = [0];
		    let rowWidth = widthFactor * clips[0].span + clipSpacing;
		    
		    let i = 1;
		    
			for ( ; i < clips.length; i++) {
				
				const width = widthFactor * clips[i].span + clipSpacing;
				
				if (rowWidth + width <= maxRowWidth) {
					// clip fits on current row
					
					rowWidth += width;
					
				} else {
					// clip will start new row
					
					// We always append the clip index to the current
					// page, even if the clip will start a new page,
					// so that we can obtain an end index for any row
					// i of a page, even the last row, as page[i + 1],
					// and the length of row i as page[i + 1] - page[i].
					page.push(i);
					
					if (page.length > this.displayHeight) {
						// new row will be on new page
						
						pages.push(page);
						page = [i];
						
					}
					
					rowWidth = width;
					
				}
				
			}
			
			// Wrap up last page.
			page.push(i);
			pages.push(page);
			
			this._pages = pages;
			
		}

	}
	
	
	get numPages() {
		return this._pages.length;
	}
	
	
	getPageIndexBounds(pageNum) {
		const page = this._pages[pageNum];
		return [page[0], page[page.length - 1]];
	}
	
	
	layOutClips(clipsDiv, pageNum, clipViewManager) {
		
		removeChildren(clipsDiv);
		
		const margin = toCssPercent(this.clipSpacing / 2.);
		
		// Style the clips div. It is important to set values for pretty
		// much all of the flexbox properties here since we allow switching
		// between different layout policies for the same clips div.
		clipsDiv.className = 'clips';
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'column';
		clipsDiv.style.flexWrap = 'nowrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'flex-start';
		clipsDiv.style.alignContent = 'stretch';
		clipsDiv.style.alignItems = 'stretch';
		clipsDiv.style.width = 'auto';
		clipsDiv.style.margin = margin;

		const rowStartIndices = this._pages[pageNum];
		
		for (let i = 0; i < this.displayHeight; i++) {
			
			// Create row div. We create a separate div for each row so
			// we can lay out clips whose spans exceed the display width
			// in a special way. See below.
			const rowDiv = document.createElement('div');
			rowDiv.className = 'row';
			rowDiv.style.display = 'flex';
			rowDiv.style.flexDirection = 'row';
			rowDiv.style.flex = '1 1 1px';
			rowDiv.style.justifyContent = 'center';
			
			if (i < rowStartIndices.length) {
				// row contains clips
				
				const startIndex = rowStartIndices[i];
				const endIndex = rowStartIndices[i + 1];
				const rowLength = endIndex - startIndex
				
				for (let j = startIndex; j < endIndex; j++) {
					
					// Get clip view.
					const view = clipViewManager.getClipView(j);
					
					const clip = this.clips[j];
					const width = 100 * (clip.span / this.displayWidth);
					
					if (rowLength == 1 && width > 100) {
						// row contains a single clip and that clip is
						// wider than the display
						
						// In this case we change the row div's justify-content
						// CSS property from center to flex-start so the clip
						// starts at the left edge of the display and the user
						// can scroll right to see the portion that doesn't
						// fit. If we leave the clip centered there will be
						// no way for the user to see the first part of it,
						// which will be off the left side of the display.
						rowDiv.style.justifyContent = 'flex-start';
						
					}
					
					
					// Style view div.
					
					const div = view.div;
				    div.className = 'clip';
				    div.style.flex = '0 0 ' + toCssPercent(width);
				    div.style.position = 'relative';
				    div.style.margin = margin
				    
				    // TODO: Draw selection outlines properly.
				    if (j == 2) {
				    	div.style.outlineWidth = '5px';
				    	div.style.outlineStyle = 'solid';
				    	div.style.outlineColor = 'orange';
				    }
				    
				    
					rowDiv.appendChild(div);
					
				}
				
			}
						
			clipsDiv.appendChild(rowDiv);
			
		}
		
		this._renderViews(pageNum, clipViewManager);
		
	}
	

	_renderViews(pageNum, clipViewManager) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		for (let i = startIndex; i < endIndex; i++) {
			const view = clipViewManager.getClipView(i);
			view.render();
		}
		
	}
	
	
	handleClipsViewResize(clipsDiv, pageNum, clipViewManager) {
		this._renderViews(pageNum, clipViewManager);
	}
	
	
}


function removeChildren(div) {
    while (div.firstChild)
    	div.removeChild(div.firstChild);
}


function toCssPercent(x) {
	return x.toFixed(2) + '%';
}
