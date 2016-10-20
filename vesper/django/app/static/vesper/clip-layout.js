'use strict'


/*

Terms:
* collection view - displays a collection of items
* collection view layout - partitions items into pages and lays out pages
* item - has width and height in item units
* cell - renders one item into a div reserved exclusively for that item

Classes:
* Clip
* ClipSpectrogramCell
* UniformResizingCellsLayout
* UniformNonresizingCellsLayout
* NonuniformResizingCellsLayout
* NonuniformNonresizingCellsLayout

Collection view layout options
    uniform or nonuniform width cells
    resizing or nonresizing cells

Clip collection view settings by cell type:

    Uniform Nonresizing
    
        // layout settings
        page_size: clips
        cell_width: pixels
        cell_height: pixels
        cell_x_spacing: pixels
        cell_y_spacing: pixels
        
        // cell settings
        cell_duration: seconds
        cell_start_freq: hertz
        cell_end_freq: hertz


    Uniform Resizing
    
        // layout settings
        page_width: columns
        page_height: rows
        cell_x_spacing: percent of page width
        cell_y_spacing: percent of page width
        
        // cell settings
        cell_duration: seconds
        cell_start_freq: hertz
        cell_end_freq: hertz
 
 
    Nonuniform Nonresizing
    
        // layout settings
        page_size: clips
        cell_x_scale: pixels per second
        cell_height: pixels
        cell_x_spacing: pixels
        cell_y_spacing: pixels
        initial_clip_padding: seconds
        final_clip_padding: seconds
        
        // cell settings
        cell_start_freq: hertz
        cell_end_freq: hertz
        
        
    Nonuniform Resizing
    
        // layout settings
        page_width: seconds
        page_height: rows
        cell_x_spacing: percent of page width
        cell_y_spacing: percent of page width
        initial_clip_padding: seconds
        final_clip_padding: seconds
        
        // cell settings
        cell_start_freq: hertz
        cell_end_freq: hertz

*/


// /** Layout for displaying clips in uniform, nonresizing cells. */
// class UniformNonresizingCellsLayout { }


// /** Layout for displaying clips in uniform, resizing cells. */
// class UniformResizingCellsLayout { }


/** Layout for displaying clips in nonuniform, nonresizing cells. */
class NonuniformNonresizingCellsLayout {
	
	
	/**
	 * Creates a layout with the specified settings.
	 * 
	 * @param {Object} settings - the settings for the layout.
	 * 
	 * Settings properties are:
	 *     pageSize {number} - the page size in cells.
	 *     cellWidthScale {number} - the cell width scale in pixels per second.
	 *     cellHeight {number} - the cell height in pixels.
	 *     cellSpacing {number} - the cell spacing in pixels.
	 */
	constructor(settings) {
		this._settings = settings;
		this._clips = [];
		this._paginate();
	}
	
	
    get settings() {
    	return this._settings;
    }
    
    
    set settings(settings) {
    	this._settings = settings;
    	this._paginate();
    }
    
    
    get clips() {
    	return this._clips;
    }
    
    
    set clips(clips) {
    	this._clips = clips;
    	this._paginate();
    }
    
    
	/**
	 * Assigns clips to pages.
	 */
	_paginate() {
		
		const s = this.settings;
		
		const numClips = this.clips.length;
		const numPages = Math.ceil(numClips / s.pageSize);
		
		const pageBounds = new Array(numPages);
		let startIndex = 0;
		for (let i = 0; i < numPages; i++) {
			const pageSize = Math.min(s.pageSize, numClips - startIndex);
			pageBounds[i] = [startIndex, startIndex + pageSize];
			startIndex += pageSize;
		}
		
		this.numPages = numPages;
		this._pageIndexBounds = pageBounds;
		
	}
	
	
	getPageIndexBounds(pageNum) {
		return this._pageIndexBounds[pageNum];
	}
	
	
	layOutClips(pageDiv, pageNum, clipCellManager) {
		
		removeChildren(pageDiv);
		
		const s = this.settings;
		const margin = s.cellSpacing / 2 + 'px';

		// Style page div. It is important to set values for pretty much
		// all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		pageDiv.className = 'page';
		pageDiv.style.display = 'flex';
		pageDiv.style.flexDirection = 'row';
		pageDiv.style.flexWrap = 'wrap';
		pageDiv.style.flex = '1 1 auto';
		pageDiv.style.justifyContent = 'center';
		pageDiv.style.alignContent = 'flex-start';
		pageDiv.style.alignItems = 'flex-end';
		pageDiv.style.width = 'auto';
		pageDiv.style.margin = margin;
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		const height = s.cellHeight + 'px';
		
		for (let i = startIndex; i < endIndex; i++) {
			
			const span = this.clips[i].span;
			const width = span * s.cellWidthScale + 'px';
			
			// Style cell div.
			const cellDiv = clipCellManager.getCell(i).div;
		    cellDiv.className = 'cell';
		    cellDiv.style.position = 'relative';
		    cellDiv.style.minWidth = width;
		    cellDiv.style.width = width;
		    cellDiv.style.height = height;
		    cellDiv.style.margin = margin;
		    
		    // TODO: Draw selection outlines properly.
		    if (i === 2) {
		    	cellDiv.style.outlineWidth = '5px';
		    	cellDiv.style.outlineStyle = 'solid';
		    	cellDiv.style.outlineColor = 'orange';
		    }
			
			pageDiv.appendChild(cellDiv);
			
		}
		
		this._renderCells(pageNum, clipCellManager);
		
	}
	
	
	_renderCells(pageNum, clipCellManager) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		for (let i = startIndex; i < endIndex; i++)
			clipCellManager.getCell(i).render();
		
	}
	
	
	handlePageResize(pageDiv, pageNum, clipCellManager) {
		// For this layout resizing is handled by the flexbox layout.
	}
	
	
}


