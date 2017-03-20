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
		    font_size: .8
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
	
	
	constructor(
		    elements, clips, recordings, solarEventTimes, settings,
		    clipViewDelegateClasses) {
		
		this._elements = elements;
		this._clips = clips;
		this._settings = settings;
		this._clipViewDelegateClasses = clipViewDelegateClasses;
		
		this._clipViews = this._createClipViews(settings);
		
		this._layoutClasses = this._createLayoutClassesObject();
		this._layout = this._createLayout(settings);
		
		this._rugPlot = new NightRugPlot(
			this, this.elements.rugPlotDiv, clips, recordings, solarEventTimes)
			
		this._audioContext = new window.AudioContext();
		
		this.pageNum = 0;
		
	}
	
	
	_createClipViews(settings) {
		
		const viewSettings = settings.clipView;
		const delegateClass =
			this.clipViewDelegateClasses[settings.clipViewType];
		
		const clipViews = new Array(clips.length);
		for (const [i, clip] of clips.entries())
			clipViews[i] =
				new ClipView(this, i, clip, viewSettings, delegateClass);
		
		return clipViews;
		
	}
	
	
	_createLayoutClassesObject() {
		return {
			'Nonuniform Nonresizing Clip Views':
				_NonuniformNonresizingClipViewsLayout,
			'Nonuniform Resizing Clip Views':
				_NonuniformResizingClipViewsLayout
		};
	}
	
	
	_createLayout(settings) {
		const layoutClass = this._layoutClasses[settings.layoutType];
		return new layoutClass(
			this.elements.clipsDiv, this._clipViews, settings.layout);
	}
	
	
	_createSelection() {
		
		if (this.numPages > 0) {
			
		    const [startNum, endNum] = this.getPageClipNumRange(this.pageNum);
		    return new Multiselection(startNum, endNum - 1);
		    
		} else {
			
			return null;
			
		}
		
	}
	
	
	_update() {
		
		if (this.numPages === 0) {
			
			// TODO: Show message indicating that there are no clips.
			
		} else {
			
		    this._layout.layOutClipViews(this.pageNum);
		    this._updateSelectionOutlines();
		    
		}
		
		this._updateTitle();
		
	}
	
	
	_updateTitle() {
		
		const q = clipQuery;
		
		const micOutputName =
			getMicrophoneOutputDisplayName(q.microphoneOutputName);
			
		const pageText = this._getTitlePageText();
		
		const title = `${q.date} / ${q.stationName} / ${micOutputName} / ` +
	        `${q.detectorName} / ${q.classification} / ${pageText}`;
		
		this.elements.titleHeading.innerHTML = title;
		
		document.title = `Clips - ${title}`;
		
	}
	
	
	_getTitlePageText() {
		
		const numClips = this.clips.length;
		
		if (numClips === 0) {
			
			return 'No Clips';
			
		} else {
		
			const numPages = this.numPages;
			const pageNum = this.pageNum;
			
			const pageText = `Page ${pageNum + 1} of ${numPages}`;
			
			const [startNum, endNum] = this.getPageClipNumRange(pageNum);
			
			const clipsText =
				endNum - startNum > 1 ?
				`Clips ${startNum + 1}-${endNum} of ${numClips}` :
				`Clip ${startNum + 1} of ${numClips}`;
				
			return `${pageText} / ${clipsText}`;
				
		}
			
	}
	
	
	_updateSelectionOutlines() {
		
		const clipViews = this._clipViews;
		const outline = this.settings.clipView.selectionOutline;
		const selection = this._selection;
		const startNum = this._selection.minIndex;
		const endNum = this._selection.maxIndex + 1;
		
		for (let i = startNum; i < endNum; i++) {
			const style = clipViews[i].div.style;
			const color = selection.contains(i) ? outline.color : 'transparent';
			style.outlineColor = color;
			style.outlineWidth = `${outline.width}px`;
		}
		
	}
	
	
	get elements() {
		return this._elements;
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	get clipViewDelegateClasses() {
		return this._clipViewDelegateClasses;
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
			const viewSettings = settings.clipView;
			for (const view of this._clipViews) {
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
	
	
	getPageClipNumRange(pageNum) {
		return this._layout.getPageClipNumRange(pageNum);
	}

	
	getClipPageNum(clipNum) {
		return this._layout.getClipPageNum(clipNum);
	}
	
	
	get pageNum() {
		return this._pageNum;
	}
	
	
	set pageNum(pageNum) {
		
		if (pageNum >= 0 && pageNum < this.numPages) {
			this._pageNum = pageNum;
			this._selection = this._createSelection();
			this._rugPlot.pageNum = pageNum;
		}
			
		this._update();
		
	}
	
	
	onResize() {
		this._rugPlot.onResize();
		// this._layout.onResize(this.pageNum);
	}


	extendSelection(i) {
		this._selection.extend(i);
		this._updateSelectionOutlines();
	}
	
	
	toggleClipSelectionState(i) {
		this._selection.toggle(i);
		this._updateSelectionOutlines();
	}
	
	
    onKeyPress(e) {
    	
    	// We disallow use of the space key for commands because it is
    	// already used by all of the main browsers for scrolling.
    	// We disallow use of the enter key because it does not have a
    	// single-character string representation.
    	if (e.key === ' ' || e.key === 'Enter')
    		return;
    	
//		console.log(
//			`onKeyPress "${e.key}"`,
//			e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);
		
		const action = this._getPredefinedCommandAction(e);
		
		if (action !== undefined) {
			
			// Prevent client from doing whatever it might normally do
			// in response to the pressed key.
			e.preventDefault();
			
			action();
				
		} else {
		
		    // this._annotationCommandInterpreter.onKey(e.key);
		    
		}
		
	}


	_getPredefinedCommandAction(e) {
		
		if (this._predefinedCommands === undefined)
			this._predefinedCommands = this._createPredefinedCommands();
		
//		let name = e.key;
//		if (name === ' ' && e.shiftKey)
//			name = '__SHIFT+SPACE__'
		
		console.log('_getPredefinedCommandAction', e.key);
		
		return this._predefinedCommands[e.key];
	
	}

	
	_createPredefinedCommands() {

		return {
			'>': () => this._showNextPage(),
			'<': () => this._showPreviousPage(),
			'^': () => this._selectFirstClip(),
			'.': () => this._selectNextClip(),
			',': () => this._selectPreviousClip()
		};
		
	}
	
	
	_showNextPage() {
		this.pageNum += 1;
	}
	
	
	_showPreviousPage() {
		this.pageNum -= 1;
	}
	
	
	_selectFirstClip() {
		if (this.numPages > 0) {
			const [startNum, _] = this.getPageClipNumRange(this.pageNum);
			this.selectClip(startNum);
			_scrollToTop();
		}
	}

	
	selectClip(i) {
		if (i >= 0 && i < this.clips.length) {
			this._selection.select(i);
			this._updateSelectionOutlines();
		}
	}
	
	
	_selectNextClip() {
		
		if (this._isSelectionSingleton()) {
			
			const i = this._selection.selectedIntervals[0][0];
			const [_, endClipNum] = this.getPageClipNumRange(this.pageNum);
			
			if (i === endClipNum - 1) {
				// selected clip is last of page
				
				if (this.pageNum != this.numPages - 1) {
					// page is not last
					
				    this.pageNum += 1;
			        this.selectClip(i + 1);
			        _scrollToTop();
			        
				}
				
			} else {
				
				this.selectClip(i + 1);
				this._scrollToClipViewIfNeeded(this._clipViews[i + 1]);
				
			}
			
		}
		
	}
	
	
	_isSelectionSingleton() {
		return this._selection !== null && this._selection.size === 1;
	}


	_scrollToClipViewIfNeeded(clipView) {
		
	    const rect = clipView.div.getBoundingClientRect();
	    
		const navbar = document.getElementById('navbar');
		const navbarHeight = navbar.getBoundingClientRect().height;
		
		// This is a bit of a kludge. Ideally we would set `yMargin`
		// to half the y spacing, but I'm not aware of a straightforward
		// way to get that spacing regardless of the layout. Perhaps
		// there is some reasonably straightforward method that uses
		// the bounding client rectangles of the clip views of the
		// current page?
	    const yMargin = this._getYMargin();
	    
	    if (rect.top < navbarHeight + yMargin ||
	            rect.bottom > window.innerHeight - yMargin)
	    	
	    	window.scrollBy(0, rect.top - navbarHeight - yMargin);
	    
	}


	/**
	 * Gets the y clip view margin of this clip collection view in pixels.
	 * 
	 * The y clip view margin is half of the y clip view spacing, which
	 * is specified in the clip view settings. However, the units in
	 * which the spacing is specified in the settings are not always
	 * pixels. This method gets the margin in pixels, regardless of the
	 * units of the settings.
	 */
	_getYMargin() {
		
		// Get y coordinate of top of clips div.
		const clipsDivY = this.elements.clipsDiv.getBoundingClientRect().top;
		
		// get y coordinate of top of first clip of current page.
		const [startNum, _] = this.getPageClipNumRange(this.pageNum);
		const clipDiv = this._clipViews[startNum].div;
		const clipDivY = clipDiv.getBoundingClientRect().top;
		
		const yMargin = clipDivY - clipsDivY;
		
		return yMargin;
		
	}
	
	
	_showClipViewRects() {
		console.log('clip view bounding client rectangles:');
		const r = this.elements.clipsDiv.getBoundingClientRect();
		console.log(r.left, r.top, r.width, r.height);
		const [startNum, endNum] = this.getPageClipNumRange(this.pageNum);
		for (let i = startNum; i < endNum; i++) {
			const r = this._clipViews[i].div.getBoundingClientRect();
			console.log(r.left, r.top, r.width, r.height);
		}
	}
	
	
	_selectPreviousClip() {
		
		if (this._isSelectionSingleton()) {
			
			const i = this._selection.selectedIntervals[0][0];
			const [startClipNum, _] = this.getPageClipNumRange(this.pageNum);
			
			if (i === startClipNum) {
				// selected clip is first of page
				
				if (this.pageNum != 0) {
					// page is not first
					
				    this.pageNum -= 1;
			        this.selectClip(i - 1);
			        _scrollToBottom();
			        
				}
				
			} else {
				
				this.selectClip(i - 1);
				this._scrollToClipViewIfNeeded(this._clipViews[i - 1]);
				
			}
			
		}
		
	}
	
	
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


function _scrollToTop() {
	window.scrollTo(0, 0);
}


function _scrollToBottom() {
	window.scrollTo(0, document.body.scrollHeight);
}


class _ClipViewsLayout {
	
	
	constructor(div, clipViews, settings) {
		
		this._div = div;
		this._clipViews = clipViews;
		this._settings = settings;
		this._pageStartClipNums = this._paginate();
		
		this._numPages = this._pageStartClipNums.length;
		if (this._numPages > 0)
			this._numPages -= 1;
		
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
    
    
    _paginate() {
		throw new Error('ClipViewsLayout._paginate not implemented');
    }
    
    
	get numPages() {
		return this._numPages;
	}
	
	
	getPageClipNumRange(pageNum) {
		this._checkPageNum(pageNum);
		const clipNums = this._pageStartClipNums;
		return [clipNums[pageNum], clipNums[pageNum + 1]];
	}
	
	
	_checkPageNum(pageNum) {
		
		if (this.numPages === 0)
			throw new Error(
				`Page number ${pageNum} is out of range since view has ` +
				`no pages.`);
				
		else if (pageNum < 0 || pageNum >= this.numPages)
			throw new Error(
				`Page number ${pageNum} is outside of range ` +
				`[0, ${this.numPages - 1}].`);
		
	}
	
	
	getClipPageNum(clipNum) {
		this._checkClipNum(clipNum);
		return findLastLE(this._pageStartClipNums, clipNum);
	}
	
	
	_checkClipNum(clipNum) {
		
		const numClips = this._clipViews.length;
		
		if (numClips === 0)
			throw new Error(
				`Clip number ${clipNum} is out of range since view has ` +
				`no clips.`);
				
		else if (clipNum < 0 || clipNum >= numClips)
			throw new Error(
				`Clip number ${clipNum} is outside of range ` +
				`[0, ${numClips - 1}].`);
		
	}
	
	
}


/** Layout that displays nonuniform, nonresizing clip views. */
class _NonuniformNonresizingClipViewsLayout extends _ClipViewsLayout {
	
	
	/**
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
	
	
	/**
	 * Assigns clips to pages.
	 */
	_paginate() {
		
		const numClips = this.clipViews.length;
		
		if (numClips === 0)
			return [];
		
		else {
			
			const pageSize = this.settings.page.size;
			const numPages = Math.ceil(numClips / pageSize);
			const pageStartClipNums = new Array(numPages + 1);
			
			let startClipNum = 0;
			for (let i = 0; i < numPages; i++) {
				pageStartClipNums[i] = startClipNum;
				startClipNum += Math.min(pageSize, numClips - startClipNum);
			}
			pageStartClipNums[numPages] = startClipNum;
			
			return pageStartClipNums;
			
		}
		
	}
	
	
	layOutClipViews(pageNum) {
		
		this._checkPageNum(pageNum);
		
		const clipsDiv = this.div;
		
		_removeChildren(clipsDiv);
		
		const cv = this.settings.clipView;
		
		const y_margin = cv.ySpacing / 2;
		const x_margin = cv.xSpacing / 2;
		const margin = y_margin + 'px ' + x_margin + 'px ';

		// Style page div. It is important to set values for pretty much
		// all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'row';
		clipsDiv.style.flexWrap = 'wrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'center';
		clipsDiv.style.alignContent = 'flex-start';
		clipsDiv.style.alignItems = 'flex-end';
		clipsDiv.style.width = 'auto';
		clipsDiv.style.margin = margin;
		
		const [startNum, endNum] = this.getPageClipNumRange(pageNum);
		const height = cv.height + 'px';
		
		for (let i = startNum; i < endNum; i++) {
			
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
		    
			clipsDiv.appendChild(clipDiv);
			
		}
		
		this._renderClipViews(pageNum);
		
	}
	
	
	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {
		
		const [startNum, endNum] = this.getPageClipNumRange(pageNum);
		
		for (let i = startNum; i < endNum; i++)
			this.clipViews[i].render();
		
	}
	
	
	// TODO: It seems that this is never called. Should we delete it?
	onResize(pageNum) {
		
		console.log('NonresizingLayout.onResize');
		this._checkPageNum(pageNum);
		
		// For this layout type resizes are handled by the flexbox layout.
		
	}
	
	
}


/** Layout that displays nonuniform, resizing clip views. */
class _NonuniformResizingClipViewsLayout extends _ClipViewsLayout {
	
	
	/**
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

	
	/**
	 * Assigns clips to pages and rows.
	 */
	_paginate() {
		
		const pg = this.settings.page;
		const cv = this.settings.clipView;
		const clipViews = this.clipViews;
		
		const pages = [];
		
		if (clipViews.length > 0) {
			
			const xSpacing = cv.xSpacing;
			const maxRowWidth = 100. - xSpacing;
			const widthFactor = 100. / pg.width;
			
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
					
					// We always append the clip number to the current
					// page, even if the clip will start a new page, so
					// that we can obtain an end clip number for any row
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
			
		}
		
		this._pages = pages;
		
		if (pages.length == 0)
			return [];
		
		else {
			const pageStartClipNums = pages.map(p => p[0]);
			const lastPage = pages[pages.length - 1];
			pageStartClipNums.push(lastPage[lastPage.length - 1]);
			return pageStartClipNums;
		}

	}
	
	
	layOutClipViews(pageNum) {
		
		this._checkPageNum(pageNum);
		
		const clipsDiv = this.div;
		
		_removeChildren(clipsDiv);
		
		const pg = this.settings.page;
		const cv = this.settings.clipView;

		const xMargin = _toCssPercent(cv.xSpacing / 2.);
		const yMargin = _toCssPercent(cv.ySpacing / 2.);
		const margin = yMargin + ' ' + xMargin;
		
		// Style the page div. It is important to set values for pretty
		// much all of the flexbox properties here since we allow switching
		// between different layouts for the same page div.
		clipsDiv.style.display = 'flex';
		clipsDiv.style.flexDirection = 'column';
		clipsDiv.style.flexWrap = 'nowrap';
		clipsDiv.style.flex = '1 1 auto';
		clipsDiv.style.justifyContent = 'flex-start';
		clipsDiv.style.alignContent = 'stretch';
		clipsDiv.style.alignItems = 'stretch';
		clipsDiv.style.width = 'auto';
		clipsDiv.style.margin = margin;

		const rowStartClipNums = this._pages[pageNum];
		const clipViews = this.clipViews;
				
		for (let i = 0; i < pg.height; i++) {
			
			// Create row div. We create a separate div for each row so
			// we can lay out clip views whose durations exceed the display
			// width in a special way. See below for details.
			const rowDiv = document.createElement('div');
			rowDiv.className = 'clip-row';
			rowDiv.style.display = 'flex';
			rowDiv.style.flexDirection = 'row';
			rowDiv.style.flex = '1 1 1px';
			rowDiv.style.justifyContent = 'center';
			
			if (i < rowStartClipNums.length) {
				// row contains clips
				
				const startNum = rowStartClipNums[i];
				const endNum = rowStartClipNums[i + 1];
				const rowLength = endNum - startNum
				
				for (let j = startNum; j < endNum; j++) {
					
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
					
					rowDiv.appendChild(clipDiv);
					
				}
				
			}
						
			clipsDiv.appendChild(rowDiv);
			
		}
		
		this._renderClipViews(pageNum);
		
	}
	

	// TODO: Reconsider whether or not we need to lay out clip divs
	// and render their contents in separate stages. If we do retain
	// the two separate stages, document why.
	_renderClipViews(pageNum) {
		
		const [startNum, endNum] = this.getPageClipNumRange(pageNum);
		
		const clipViews = this.clipViews;
		for (let i = startNum; i < endNum; i++)
			clipViews[i].render();
		
	}
	
	
	// TODO: It seems that this is never called. Should we delete it?
	onResize(pageNum) {
		console.log('ResizingLayout.onResize');
		this._checkPageNum(pageNum);
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


/*

Clip collection view layout sets clip view time bounds, so clip view
does not have to know anything about layout.

clip collection view settings:

    layout_type: Nonuniform Resizing Clip Views
    
    layout:
        page_width: seconds
        page_height: rows
        x_spacing: percent of page width
        y_spacing: percent of page width
        initial_padding: seconds
        final_padding: seconds
            
    clip_view_type: Spectrogram
    
    clip_view:
    
        selection_outline:
            width: pixels
            color: yellow
            
        label:
		    visible: true
		    location: bottom
		    color: white
		    size: .8
		    classification_included: true
		    start_time_included: false
		    hidden_classification_prefixes: ["Call."]
		    
		play_button:
		    color: yellow
		    
		frequency_axis_limits:
		    start: hertz
		    end: hertz
		
		spectrogram:
		    window:
		        type: Hann
		        size: 100
		    hop_size: 25
		    dft_size: 256
		    power_reference: 1
		    smoothing_enabled: true
		    colormap:
		        type: Gray
		        domain_limits:
		            start: 0
		            end: 1
		        power_limits:
		            start: dB
		            end: dB
		   
		   
settings.selection_outline_width = 5;
settings.spectrogram.window.type = 'Gaussian';
settings.spectrogram.colormap.type = 'Gray';
settings.spectrogram.colormap.power_limits: { start: 10, end: 100 };


Observations and questions:

* We will deal with *settings*, each of which has a name and a value.
  The settings namespace is hierarchical. Setting values are typed.
  Settings have default values. The set of settings with default
  values for an application is the *default settings*.
  
* Each user can specify a set of *application settings*.

* Sets of settings are composable by sequencing. A setting name is
  looked up in the sequence by looking it up in each of the sequence
  elements, taking the first value found.
  
* We look up a setting name in a sequence of sets of settings that
  typically ends with the application settings followed by the
  default settings.
  
* A preset is a set of settings with particular names, according to
  the preset's *preset type*.

* How can we allow the user to define a preset that "plugs in" at various
  places in the settings namespace? For example, how could they define
  one spectrogram settings preset that can be used both for clip
  collection views and individual clip views? (Perhaps the answer is
  relative names.)

* How are settings specified? How do plugins specify the settings they
  use? How do they specify preset types?

* How do we create forms for editing settings? To what extent can we
  create them automatically? Can we support their description via YAML?

* Can we implement lookup with composition via dot notation in both
  Python and JavaScript?
  
* Can we support both camel and snake case?

*/


class ClipView {
	
	
	constructor(parent, clipNum, clip, settings, delegateClass) {
		
		this._parent = parent;
		this._clipNum = clipNum;
		this._clip = clip;
		this._settings = settings;
		
		this._delegate = new delegateClass(this, this.clip, this.settings);

		this._div = null;
		this._label = null;
		this._playButton = null;
		
	}
	
	
	get parent() {
		return this._parent;
	}
	
	
	get clipNum() {
		return this._clipNum;
	}
	
	
	get clip() {
		return this._clip;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		if (this._div !== null) {
			this._updateSettings(settings);
		}
		this._settings = settings;
		this._delegate.settings = settings;
	}
	
	
	_updateSettings(settings) {
		
	}
	
	
	// TODO: Decouple the time axis limits of clip views from their
	// clips so that, for example, we can create uniform-width clip
	// views and clip views that pad their clips with context. This
	// will mainly come into play when we display clips extracted
	// on the fly from their parent recordings.
	get duration() {
		const clip = this.clip;
		return (clip.length - 1) / clip.sampleRate;
	}
	
	
	get div() {
		if (this._div === null) {
			this._div = this._createDiv();
			this._populateDiv();
		}
		return this._div;
	}
	
	
	_createDiv() {
	    const div = document.createElement('div');
	    div.className = 'clip';
	    return div;
	}
	    
	    
	_populateDiv() {
	    this._canvas = this._createCanvas();
		this._label = this._createLabel();
		this._styleLabel();
	    this._startClipAudioDataDownload();
	}


	_createCanvas(div) {
		
	    const canvas = document.createElement('canvas');
	    canvas.className = 'clip-canvas';
	    canvas.addEventListener('mouseover', e => this._onMouseOver(e));
	    canvas.addEventListener('mouseout', e => this._onMouseOut(e));
	    canvas.addEventListener('click', e => this._onCanvasClick(e));
	    this._div.appendChild(canvas);
	    
	    return canvas;
	    
	}
	
	
	_onMouseOver(e) {
		console.log("mouse over " + this.clipNum);
	}
	
	
	_onMouseOut(e) {
		console.log("mouse out " + this.clipNum);
	}
	
	
	_onCanvasClick(e) {
	
		const parent = this.parent;
		const clipNum = this.clipNum;
		
		if (e.shiftKey)
			parent.extendSelection(clipNum);
		else if (e.ctrlKey || e.metaKey)
			parent.toggleClipSelectionState(clipNum);
		else
			parent.selectClip(clipNum);
		
	}
	
	
    _createLabel() {
	    const label = document.createElement('p');
	    label.className = 'clip-label';
	    this._div.appendChild(label);
	    return label;
	}
	
	
    _styleLabel() {
    	
	    const label = this._label.style;
	    const offset = '2px';
	    const labelSettings = this.settings.label;
	    const loc = labelSettings.location;
	    
	    // Set label style attributes to defaults.
	    label.left = 'unset';
	    label.top = 'unset';
	    label.right = 'unset';
	    label.bottom = 'unset';
	    label.width = 'auto';
	    label.height = 'auto';
	    label.margin = '0';
	    
	    // Set label horizontal location.
	    if (loc.endsWith('Left')) {
	    	label.left = offset;
	    } else if (loc.endsWith('Right')) {
	    	label.right = offset;
	    } else {
	    	label.width = '100%';
	    	label.margin = '0 auto';
	    }
	    
	    // Set label vertical location and padding.
	    if (loc.startsWith('Below')) {
	    	label.top = '100%';
	    	label.marginTop = `${this.settings.selectionOutline.width}px`;
	    } else if (loc.startsWith('Above')) {
	    	label.bottom = '100%';
	    	label.marginBottom = `${this.settings.selectionOutline.width}px`;
	    } else if (loc.startsWith('Top')) {
	    	label.top = offset;
	    } else {
	    	label.bottom = offset;
	    }
	    
	    label.color = labelSettings.color;
	    label.fontSize = `${labelSettings.fontSize}em`;
	    
		label.visibility = labelSettings.visible ? 'visible' : 'hidden';
			    
    }
    
    
    _startClipAudioDataDownload() {
    	
    	const clip = this.clip;
		const context = new OfflineAudioContext(1, 1, clip.sampleRate);
		const xhr = new XMLHttpRequest();
		xhr.open('GET', clip.url);
		xhr.responseType = 'arraybuffer';
		xhr.onload = () =>
			context.decodeAudioData(xhr.response).then(audioBuffer =>
		        this._onAudioDataDecoded(audioBuffer));
		xhr.send();
		
		// See comment in _createPlayButton for information regarding
		// the following.
//	    const context = new OfflineAudioContext(
//          1, clip.length, clip.sampleRate);
//	    const source = context.createMediaElementSource(audio);
//	    source.connect(context.destination);
//	    context.startRendering().then(audioBuffer =>
//	        onAudioDecoded(audioBuffer, clip));
	
	}


    // TODO: Create a SpectrogramRenderer class that encapsulates the
    // spectrogram computation and rendering pipeline?
	_onAudioDataDecoded(audioBuffer) {
		
		console.log('got samples for clip', this.clipNum);
//		_showAudioBufferInfo(audioBuffer);
		
		const clip = this.clip;
		clip.audioBuffer = audioBuffer;
	    clip.samples = audioBuffer.getChannelData(0);
	    
	    // We create the play button for a clip only after its audio data
	    // are available since it is only then that we can play them from
	    // this.clip.audioBuffer using the Web Audio API.
		this._playButton = this._createPlayButton();
		this._stylePlayButton();
	    
	    this._delegate.onClipAudioDataDownloaded()
	    
	}


	_createPlayButton() {
		
	    const button = document.createElement('button');
	    button.className = 'clip-play-button';
	    button.addEventListener('click', e => this._onPlayButtonClick(e));
	    this._div.appendChild(button);    
	    
	    const icon = document.createElement('span');
	    icon.className = 'glyphicon glyphicon-play';
	    button.appendChild(icon);
	    
	    return button;
	    
	    /*
	     * The following comment is outdated, and should be updated.
	     * 
	     * TODO: Download each audio file only once rather than twice.
	     * We currently download an audio file once for its HTML5 audio
	     * element (for playback) and a second time using an XHR (to get
	     * its samples so we can compute a spectrogram from them).
	     * 
	     * I believe we should be able to use a Web Audio
	     * MediaElementSourceNode to decode the audio of an audio element
	     * into the destination AudioBuffer of an offline audio context,
	     * obviating the XHR, but I have not been able to get this to work.
	     * The commented code in _startClipSamplesDownload always yields
	     * all-zero samples.
	     * 
	     * Another approach would be use only the XHR, dropping the audio
	     * element and performing playback using Web Audio. I would prefer
	     * the other approach, however, since it should allow us to decode
	     * only portions of the source of an audio element, which would be
	     * useful in the future for long sounds.
	     */
//	    const audio = document.createElement('audio');
//	    audio.className = 'clip-audio';
//	    audio.setAttribute('src', clip.url);
//	    audio.innerHtml =
//	        'Your browser does not support the <code>audio</code> HTML element.'
//	    div.appendChild(audio)
	    
	}
    

	_onPlayButtonClick(e) {
		this._playAudioBuffer(this.clip.audioBuffer);
	}
	
	
	_playAudioBuffer(buffer) {
		const context = this.parent._audioContext;
		const source = context.createBufferSource();
		source.buffer = buffer;
		source.connect(context.destination);
		source.start();
	}
	
	
    _stylePlayButton() {
    	
		const button = this._playButton.style;
	    const offset = '2px';
	    const label = this._label.style;
	    const labelLoc = this.settings.label.location;
		
		button.left = offset;
		button.right = 'unset';
		
	    if (label.visibility === 'visible' && labelLoc.startsWith('Top')) {
	    	// label visible and at top of clip
	    	
	    	// Put button at bottom left of clip.
	        button.top = 'unset';
	        button.bottom = offset;
	        
	    } else {
	    	// label not visible or at bottom of clip
	    	
	    	// Put button at top left of clip.
	    	button.top = offset;
	    	button.bottom = 'unset';
	    	
	    }
	    
			    
    }
    
    
	render() {
		this._delegate.render();
		this._renderLabel();
	}
	
	
	_renderLabel() {

		const clip = this.clip;
		const s = this.settings.label;
	
		if (s.visible) {
			
			let labelParts = [];
			
			if (s.classificationIncluded) {
				
				let annotation = clip.annotations['Classification'];
				
				if (annotation === undefined)
					annotation = 'Unclassified';
				
					for (const prefix of s.hiddenClassificationPrefixes)
						if (annotation.startsWith(prefix))
							annotation = annotation.substr(prefix.length);
				
		        labelParts.push(annotation);
		        
			}
			
			if (s.startTimeIncluded) {
				const parts = clip.startTime.split(' ');
				labelParts.push(parts[1]);
			}
			
			this._label.innerHTML =
				(labelParts.length !== 0) ? labelParts.join(' ') : ''
			
		}
	
	}

}


class ClipViewDelegate {
	
	
	// TODO: Some clip view delegates will want to respond to mouse
	// and keyboard events, e.g. to allow clip metadata creation like
	// call start and end times and/or frequencies or frequency tracks.
	// Figure out how this will work and create a view delegate that
	// demonstrates it.
	
	// TODO: Can we use BokehJS to plot in a clip view? BokehJS might
	// create the entire contents, or it might just create an overlay
	// that is drawn on top of contents that are rendered otherwise.
	
	
	constructor(clipView, clip, settings) {
		this._clipView = clipView;
		this._clip = clip;
		this._settings = settings;
	}
	
	
	get clipView() {
		return this._clipView;
	}
	
	
	get clip() {
		return this._clip;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		this._settings = settings;
	}
	
	
	/**
	 * Handles the arrival of the clip audio data of this delegate's clip view.
	 * 
	 * A clip view creates its HTML components and downloads the clip's
	 * audio data lazily, or more specifically not until the view's div is
	 * requested. After the audio data have been downloaded the view invokes
	 * this method, which should render the clip on the clip view's canvas.
	 * The canvas is available from this method as `this.clipView._canvas`,
	 * the decoded audio data are available as `this.clip.audioBuffer`, a
	 * Web Audio AudioBuffer, and the clip samples are available as
	 * this.clip.samples, a Float32Array.
	 */
	onClipAudioDataDownloaded() {
		throw new Error(
			'ClipViewDelegate.onClipAudioDataDownloaded not implemented');
	}
	
	
	/**
	 * Renders the contents of this delegate's clip view.
	 * 
	 * This method is invoked by this delegate's clip view whenever
	 * the contents of the clip view may need to be rendered, including
	 * when the containing clip collection view has changed size.
	 */
	render() {
		throw new Error('ClipViewDelegate.render method not implemented.');
	}
	
	
}


class SpectrogramClipViewDelegate extends ClipViewDelegate {
	
	
    // TODO: Update view in response to settings changes, recomputing
	// as little as possible.
	
	onClipAudioDataDownloaded() {
		
	    const settings = this.settings.spectrogram;
	    
	    // Compute spectrogram, offscreen spectrogram canvas, and
	    // spectrogram image data and put image data to canvas. The
	    // spectrogram canvas and the spectrogram image data have the
	    // same size as the spectrogram. 
	    const clip = this.clipView.clip;
	    this._spectrogram = _computeSpectrogram(this._clip.samples, settings);
	    this._spectrogramCanvas =
	    	_createSpectrogramCanvas(this._spectrogram, settings);
	    this._spectrogramImageData =
	    	_createSpectrogramImageData(this._spectrogramCanvas);
	    _computeSpectrogramImage(
	    	this._spectrogram, this._spectrogramCanvas,
	    	this._spectrogramImageData, settings);
	    
	    // Draw spectrogram image.
	    const canvas = this.clipView._canvas;
	    _drawSpectrogramImage(clip, this._spectrogramCanvas, canvas, settings);
	    
	}

	
	render() {
		// For the time being we do nothing here, since apparently 
		// an HTML canvas can resize images that have been drawn to
		// it automatically. We will need to do something here (or
		// somewhere, anyway) eventually to handle view settings
		// changes, for example changes to spectrogram settings
		// or color map settings.
	}

	
}


function _showAudioBufferInfo(b) {
	const samples = b.getChannelData(0);
    const [min, max] = _getExtrema(samples);
    console.log(
        'AudioBuffer', b.numberOfChannels, b.length, b.sampleRate, b.duration,
        min, max);
}


function _getExtrema(samples) {
    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;
    for (const s of samples) {
    	if (s < min) min = s;
        if (s > max) max = s;
    }
    return [min, max];	
}


function _scaleSamples(samples, factor) {
    for (let i = 0; i < samples.length; i++)
    	samples[i] *= factor;	
}


function _computeSpectrogram(samples, settings) {
	
	// TODO: We need to guarantee somehow that if a window is present
	// it is the correct one, e.g. that it is of the correct type and
	// size.
	if (!settings.hasOwnProperty('window'))
	    settings.window = createDataWindow('Hann', settings.windowSize);
	
	const spectrogram = allocateSpectrogramStorage(samples.length, settings);
	computeSpectrogram(samples, settings, spectrogram);
	return spectrogram;
	
}


function _createSpectrogramCanvas(spectrogram, settings) {

	const numBins = settings.dftSize / 2 + 1;
	const numSpectra = spectrogram.length / numBins;
	
	const canvas = document.createElement('canvas');
	canvas.width = numSpectra;
	canvas.height = numBins;
	
	return canvas;

}


function _createSpectrogramImageData(canvas) {

	const numSpectra = canvas.width;
	const numBins = canvas.height;
	
	const context = canvas.getContext('2d');
	return context.createImageData(numSpectra, numBins);

}


function _computeSpectrogramImage(spectrogram, canvas, imageData, settings) {

	const numSpectra = canvas.width;
	const numBins = canvas.height;
	const data = imageData.data;
	
	// Get scale factor and offset for mapping the range
	// [settings.lowPower, settings.highPower] into the range [0, 255].
	const delta = settings.highPower - settings.lowPower
	const a = 255 / delta;
	const b = -255 * settings.lowPower / delta;
	
	// Map spectrogram values to pixel values.
	let spectrumNum = 0;
	let spectrumStride = numBins;
	let m = 0;
	for (let i = 0; i < numBins; i++) {
		let k = numBins - 1 - i
	    for (let j = 0; j < numSpectra; j++) {
			const v = 255 - a * spectrogram[k] + b;
			data[m++] = v;
			data[m++] = v;
			data[m++] = v;
			data[m++] = 255;
			k += spectrumStride;
		}
	}
	
	// Write pixel values to spectrogram canvas.
	const context = canvas.getContext('2d');
	context.putImageData(imageData, 0, 0);

}


function _drawSpectrogramImage(clip, spectrogramCanvas, canvas, settings) {

	const context = canvas.getContext('2d');
	
	// Draw gray background rectangle.
	context.fillStyle = 'gray';
	context.fillRect(0, 0, canvas.width, canvas.height);
	
	// Draw spectrogram from clip spectrogram canvas, stretching as needed.
	const gramCanvas = spectrogramCanvas;
	const numSpectra = gramCanvas.width;
	context.imageSmoothingEnabled = settings.smoothingEnabled;
	if (settings.timePaddingEnabled) {
		let [x, width] = _getSpectrogramXExtent(
			settings, numSpectra, clip, canvas.width);
		context.drawImage(gramCanvas, x, 0, width, canvas.height);
	} else {
		context.drawImage(gramCanvas, 0, 0, canvas.width, canvas.height);
	}
	
}


function _getSpectrogramXExtent(settings, numSpectra, clip, canvasWidth) {
	const sampleRate = clip.sampleRate;
	const startTime = settings.window.length / 2 / sampleRate;
	const spectrumPeriod = settings.hopSize / sampleRate;
	const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
	const span = (clip.length - 1) / sampleRate;
	const pixelPeriod = span / canvasWidth;
	const x = startTime / pixelPeriod;
	const width = (endTime - startTime) / pixelPeriod;
	return [x, width];
}


class _AnnotationCommandInterpreter {
	
	
	constructor(spec) {
		this._commandNamePrefixes = new Set();
		this._commandActions = {};
		this._parseSpec(spec);
		this._clearCommandNameBuffer();
	}
	
	
	_parseSpec(spec) {
		for (const element of spec)
			this._parseSpecElement(element);
	}
	
	
	_parseSpecElement(element) {
		const commands = element.annotation_commands;
		const commandNames = Object.keys(commands);
		this._addCommandNamePrefixes(commandNames);
		this._addCommandActions(element.annotation_name, commands);
	}
	
	
	_addCommandNamePrefixes(names) {
		
		/*
		 * Adds the nonempty, proper prefixes of the specified command
		 * names to this._commandNamePrefixes.
		 */
		
		for (const name of names)
			for (let i = 1; i < name.length; i++)
				this._commandNamePrefixes.add(name.slice(0, i));
		
	}
	
	
	_addCommandActions(annotationName, commands) {
		const keys = Object.keys(commands);
		for (const key of keys)
			this._commandActions[key] =
				_parseCommandAction(annotationName, commands[key]);
	}
	
	
	_clearCommandNameBuffer() {
		this._commandNameBuffer = '';
	}
	
	
	onKey(key) {
		
		if (key === '\\') {
			
			this._clearCommandNameBuffer();
			console.log('Cleared command name buffer.');
		
		} else {
			
			const name = this._commandNameBuffer + key;
			
			let action = this._commandActions[name];
			
			if (action !== undefined) {
				
				action();
				this._clearCommandNameBuffer();
			
			} else if (this._commandNamePrefixes.has(name)) {
					
				// TODO: Show contents of name buffer in UI.
				console.log(`Command name buffer "${name}".`);
				this._commandNameBuffer = name;
			    
			
			} else {
				// nonexistent command
				
				// TODO: Notify user of error.
				console.log(`Unrecognized command name "${name}".`);
				this._clearCommandNameBuffer();
				
			}
				
		}
		
	}
	
}

	
function _parseCommandAction(annotationName, actionSpec) {
	
	let scope = 'Selection';
	if (actionSpec.startsWith('*')) {
		scope = 'Page';
		actionSpec = actionSpec.slice(1);
	}
	
	let annotationValue = null;
	let annotatorName = null;
	if (actionSpec.startsWith('@'))
		annotatorName = actionSpec.slice(1);
	else
		annotationValue = actionSpec;

	if (annotationValue !== null)
		return () => _annotateClips(annotationName, annotationValue, scope);
	else
		return () => _runClipAnnotator(annotationName, annotatorName, scope);

}


function _annotateClips(name, value, scope) {
	
	if (scope === 'Selection') {
		_annotateSelectedClips(name, value);
		// TODO: We need access to the clip collection view here.
		_selectNextClip();
	}
	
	else if (scope === 'Page')
		_annotateIntervalClips(name, value, [0, clips.length - 1]);
	
	else
		// TODO: Implement 'All' scope.
		window.alert(`Unrecognized annotation command scope "${scope}".`);
	
}


function _annotateSelectedClips(name, value) {
	for (const interval of selection.selectedIntervals)
		_annotateIntervalClips(name, value, interval);
}


function _annotateIntervalClips(name, value, interval) {
	
	for (let i = interval[0]; i <= interval[1]; i++) {
		
		const clip = clips[i];
		const url = `/vesper/clips/${clip.id}/annotations/${name}`;
		
		const xhr = new XMLHttpRequest();
		xhr.onload = () => _onAnnotationPutComplete(xhr, clip, name, value);
		xhr.open('PUT', url);
		xhr.setRequestHeader('Content-Type', 'text/plain; charset=utf-8');
		xhr.send(value);
		
	}

}


function _onAnnotationPutComplete(xhr, clip, annotationName, annotationValue) {
	
	console.log(
		'PUT completed', xhr.status, clip.id, annotationName, annotationValue);
	
	// TODO: Notify user on errors.
	// TODO: Handle non-"Classification" annotations.
	if (xhr.status === 200) {
		clip.classification = annotationValue;
		drawClip(clip, clipSpectrogramSettings);
	}
	
}


function _runClipAnnotator(annotationName, annotatorName, scope) {
	// TODO: Implement this function.
	console.log(
		`run annotator "${annotationName}" "${annotatorName}" ${scope}`);
}


// <ArrowLeft>
// <Shift+ArrowLeft>
// <ArrowRight>
// <Shift+ArrowRight>


/*
Questions:
* What is the relationship between settings and presets?
* What is the relationship between settings and application preferences?
*/


/*
Annotation options:

annotate_selected_clips:
* select_next_clip: Boolean
* play_next_clip: Boolean

annotate_page_clips:
* advance_to_next_page: Boolean
* select_first_clip: Boolean
* play_first_clip: Boolean

*/


/*


// What are Unicode arrow code point names?


// basic keyboard commands YAML
commands:
    '<Shift+ArrowRight>': show_next_page
    '<Shift+ArrowLeft>': show_previous_page
    '<ArrowRight>': select_next_clip
    '<ArrowLeft>': select_previous_clip
    '^': select_first_clip
    '/': play_selected_clip
    

// classification keyboard commands header YAML
bindings:

    annotation_name: Classification
    annotation_scope: Selection
    
    annotate:
        args: [value]
        actions:
            - [annotate_clips, <<annotation_name>>, <<value>>, <<annotation_scope>>]
            
    annotate_page:
        args: [value]
        actions:
            - [annotate_clips, <<annotation_name>>, <<value>>, Page]
            
    commands:
        '#': [bind_temp, annotation_scope, Page]
        '*': [bind_temp, annotation_scope, All]
        '_': clear_temp_bindings
        
        
*/

_BASIC_KEYBOARD_COMMANDS = {
		
    'commands': {
    	'<Shift+ArrowRight>': 'show_next_page',
    	'<Shift+ArrowLeft>': 'show_previous_page',
    	'<ArrowRight>': 'select_next_clip',
    	'<ArrowLeft>': 'select_previous_clip',
    	'^': 'select_first_clip',
    	'/': 'play_selected_clip'
    }

};


_CLASSIFICATION_KEYBOARD_COMMANDS_HEADER = {
		
	'bindings': {
		
		'annotation_name': 'Classification',
		'annotation_scope': 'Selection',
			
		'annotate': {
			'args': ['value'],
			'actions': [
			    ['annotate_clips',
			        '<<annotation_name>>', '<<value>>', '<<annotation_scope>>']
			]
		},
		
		'annotate_page': {
		    'args': ['value'],
		    'actions': [
		        ['annotate_clips', '<<annotation_name>>', '<<value>>', 'Page']
		    ]
		},
		
	},
	
	'commands': {
    	'#': ['bind_temp', 'annotation_scope', 'Page'],
    	'*': ['bind_temp', 'annotation_scope', 'All'],
    	'_': 'clear_temp_bindings'
	}
		

};


_CLASSIFICATION_KEYBOARD_COMMANDS = {
	
	// Extension merges mapping items like 'bindings' and 'commands'.
	'extends': [
	    'basic_keyboard_commands',
	    'classification_keyboard_commands_header'
	],

	'settings': {
        'advance_selection_after_single_clip_annotation': true,
        'advance_page_after_page_annotation': true,
        'play_single_clip_selections': true
	},
		
    'commands': {
    	
    	'!c': ['bind', {'annotation_name': 'Classification'}],
    	'!h': ['bind', {'annotation_name': 'Harold Classification'}],
    	
    	'c': ['classify_clips', 'Call'],
    	'C': ['classify_page', 'Call'],
    	'n': ['classify_clips', 'Noise'],
    	'N': ['classify_page', 'Noise'],
    	'x': ['classify_clips', 'Unclassified'],
    	'X': ['classify_page', 'Unclassified'],

	    '@o': ['auto_classify_clips', 'MPG Ranch Outside Clip Classifier'],
	    '@O': ['auto_classify_page', 'MPG Ranch Outside Clip Classifier'],
	    '@c': ['auto_classify_clips', 'NFC Coarse Clip Classifier'],
	    '@C': ['auto_classify_page', 'NFC Coarse Clip Classifier'],
	    
    }
    
};


function _createExampleCommandInterpreter() {
	return new _CommandInterpreter(_CLASSIFICATION_KEYBOARD_COMMANDS);
}
