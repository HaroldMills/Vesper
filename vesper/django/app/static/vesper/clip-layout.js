'use strict'


/*

Clip collection view layout settings by layout type:

    Uniform Nonresizing Clip Views
    
        page:
            size: clips
            
        clip_view:
            width: pixels
            height: pixels
            x_spacing: pixels
            y_spacing: pixels
            selection_outline_width: pixels
            duration: seconds
            

    Uniform Resizing Clip Views
    
        page:
            width: columns
            height: rows
            
        clip_view:
            x_spacing: percent of page width
            y_spacing: percent of page width
            selection_outline_width: pixels
            duration: seconds
        
 
    Nonuniform Nonresizing Clip Views
    
        page:
            size: clips
            
        clip_view:
            time_scale: pixels per second
            height: pixels
            x_spacing: pixels
            y_spacing: pixels
            selection_outline_width: pixels
            initial_padding: seconds
            final_padding: seconds
        
        
    Nonuniform Resizing Clip Views
    
        page:
            width: seconds
            height: rows
            
        clip_view:
            x_spacing: percent of page width
            y_spacing: percent of page width
            selection_outline_width: pixels
            initial_padding: seconds
            final_padding: seconds

*/


// /** Layout that displays uniform, nonresizing clip views. */
// class UniformNonresizingClipViewsLayout { }


// /** Layout that displays uniform, resizing clip views. */
// class UniformResizingClipViewsLayout { }


/** Layout that displays nonuniform, nonresizing clip views. */
class NonuniformNonresizingClipViewsLayout {
	
	
	/**
	 * Creates a layout with the specified settings.
	 * 
	 * Settings:
	 * 
	 *     page:
     *         size: clips
     *         
     *     clip_view:
     *         time_scale: pixels per second
     *         height: pixels
     *         x_spacing: pixels
     *         y_spacing: pixels
     *         selection_outline_width: pixels
     *         initial_padding: seconds
     *         final_padding: seconds
     */
	constructor(div, clipViews, settings) {
		this._div = div;
		this._clipViews = clipViews;
		this._settings = settings;
		this._paginate();
	}
	
	
	get div() {
		return this._div;
	}
	
	
    get clipViews() {
    	return this._clipViews;
    }
    
    
    get settings() {
    	return this._settings;
    }
    
    
    set settings(settings) {
    	this._settings = settings;
    	this._paginate();
    }
    
    
	/**
	 * Assigns clips to pages.
	 */
	_paginate() {
		
		const pg = this.settings.page;
		
		const numClips = this.clipViews.length;
		const numPages = Math.ceil(numClips / pg.size);
		
		const pageBounds = new Array(numPages);
		let startIndex = 0;
		for (let i = 0; i < numPages; i++) {
			const pageSize = Math.min(pg.size, numClips - startIndex);
			pageBounds[i] = [startIndex, startIndex + pageSize];
			startIndex += pageSize;
		}
		
		this._numPages = numPages;
		this._pageIndexBounds = pageBounds;
		
	}
	
	
	get numPages() {
		return this._numPages;
	}
	
	
	getPageIndexBounds(pageNum) {
		return this._pageIndexBounds[pageNum];
	}
	
	
	layOutClipViews(pageNum) {
		
		const pageDiv = this.div;
		
		_removeChildren(pageDiv);
		
		const cv = this.settings.clipView;
		
		const y_margin = cv.ySpacing / 2;
		const x_margin = cv.xSpacing / 2;
		const margin = y_margin + 'px ' + x_margin + 'px ';

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
		const height = cv.height + 'px';
		
		for (let i = startIndex; i < endIndex; i++) {
			
			const clipView = this.clipViews[i];
			const clipDiv = clipView.div;
			const width = clipView.duration * cv.timeScale + 'px';
			
			// Style clip div. It is important to set values for
			// pretty much all of the sizing properties here since
			// we reuse clip divs across layouts.
		    clipDiv.className = 'clip';
		    clipDiv.style.position = 'relative';
		    clipDiv.style.minWidth = width;
		    clipDiv.style.width = width;
		    clipDiv.style.height = height;
		    clipDiv.style.margin = margin;
		    
		    // TODO: Draw selection outlines properly.
		    if (i === 2) {
		    	clipDiv.style.outlineWidth = '5px';
		    	clipDiv.style.outlineStyle = 'solid';
		    	clipDiv.style.outlineColor = 'orange';
		    }
			
			pageDiv.appendChild(clipDiv);
			
		}
		
		this._renderClipViews(pageNum);
		
	}
	
	
	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		for (let i = startIndex; i < endIndex; i++)
			this.clipViews[i].render();
		
	}
	
	
	onResize(pageNum) {
		// For this layout type resizes are handled by the flexbox layout.
	}
	
	
}


