'use strict'


/*

settings:

    layout_type: Nonuniform Resizing Clip Views
    
    layout:
    
        page:
            width: seconds
            height: rows
            
        clip_view:
            x_spacing: percent of page width
            y_spacing: percent of page width
            selection_outline_width: pixels
            initial_padding: seconds
            final_padding: seconds
            
        clip_label:
		    visible: true
		    location: bottom
		    color: white
		    size: .8
		    classification_included: true
		    start_time_included: false
		    hidden_classification_prefixes: ["Call."]
    
    clip_view_type: Spectrogram
    
    clip_view:
    
        frequency_axis:
            start: 5000
            end: 11000
	    
	    spectrogram:
		    window_size: 100
		    hop_size: 25
		    dft_size: 256
		    reference_power: 1
		    low_power: 10
		    high_power: 100
		    smoothing_enabled: true
	    
	    colors:
	        spectrogram_colormap: gray


For nonuniform clip view layouts, the time axis initial and final
padding settings affect both clip view layout and content. This leads
to a dilemma: in a clip collection view settings object, should those
settings be considered layout settings or clip view settings? I
have chosen to consider them layout settings, since then a change
of layout type affects only layout settings, and never clip view
settings. However, this leaves us with settings that affect clip
view content in both the layout and clip view settings, which
complicates clip view initialization and settings updates. A
possible solution would be to augment the clip view settings of
a clip collection view settings object with the relevant layout
settings before initializing a clip view or updating its settings.

A similar dilemma arises concerning clip label settings, and
probably other display elements. Could we perhaps have a
nonredundant, hierarchical settings namespace, but allow a given
setting to appear in multiple places in the settings UI?

Perhaps it would be be helpful to allow presets that specify values
for some settings but not others. Then one could maintain settings
presets for separate concerns (e.g. layouts, spectrogram parameters,
spectrogram colors).

*/


class ClipCollectionView {
	
	
	constructor(div, clips, clipViewClasses, settings) {
		
		this._div = div;
		this._clips = clips;
		this._clipViewClasses = clipViewClasses;
		this._settings = settings;
		this._pageNum = 0;
		
		this._clipViews = this._createClipViews(settings);
		this._layout = this._createLayout(settings);
		
		this._update();
		
	}
	
	
	_createClipViews(settings) {
		const viewClass = this.clipViewClasses[settings.clipViewType];
		const viewSettings = _getFullClipViewSettings(settings);
		const createClipView = clip => new viewClass(this, clip, viewSettings);
		return this.clips.map(createClipView);
	}
	
	
	_createLayout(settings) {
		const layoutClass = _layoutClasses[settings.layoutType];
		return new layoutClass(this.div, this._clipViews, settings.layout);
	}
	
	
	_update() {
		
		if (this.numPages === 0) {
			
			// TODO: Show message indicating that there are no clips.
			
		} else {
			
		    this._layout.layOutClipViews(this.pageNum);
		    
		}
		
	}
	
	
	get div() {
		return this._div;
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	get clipViewClasses() {
		return this._clipViewClasses;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		this._updateClipViewSettings(settings);
		this._updateLayoutSettings(settings);
		this._settings = settings;
		this.pageNum = 0;
		this._update();
	}
	
	
	_updateClipViewSettings(settings) {
		
		if (settings.clipViewType !== this.settings.clipViewType) {
			// clip view type will change
			
			this._clipViews = _createClipViews(settings);
			
		} else {
			// clip view type will not change
		
			// TODO: Update view settings only if they have changed.
			const viewSettings = _getFullClipViewSettings(settings);
			for (let view of this._clipViews) {
				view.settings = viewSettings;
			}
			
		}
		
	}
	
	
	_updateLayoutSettings(settings) {
		
		if (settings.layoutType !== this.settings.layoutType)
			// layout type will change
			
			this._layout = this._createLayout(settings);
			
		else
			// layout type will not change
			
			this._layout.settings = settings.layout;
		
	}
	
	
	get numPages() {
		return this._layout.numPages;
	}
	
	
	getPageIndexBounds(pageNum) {
		return this._layout.getPageIndexBounds(pageNum);
	}

	
	get pageNum() {
		return this._pageNum;
	}
	
	
	set pageNum(pageNum) {
		this._pageNum = pageNum;
		this._update();
	}
	
	
	onResize() {
		this._layout.onResize(this.pageNum);
	}


}


function _getFullClipViewSettings(settings) {
	// TODO: Augment clip view settings with any relevant ones
	// from the layout settings, e.g. the time axis duration or
	// initial and final padding.
	return settings.clipView;
}


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
// class _UniformNonresizingClipViewsLayout { }


// /** Layout that displays uniform, resizing clip views. */
// class _UniformResizingClipViewsLayout { }


/** Layout that displays nonuniform, nonresizing clip views. */
class _NonuniformNonresizingClipViewsLayout {
	
	
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
class _NonuniformResizingClipViewsLayout {
	
	
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


const _layoutClasses = {
	'Nonuniform Nonresizing Clip Views': _NonuniformNonresizingClipViewsLayout,
	'Nonuniform Resizing Clip Views': _NonuniformResizingClipViewsLayout
};