/** Layout for displaying clips in nonuniform, resizing cells. */
class NonuniformResizingCellsLayout {
	
	
	/**
	 * Creates a layout for the specified clips.
	 * 
	 * @param {Object} settings - the settings for the layout.
	 * 
	 * 
	 * Settings properties are:
	 *     pageWidth {number} - the page width in seconds.
	 *     pageHeight {number} - the page height in rows.
	 *     cellSpacing {number} - the cell spacing as a percent of page width.
	 */
	constructor(settings) {
		this._settings = settings;
		this.clips = [];
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	set clips(clips) {
		this._clips = clips;
		this._paginate();
	}
	
	
	/**
	 * Assigns clips to pages and rows.
	 */
	_paginate() {
		
		const s = this.settings;
		const clips = this.clips;
		
		if (clips.length == 0) {
			
			this._pages = [];
			
		} else {
			
			const cellSpacing = s.cellSpacing;
			const maxRowWidth = 100. - cellSpacing;
			const widthFactor = 100. / s.pageWidth;
			
			const pages = [];
			let page = [0];
		    let rowWidth = widthFactor * clips[0].span + cellSpacing;
		    
		    let i = 1;
		    
			for ( ; i < clips.length; i++) {
				
				const width = widthFactor * clips[i].span + cellSpacing;
				
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
					
					if (page.length > s.pageHeight) {
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
	
	
	layOutClips(pageDiv, pageNum, clipCellManager) {
		
		removeChildren(pageDiv);
		
		const s = this.settings;
		const margin = toCssPercent(s.cellSpacing / 2.);
		
		// Style the page div. It is important to set values for pretty
		// much all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		pageDiv.className = 'page';
		pageDiv.style.display = 'flex';
		pageDiv.style.flexDirection = 'column';
		pageDiv.style.flexWrap = 'nowrap';
		pageDiv.style.flex = '1 1 auto';
		pageDiv.style.justifyContent = 'flex-start';
		pageDiv.style.alignContent = 'stretch';
		pageDiv.style.alignItems = 'stretch';
		pageDiv.style.width = 'auto';
		pageDiv.style.margin = margin;

		const rowStartIndices = this._pages[pageNum];
		
		for (let i = 0; i < s.pageHeight; i++) {
			
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
					
					const cell = clipCellManager.getCell(j);
					
					const clip = this.clips[j];
					const width = 100 * (clip.span / s.pageWidth);
					
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
					
					
					// Style cell div.
					const cellDiv = cell.div;
				    cellDiv.className = 'cell';
				    cellDiv.style.flex = '0 0 ' + toCssPercent(width);
				    cellDiv.style.position = 'relative';
				    cellDiv.style.margin = margin
				    
				    // TODO: Draw selection outlines properly.
				    if (j == 2) {
				    	cellDiv.style.outlineWidth = '5px';
				    	cellDiv.style.outlineStyle = 'solid';
				    	cellDiv.style.outlineColor = 'orange';
				    }
				    
				    
					rowDiv.appendChild(cellDiv);
					
				}
				
			}
						
			pageDiv.appendChild(rowDiv);
			
		}
		
		this._renderCells(pageNum, clipCellManager);
		
	}
	

	_renderCells(pageNum, clipCellManager) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		for (let i = startIndex; i < endIndex; i++)
			clipCellManager.getCell(i).render();
		
	}
	
	
	handlePageResize(pageDiv, pageNum, clipCellManager) {
		this._renderCells(pageNum, clipCellManager);
	}
	
	
}


function removeChildren(div) {
    while (div.firstChild)
    	div.removeChild(div.firstChild);
}


function toCssPercent(x) {
	return x.toFixed(2) + '%';
}