/** Layout that displays nonuniform, resizing clip views. */
class NonuniformResizingClipViewsLayout {
	
	
	/**
	 * Creates a layout for the specified clips.
	 * 
	 * Settings:
	 * 
	 *     page:
     *         width: seconds
     *         height: rows
     *         
     *     clip_view:
     *         x_spacing: percent of page width
     *         y_spacing: percent of page width
     *         selection_outline_width: pixels
     *         initial_padding: seconds
     *         final_padding: seconds
	 */
	constructor(div, clipViews, settings) {
		this._div = div;
		this._clipViews = clipViews;
		this._settings = settings;
		this._paginate();
	}
	
	
	get div() {
		return this._div;
	}
	
	
    get clipViews() {
    	return this._clipViews;
    }
    
    
    get settings() {
    	return this._settings;
    }
    
    
    set settings(settings) {
    	this._settings = settings;
    	this._paginate();
    }
    
    
	/**
	 * Assigns clips to pages and rows.
	 */
	_paginate() {
		
		const pg = this.settings.page;
		const cv = this.settings.clipView;
		const clipViews = this.clipViews;
		
		if (clipViews.length === 0) {
			
			this._pages = [];
			
		} else {
			
			const xSpacing = cv.xSpacing;
			const maxRowWidth = 100. - xSpacing;
			const widthFactor = 100. / pg.width;
			
			const pages = [];
			let page = [0];
		    let rowWidth = widthFactor * clipViews[0].duration + xSpacing;
		    
		    let i = 1;
		    
			for ( ; i < clipViews.length; i++) {
				
				const width = widthFactor * clipViews[i].duration + xSpacing;
				
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
					
					if (page.length > pg.height) {
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
	
	
	layOutClipViews(pageNum) {
		
		const pageDiv = this.div;
		
		_removeChildren(pageDiv);
		
		const pg = this.settings.page;
		const cv = this.settings.clipView;

		const xMargin = _toCssPercent(cv.xSpacing / 2.);
		const yMargin = _toCssPercent(cv.ySpacing / 2.);
		const margin = xMargin + ' ' + yMargin;
		
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
		const clipViews = this.clipViews;
				
		for (let i = 0; i < pg.height; i++) {
			
			// Create row div. We create a separate div for each row so
			// we can lay out clip views whose durations exceed the display
			// width in a special way. See below for details.
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
					
					const clipView = clipViews[j];
					
					const width = 100 * (clipView.duration / pg.width);
					
					if (rowLength === 1 && width > 100) {
						// row contains a single clip view and that clip view
						// is wider than the display
						
						// In this case we change the row div's justify-content
						// CSS property from center to flex-start so the clip
						// starts at the left edge of the display and the user
						// can scroll right to see the portion that doesn't
						// fit. If we leave the clip centered there will be
						// no way for the user to see the first part of it,
						// which will be off the left side of the display.
						rowDiv.style.justifyContent = 'flex-start';
						
					}
					
					
					// Style clip div. It is important to set values for
					// pretty much all of the sizing properties here since
					// we reuse clip divs across layouts.
					const clipDiv = clipView.div;
				    clipDiv.className = 'clip';
				    clipDiv.style.position = 'relative';
				    clipDiv.style.flex = '0 0 ' + _toCssPercent(width);
				    clipDiv.style.minWidth = 'auto';
				    clipDiv.style.width = 'auto';
				    clipDiv.style.height = 'auto';
				    clipDiv.style.margin = margin
				    
				    // TODO: Draw selection outlines properly.
				    if (j === 2) {
				    	clipDiv.style.outlineWidth = '5px';
				    	clipDiv.style.outlineStyle = 'solid';
				    	clipDiv.style.outlineColor = 'orange';
				    }
				    
					rowDiv.appendChild(clipDiv);
					
				}
				
			}
						
			pageDiv.appendChild(rowDiv);
			
		}
		
		this._renderClipViews(pageNum);
		
	}
	

	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {
		
		const [startIndex, endIndex] = this.getPageIndexBounds(pageNum);
		
		const clipViews = this.clipViews;
		for (let i = startIndex; i < endIndex; i++)
			clipViews[i].render();
		
	}
	
	
	onResize(pageNum) {
		this._renderClipViews(pageNum);
	}
	
	
}


function _removeChildren(div) {
    while (div.firstChild)
    	div.removeChild(div.firstChild);
}


function _toCssPercent(x) {
	return x.toFixed(2) + '%';
}
