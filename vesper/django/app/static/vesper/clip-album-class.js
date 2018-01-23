'use strict'


/*
 * TODO: Client should perform only those display pipeline functions that
 * are needed to update the display after a settings change. For example
 * it should not recompute spectrograms after a color map or layout change.
 */


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
to a dilemma: in a clip album settings object, should those settings
be considered layout settings or clip view settings? I have chosen
to consider them layout settings, since then a change of layout type
affects only layout settings, and never clip view settings. However,
this leaves us with settings that affect clip view content in both
the layout and clip view settings, which complicates clip view
initialization and settings updates. A possible solution would be to
augment the clip view settings of a clip album settings object with
the relevant layout settings before initializing a clip view or
updating its settings.

A similar dilemma arises concerning clip label settings, and
probably other display elements. Could we perhaps have a
nonredundant, hierarchical settings namespace, but allow a given
setting to appear in multiple places in the settings UI?

Perhaps it would be be helpful to allow presets that specify values
for some settings but not others. Then one could maintain settings
presets for separate concerns (e.g. layouts, spectrogram parameters,
spectrogram colors).

*/


const _DEFAULT_SETTINGS = {
		
	layoutType: 'Nonuniform Resizing Clip Views',
	
	layout: {
		
		page: {
			width: 2,              // seconds
			height: 6              // rows
		},
		
		clipView: {
			xSpacing: 1,           // percent of display width
			ySpacing: 2            // percent of display width
		}
		
	},
	
	clipViewType: 'Spectrogram',
	
	clipView: {
		
		selectionOutline: {
			color: 'orange',
			width: 5
		},
		
        label: {
		    visible: true,
		    location: 'Below',
		    color: 'black',
		    fontSize: 1,
		    classificationIncluded: true,
		    startTimeIncluded: true,
		    hiddenClassificationPrefixes: []
        },
        
		spectrogram: {
			windowSize: .005,
			hopSize: .0025,
			referencePower: 1e-9,
			lowPower: 10,
			highPower: 100,
			startFrequency: 0,
			endFrequency: 11000,
			smoothingEnabled: true,
			timePaddingEnabled: false
		}
	
	}
	
};


const _COMMAND_CHARS = new Set(
	'abcdefghijklmnopqrstuvwxyz' +
	'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
	'`1234567890-=[]\\;\',./' +
	'~!@#$%^&*()_+{}|:"<>?');


const _DEFAULT_COMMANDS = {
		
	'globals': {
		'annotation_name': 'Classification',
		'annotation_scope': 'Selection'
	},
	
	'commands': {
		'>': ['show_next_page'],
		'<': ['show_previous_page'],
	    '.': ['select_next_clip'],
	    ',': ['select_previous_clip'],
	    '/': ['play_selected_clip']
	}

};


// The maximum number of clips that the _annotateClips function will
// annotate without displaying the wait cursor.
const _ANNOTATION_WAIT_CURSOR_THRESHOLD = 20


function setCursor(name) {
	document.body.style.cursor = name;
}


class ClipAlbum {
	
	
	constructor(
		    elements, clips, recordings, solarEventTimes,
		    clipViewDelegateClasses, settings = null, commands = null) {
		
		this._elements = elements;
		this._clips = this._createClips(clips);
		
		this._clipViewDelegateClasses = clipViewDelegateClasses;
		
		this._settings = settings === null ? _DEFAULT_SETTINGS : settings;
		this.commands = commands === null ? _DEFAULT_COMMANDS : commands;
		
		this._clipViews = this._createClipViews(this.settings);
		
		this._layoutClasses = this._createLayoutClassesObject();
		this._layout = this._createLayout(this.settings);
		
		if (this.elements.rugPlotDiv !== null)
        		this._rugPlot = new NightRugPlot(
        			this, this.elements.rugPlotDiv, this.clips, recordings,
        			solarEventTimes);
		else
		    this._rugPlot = null;
			
		// We use a Web Audio `AudioContext` object to play clips.
		this._audioContext = new window.AudioContext();
		
		const clipManagerSettings = {
			'maxNumClips': 2000,
			'numPrecedingPreloadedPages': 1,
			'numFollowingPreloadedPages': 1
		};
		this._clipManager = new _PreloadingClipManager(
			clipManagerSettings, this.clips, this._layout.pageStartClipNums);
		
		this.pageNum = 0;
		
	}
	
	
	_createClips(clipInfos) {
		
		const clips = [];
		
		for (const entry of clipInfos.entries()) {
			clips.push(this._createClip(entry));
		}
		
		return clips;
		
	}
	
	
	_createClip([clipNum, clipInfo]) {
		return new _Clip(clipNum, ...clipInfo);
	}
	
	
	_createClipViews(settings) {
		
		const viewSettings = settings.clipView;
		const delegateClass =
			this.clipViewDelegateClasses[settings.clipViewType];
		
		const clipViews = new Array(this.clips.length);
		
		for (const [i, clip] of this.clips.entries()) {
			
			clipViews[i] = new ClipView(
				this, clip, viewSettings, delegateClass);
			
			clip.view = clipViews[i];
			
		}
		
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
		
		const pageText = this._getTitlePageText();
		
        let title = `${q.stationMicName} / ${q.detectorName} / ` +
            `${q.classification} / ${pageText}`;
        
		if (q.date !== null)
		    title = `${q.date} / ` + title;
		
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
	
	
	get clipViewDelegateClasses() {
		return this._clipViewDelegateClasses;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		
		this._updateClipViewSettings(settings);
		
		const [paginationChanged, pageNum] =
			this._updateLayoutSettings(settings);
		
		this._settings = settings;
		
		if (paginationChanged) {
			
		    this._clipManager.update(this._layout.pageStartClipNums, pageNum);
		
		    // It is important to do this *after* updating the clip manager
		    // for both the new pagination and the (possibly) new page
		    // number. Otherwise the clip manager may update twice, once
		    // because the page number changed (but not the pagination)
		    // and a second time because the pagination changed.
		    //
			// Note that this assignment triggers a call to this._update,
		    // so we don't need to invoke this._update explicitly here.
		    this.pageNum = pageNum;
		    
		} else
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
	
	
	/*
	 * Updates the settings of this album's layout.
	 * 
	 * Returns true if and only if the album's pagination changed,
	 * or if it is not known whether or not it changed.
	 */
	_updateLayoutSettings(settings) {
		
		const oldFirstClipNum = this._layout.pageStartClipNums[this.pageNum];
		let paginationChanged;
		
		if (settings.layoutType !== this.settings.layoutType) {
			// layout type will change
			
			this._layout = this._createLayout(settings);
			
			// Pagination may or may not have changed. We say it has to
			// ensure that display will update properly in all cases.
			paginationChanged = true;
		
		} else {
			// layout type will not change
			
			const oldPageStartClipNums = this._layout.pageStartClipNums;
			this._layout.settings = settings.layout;
			paginationChanged = !arraysEqual(
				this._layout.pageStartClipNums, oldPageStartClipNums);
			
		}
		
		// Get new page number of clip that was first on old page.
		const newPageNum = this._layout.getClipPageNum(oldFirstClipNum);
		
		return [paginationChanged, newPageNum];
		
	}
	
	
	get commands() {
		return this._commands;
	}
	
	
	set commands(commands) {
		this._commands = commands;
 		this._commandInterpreter =
 			this._createCommandInterpreter(this._commands);
	}
	
	
	_createCommandInterpreter(spec) {
		
		const functionData = [
			
			['show_next_page', [], _ => this._showNextPage()],
			['show_previous_page', [], _ => this._showPreviousPage()],
			
			['select_first_clip', [], _ => this._selectFirstClip()],
			['select_next_clip', [], _ => this._selectNextClip()],
			['select_previous_clip', [], _ => this._selectPreviousClip()],
			
			['play_selected_clip', [], _ => this._playSelectedClip()],
			
			['toggle_clip_labels', [], _ => this._toggleClipLabels()],
			
			['annotate_clips', ['annotation_value'],
				e => this._annotateClipsDelegate(e)],
			['annotate_selected_clips', ['annotation_value'],
				e => this._annotateSelectedClipsDelegate(e)],
			['annotate_page_clips', ['annotation_value'],
				e => this._annotatePageClipsDelegate(e)],
			['annotate_all_clips', ['annotation_value'],
				e => this._annotateAllClipsDelegate(e)],

			['unannotate_clips', [], e => this._unannotateClipsDelegate(e)],
			['unannotate_selected_clips', [],
				e => this._unannotateSelectedClipsDelegate(e)],
			['unannotate_page_clips', [],
				e => this._unannotatePageClipsDelegate(e)],
			['unannotate_all_clips', [],
				e => this._unannotateAllClipsDelegate(e)],

		];
		
		const functions = functionData.map(
			args => new RegularFunction(...args));
		
		return new KeyboardCommandInterpreter(spec, functions);
		
	}


	_toggleClipLabels() {
		this.settings.clipView.label.visible =
			!this.settings.clipView.label.visible;
		this._updateClipViewSettings(this.settings);
	}
	
	
	_annotateClipsDelegate(env) {
		
		const scope = env.getRequired('annotation_scope');
		
		switch (scope) {
		
		case 'Selection':
			this._annotateSelectedClipsDelegate(env);
			break;
			
		case 'Page':
			this._annotatePageClipsDelegate(env);
			break;
			
		case 'All':
			this._annotateAllClipsDelegate(env);
			break;
		
		default:
			window.alert(`Unrecognized annotation scope "${scope}".`);
		
		}
		
	}


	_annotateSelectedClipsDelegate(env) {
		
		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotateSelectedClips(name, value);
		
		// TODO: Optionally play selected clip.
		this._selectNextClip();
		
	}
	
	
	_annotateSelectedClips(name, value) {
		const clipNums = this._selection.selectedIndices;
		const clips = clipNums.map(i => this.clips[i]);
		this._annotateClips(name, value, clips);
	}


	_annotateClips(name, value, clips) {
		
		if (clips.length > _ANNOTATION_WAIT_CURSOR_THRESHOLD)
		    setCursor('wait');
		
		const url = `/annotations/${name}/`;
		const clip_ids = clips.map(clip => clip.id);
		
		const xhr = new XMLHttpRequest();
		xhr.onload =
			() => this._onAnnotationsPostComplete(xhr, name, value, clips);
		xhr.open('POST', url);
		xhr.setRequestHeader('Content-Type', 'application/json; charset=utf-8');
		xhr.send(JSON.stringify({
			value: value,
			clip_ids: clip_ids
		}));
		
	}
	
	
	_onAnnotationsPostComplete(xhr, annotationName, annotationValue, clips) {
		
		if (clips.length > _ANNOTATION_WAIT_CURSOR_THRESHOLD)
		    setCursor('auto');
		
		if (xhr.status === 200) {
			
			for (const clip of clips) {
				
				const annotations = clip.annotations
				
				if (annotations !== null) {
					// client has clip annotations
					
					if (annotationValue === null)
						delete annotations[annotationName]
					else
						annotations[annotationName] = annotationValue;
					
					if (this._isClipOnCurrentPage(clip))
						clip.view.render();
					
				}
				
			}
			
		} else {
			
			this._onAnnotationError(xhr);
			
		}
		
	}
	
	
	_isClipOnCurrentPage(clip) {
		return this._layout.getClipPageNum(clip.num) == this.pageNum;
	}


	_onAnnotationError(xhr) {
		window.alert(
			`Annotation request failed with response ` +
			`"${xhr.status} ${xhr.statusText}".`);
	}
	
	
	_annotatePageClipsDelegate(env) {
		
		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotatePageClips(name, value);
		
		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.
		
	}
	
	
	_annotatePageClips(name, value) {
		const [startClipNum, endClipNum] =
			this.getPageClipNumRange(this.pageNum);
		const clipNums = rangeArray(startClipNum, endClipNum);
		const clips = clipNums.map(i => this.clips[i]);
		this._annotateClips(name, value, clips);
	}
	
	
	_annotateAllClipsDelegate(env) {
		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotateAllClips(name, value);
	}
	
	
	_annotateAllClips(name, value) {
		this._annotateClips(name, value, this.clips);
	}
	
	
	_unannotateClipsDelegate(env) {
		
		const scope = env.getRequired('annotation_scope');
		
		switch (scope) {
		
		case 'Selection':
			this._unannotateSelectedClipsDelegate(env);
			break;
			
		case 'Page':
			this._unannotatePageClipsDelegate(env);
			break;
			
		case 'All':
			this._unannotateAllClipsDelegate(env);
			break;
		
		default:
			window.alert(`Unrecognized annotation scope "${scope}".`);
		
		}
		
	}


	_unannotateSelectedClipsDelegate(env) {
		
		const name = env.getRequired('annotation_name');
		this._annotateSelectedClips(name, null);
		
		// TODO: Optionally play selected clip.
		this._selectNextClip();
		
	}
	
	
	_unannotatePageClipsDelegate(env) {
		
		const name = env.getRequired('annotation_name');
		this._annotatePageClips(name, null)
		
		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.
		
	}
	
	
	_unannotateAllClipsDelegate(env) {
		const name = env.getRequired('annotation_name');
		this._annotateAllClips(name, null);
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
			const range = this.getPageClipNumRange(pageNum);
			if (this._rugPlot !== null)
			    this._rugPlot.setPageClipNumRange(range);
			this._clipManager.pageNum = pageNum;
		}
			
		this._update();
		
	}
	
	
	onResize() {
	    if (this._rugPlot !== null)
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
    	
    	// We allow the use only of alphabetic, numeric, and symbolic
    	// characters that are not modified by the Ctrl, Alt, or Meta
    	// keys in commands. This avoids interference with use of
    	// modified keys and other keys (such as the space and enter
    	// keys) that are used by various operating systems and browsers
    	// in ways with which we don't want to interfere.
	    if (e.ctrlKey || e.altKey || e.metaKey || !_COMMAND_CHARS.has(e.key))
	    	return;
	    
//		console.log(
//			`onKeyPress "${e.key}"`,
//			e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);
		
		// Prevent client from doing whatever it might normally do
		// in response to the pressed key.
		e.preventDefault();
		
    	try {
    	    this._commandInterpreter.handleKey(e.key);
    	} catch (e) {
    		window.alert(e.message);
    	}
    	
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


	_playSelectedClip() {
		if (this._isSelectionSingleton()) {
			const i = this._selection.selectedIntervals[0][0];
			this._clipViews[i].playClip();
		}
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
	 * Gets the y clip view margin of this clip album in pixels.
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

Clip album layout settings by layout type:

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


const _CLIP_STATUS = {
	UNLOADED: 0,
	LOADING: 1,
	LOADED: 2
}


class _Clip {
	
	
	constructor(num, id, length, sampleRate, startTime) {
		
		this._num = num;
		this._id = id;
		this._length = length;
		this._sampleRate = sampleRate;
		this._startTime = startTime;
		
		this._samples = null;
		this._samplesStatus = _CLIP_STATUS.UNLOADED;
		
		this._annotations = null;
		this._annotationsStatus = _CLIP_STATUS.UNLOADED;
		
	}
	
	
	get id() {
		return this._id;
	}
	
	
	get num() {
		return this._num;
	}
	
	
	get length() {
		return this._length;
	}
	
	
	get sampleRate() {
		return this._sampleRate;
	}
	
	
	get span() {
		if (this.length === 0)
			return 0;
		else
			return (this.length - 1) / this.sampleRate;
	}
	
	
	get duration() {
		return this.length / this.sampleRate;
	}
	
	
	get startTime() {
		return this._startTime;
	}
	

	get samples() {
		return this._samples;
	}
	
	
	set samples(samples) {
		this._samples = samples;
	}
	
	
	get samplesStatus() {
		return this._samplesStatus;
	}
	
	
	set samplesStatus(status) {
		this._samplesStatus = status;
	}
	
	
	get annotations() {
		return this._annotations;
	}
	
	
	set annotations(annotations) {
		this._annotations = annotations;
	}
	
	
	get annotationsStatus() {
		return this._annotationsStatus;
	}
	
	
	set annotationsStatus(status) {
		this._annotationsStatus = status;
	}
	
	
	get url() {
		return `/clips/${this.id}/`;
	}
	
	
	get wavFileUrl() {
    	return `${this.url}wav/`;
	}
	
	
	get annotations() {
		return this._annotations;
	}
	
	
	set annotations(annotations) {
		this._annotations = annotations;
	}
	
	
	get annotationsUrl() {
		return `${this.url}annotations/`;
	}
	
	
	get annotationsJsonUrl() {
		return `${this.annotationsUrl}json/`;
	}
	
	
	getAnnotationUrl(name) {
		return `${this.annotationsUrl}${name}/`;
	}
	
	
}


class _ClipLoader {
	
	
	constructor() {
		
		// We use Web Audio `OfflineAudioContext` objects to decode clip
		// audio buffers that arrive from the server. For some reason,
		// it appears that different contexts are required for different
		// sample rates. We allocate the contexts as needed, storing them
		// in a `Map` from sample rates to contexts.
		this._audioContexts = new Map();
		
	}
	
	
    isClipUnloaded(clip) {
		return clip.samplesStatus === _CLIP_STATUS.UNLOADED;
    }

    
	loadClip(clip) {
		
		if (clip.samplesStatus === _CLIP_STATUS.UNLOADED)
			this._requestAudioData(clip);
		
		if (clip.annotationsStatus === _CLIP_STATUS.UNLOADED)
			this._requestAnnotations(clip);
		
	}
	
	
    _requestAudioData(clip) {
    	
		// console.log(`requesting audio data for clip ${clip.num}...`);

		clip.samplesStatus = _CLIP_STATUS.LOADING;
	    
		const xhr = new XMLHttpRequest();
		xhr.open('GET', clip.wavFileUrl);
		xhr.responseType = 'arraybuffer';
		xhr.onload = () => this._onAudioDataXhrResponse(xhr, clip);
		xhr.send();
		
		// See comment in ClipView._createPlayButton for information
		// regarding the following.
//	    const context = new OfflineAudioContext(
//          1, clip.length, clip.sampleRate);
//	    const source = context.createMediaElementSource(audio);
//	    source.connect(context.destination);
//	    context.startRendering().then(audioBuffer =>
//	        onAudioDecoded(audioBuffer, clip));
	
	}


    _onAudioDataXhrResponse(xhr, clip) {
    	
   	    if (xhr.status === 200) {
    		
   	    	// console.log(`received audio data for clip ${clip.num}...`);
   	    	
   	    	const sampleRate = clip.sampleRate;
   	    	
   	    	let context = this._audioContexts.get(sampleRate);
   	    	
   	    	if (context === undefined) {
   	    		// no context for this sample rate in cache
   	    		
   	    		// console.log(
   	    		// 	`creating audio context for sample rate ${sampleRate}...`);
   	    		
   	    		// Create context for this sample rate and add to cache.
   	    		context = new OfflineAudioContext(1, 1, sampleRate);
   	    		this._audioContexts.set(sampleRate, context);
   	    		
   	    	}
   	    	
   	    	// TODO: Handle decode errors.
   	    	context.decodeAudioData(xhr.response).then(
   	    		audioBuffer => this._onAudioDataDecoded(audioBuffer, clip));
    		
    	} else {
    		
    		// TODO: Notify user of error.
    		console.log(`request for clip ${clip.num} audio data failed`);
    		
    	}
    	
    	
    }
    
    
    // TODO: Create a SpectrogramRenderer class that encapsulates the
    // spectrogram computation and rendering pipeline?
	_onAudioDataDecoded(audioBuffer, clip) {
		
        // console.log(`decoded audio data for clip ${clip.num}`);
		
		// _showAudioBufferInfo(audioBuffer);
		
   	    // An audio data load operation can be canceled while in progress
    	// by changing `clip.samplesStatus` from `_CLIP_STATUS.LOADING`
    	// to `_CLIP_STATUS_UNLOADED`. In this case we ignore the data
    	// when they arrive.
    	if (clip.samplesStatus === _CLIP_STATUS.LOADING) {

			clip.audioBuffer = audioBuffer;
		    clip.samples = audioBuffer.getChannelData(0);
		    clip.samplesStatus = _CLIP_STATUS.LOADED;
		    
		    clip.view.onClipSamplesChanged();
		    
    	}
	    
	}


    _requestAnnotations(clip) {
    	
	    clip.annotationsStatus = _CLIP_STATUS.LOADING;
	    
	    const xhr = new XMLHttpRequest();
		xhr.open('GET', clip.annotationsJsonUrl);
		xhr.onload = () => this._onAnnotationsXhrResponse(xhr, clip)
		xhr.send();
		
    }
    
    
    _onAnnotationsXhrResponse(xhr, clip) {
    	
    	// An annotations load operation can be canceled while in progress
    	// by changing `clip.annotationsStatus` from `_CLIP_STATUS.LOADING`
    	// to `_CLIP_STATUS_UNLOADED`. In this case we ignore the
    	// annotations when they arrive.
    	if (clip.annotationsStatus === _CLIP_STATUS.LOADING) {

	    	if (xhr.status === 200) {
	   	    	// request completed without error
	    		
	    		clip.annotations = JSON.parse(xhr.responseText);
	    		clip.annotationsStatus = _CLIP_STATUS.LOADED;
	    		
	    	} else {
	    		// request failed
	    		
	    		// TODO: Report error somehow.
	    		
	    		clip.annotations = null;
	    		clip.annotationsStatus = _CLIP_STATUS.UNLOADED;
	    		
	    	}
	    	
	    	clip.view.onClipAnnotationsChanged();
	    	
    	}
     	
    }
    
    
    unloadClip(clip) {
    	
		clip.audioBuffer = null;
		clip.samples = null;
		clip.samplesStatus = _CLIP_STATUS.UNLOADED;
		
		clip.view.onClipSamplesChanged();
		
	}
    
    
}



const _PAGE_STATUS = {
	UNLOADED: 0,
	PARTIALLY_LOADED: 1,
	LOADED: 2
}


// Loads and unloads clip samples and annotations on behalf of a clip album.
// 
// Different clip managers may load clip data according to different policies.
// For example, one manager may load data for clip pages as they are displayed,
// requesting data from the server one clip at a time. Another manager may load
// the data for the clips of a page in bulk, obtaining all of the data from
// the server in a single request. Yet other managers may load data for all
// the clips of an album greedily, regardless of which pages have or have not
// been displayed.
class _ClipManager {
	
	
	constructor(
		    settings, clips, pageStartClipNums, pageNum = 0,
		    clipLoader = null) {
		
		this._settings = settings;
		this._clips = clips;
		this._pageStartClipNums = null;
		this._pageNum = null;
		this._clipLoader = clipLoader === null ? new _ClipLoader() : clipLoader;
		
		this._loadedPageNums = new Set();
		this._numLoadedClips = 0;
		
		this.update(pageStartClipNums, pageNum);
		
	}
	
	
	get clips() {
		return this._clips;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	get pageStartClipNums() {
		return this._pageStartClipNums;
	}
	
	
	get pageNum() {
		return this._pageNum;
	}
	
	
	set pageNum(pageNum) {
		if (pageNum != this.pageNum) {
		    this.update(this.pageStartClipNums, pageNum);
		}
	}
	
	
	/**
	 * Updates this clip manager for the specified pagination and
	 * page number.
	 * 
	 * `pageStartClipNums` is a nonempty, increasing array of clip numbers.
	 * `pageNum` is a page number in [0, `pageStartClipNums.length`).
	 */
	update(pageStartClipNums, pageNum) {

		// We assume that while `this._pageStartClipNums` and `this._pageNum`
		// are both initialized to `null` in the constructor, this method
		// is never invoked with a `null` argument: `pageStartClipNums`
		// is always a nonempty, increasing array of numbers and `pageNum`
		// is always a number.
		
		if (this.pageStartClipNums === null ||
				!arraysEqual(pageStartClipNums, this.pageStartClipNums)) {
			// pagination will change
			
			this._updatePagination(pageStartClipNums, pageNum);
			this._updatePageNum(pageNum);
			
	    } else if (pageNum !== this.pageNum) {
	    	// pagination will not change, but page number will
	    	
	    	this._updatePageNum(pageNum);
	    	
	    }
	    
	}
	
	
	_updatePagination(pageStartClipNums, pageNum) {
		
		const oldPageStartClipNums = this._pageStartClipNums;
		
		this._pageStartClipNums = pageStartClipNums
		
		if (oldPageStartClipNums !== null) {
			// may have pages loaded according to the old pagination
			
			const numAlbumPages = this.pageStartClipNums.length - 1;
			
			const requiredPageNums =
				new Set(this._getRequiredPageNums(pageNum));
			
			this._loadedPageNums = new Set();
			this._numLoadedClips = 0;
			
			for (let i = 0; i < numAlbumPages; i++) {
				
				const status = this._getPageStatus(i);
				
				if (status === _PAGE_STATUS.LOADED) {
					
					this._loadedPageNums.add(i);
					this._numLoadedClips += this._getNumPageClips(i);
					
				} else if (status === _PAGE_STATUS.PARTIALLY_LOADED) {
					
					if (requiredPageNums.has(i))
						// page required under new pagination
						
						// Load entire page.
						this._loadPage(i);
					
					else
						// page not required under new pagination
						
						// Unload part of page that is loaded.
					    this._unloadPartiallyLoadedPage(i);
					
				}
			
			}
			
		}
		
	}
	
	
	/**
	 * Gets the numbers of the pages that this clip manager should
	 * definitely load for the current pagination and the specified
	 * page number. The page numbers are returned in an array in the
	 * order in which the pages should be loaded.
	 */
	_getRequiredPageNums(pageNum) {
		throw new Error('_ClipManager._getRequiredPageNums not implemented');
	}
	
	
	_getPageStatus(pageNum) {
		
		let hasUnloadedClips = false;
		let hasLoadedClips = false;
	
		const start = this.pageStartClipNums[pageNum];
		const end = this.pageStartClipNums[pageNum + 1];
		
		for (let i = start; i < end; i++) {
			
			if (this._clipLoader.isClipUnloaded(this.clips[i])) {
				
				if (hasLoadedClips)
					return _PAGE_STATUS.PARTIALLY_LOADED;
				else
					hasUnloadedClips = true;
			
			} else {
				
				if (hasUnloadedClips)
					return _PAGE_STATUS.PARTIALLY_LOADED;
				else
					hasLoadedClips = true;
				
			}
			
		}
		
		// If we get here, either all of the clips of the page were
		// unloaded or all were not unloaded.
		return hasLoadedClips ? _PAGE_STATUS.LOADED : _PAGE_STATUS.UNLOADED;
		
	}
	
	
	_getNumPageClips(pageNum) {
		return this._getNumPageRangeClips(pageNum, 1);
	}
	
	
	_getNumPageRangeClips(pageNum, numPages) {
		const clipNums = this.pageStartClipNums;
	    return clipNums[pageNum + numPages] - clipNums[pageNum];
	}
	
	
	_loadPage(pageNum) {

    	if (!this._loadedPageNums.has(pageNum)) {
    		
    		// console.log(`clip manager loading page ${pageNum}...`);
    		
			const start = this.pageStartClipNums[pageNum];
			const end = this.pageStartClipNums[pageNum + 1];
			
			for (let i = start; i < end; i++)
				this._clipLoader.loadClip(this.clips[i]);
			
    		this._loadedPageNums.add(pageNum);
    		this._numLoadedClips += this._getNumPageClips(pageNum);
    		
    	}
		
	}
	
	
	_unloadPartiallyLoadedPage(pageNum) {
		
		// console.log(
		// 	`clip manager unloading partially loaded page ${pageNum}...`);
		
		const start = this.pageStartClipNums[pageNum];
		const end = this.pageStartClipNums[pageNum + 1];
		
		for (let i = start; i < end; i++)
			this._clipLoader.unloadClip(this.clips[i]);
					
	}
	
	
	_updatePageNum(pageNum) {
		
	    // console.log(`clip manager updating for page ${pageNum}...`);
	    
		const [unloadPageNums, loadPageNums] = this._getUpdatePlan(pageNum);
			
		for (const pageNum of unloadPageNums)
			this._unloadPage(pageNum);
		
		for (const pageNum of loadPageNums)
			this._loadPage(pageNum);
		
		this._pageNum = pageNum;

		const pageNums = Array.from(this._loadedPageNums)
	    pageNums.sort((a, b) => a - b);
		// console.log(`clip manager loaded pages: [${pageNums.join(', ')}]`);
		// console.log(`clip manager num loaded clips ${this._numLoadedClips}`);

	}
	
	
	/**
	 * Returns an array `[unloadPageNums, loadPageNums]` containing two
	 * arrays of page numbers. `unloadPageNums` contains the numbers of
	 * loaded pages that should be unloaded, and `loadPageNums` contains
	 * the numbers of unloaded pages that should be loaded.
	 */
	_getUpdatePlan(pageNum) {
		throw new Error('_ClipManager._getUpdatePlan not implemented');
	}
	
	
	_unloadPage(pageNum) {

    	if (this._loadedPageNums.has(pageNum)) {
    		
    		// console.log(`clip manager unloading page ${pageNum}...`);
    		
			const start = this.pageStartClipNums[pageNum];
			const end = this.pageStartClipNums[pageNum + 1];
			
			for (let i = start; i < end; i++)
				this._clipLoader.unloadClip(this.clips[i]);
			
    		this._loadedPageNums.delete(pageNum);
    		this._numLoadedClips -= this._getNumPageClips(pageNum);
			
    	}
		
	}
	
	
}


class _SimpleClipManager extends _ClipManager {
	
	
	_getRequiredPageNums(pageNum) {
		return [pageNum];
	}
	
	
	_getUpdatePlan(pageNum) {
		return [[this.pageNum], [pageNum]];
	}
	
	
}


class _PreloadingClipManager extends _ClipManager {
	
	
	/**
	 * The settings used by this class are:
	 * 
	 *     maxNumClips - maximum number of clips kept in memory.
	 *     numPrecedingPreloadedPages - number of preceding pages to preload.
	 *     numFollowingPreloadedPages - number of following pages to preload.
	 */

	
	_getRequiredPageNums(pageNum) {
		
		const pageNums = [pageNum];
				
		const numAlbumPages = this.pageStartClipNums.length - 1;
		for (let i = 0; i < this.settings.numFollowingPreloadedPages; i++) {
			const j = pageNum + i + 1;
			if (j >= numAlbumPages)
				break;
			pageNums.push(j);
		}
		
		for (let i = 0; i < this.settings.numPrecedingPreloadedPages; i++) {
			const j = pageNum - i - 1;
			if (j < 0)
				break;
			pageNums.push(j);
		}
		
		return pageNums;
				
	}
	
	
	_getUpdatePlan(pageNum) {
		const requiredPageNums = this._getRequiredPageNums(pageNum);
		const loadPageNums = this._getLoadPageNums(requiredPageNums);
        const unloadPageNums =
        	this._getUnloadPageNums(requiredPageNums, loadPageNums);
        return [unloadPageNums, loadPageNums];
	}
	
	
	_getLoadPageNums(requiredPageNums) {
		const not_loaded = i => !this._loadedPageNums.has(i);
		return requiredPageNums.filter(not_loaded);
	}
	
	
	_getUnloadPageNums(requiredPageNums, loadPageNums) {
		
		const numAlbumPages = this.pageStartClipNums.length - 1;
		const min = (a, b) => Math.min(a, b);
		const minPageNum = requiredPageNums.reduce(min, numAlbumPages);
		const max = (a, b) => Math.max(a, b);
		const maxPageNum = requiredPageNums.reduce(max, 0);
		
		const numClipsToLoad = this._getNumClipsInPages(loadPageNums)
		const numClipsToUnload = Math.max(
			this._numLoadedClips + numClipsToLoad - this.settings.maxNumClips,
			0);
		
		const pageNums = new Set(this._loadedPageNums);
		const unloadPageNums = [];
		let numClipsUnloaded = 0;
		
		while (numClipsUnloaded < numClipsToUnload) {
			
			const i = this._findMostDistantLoadedPageNum(
				pageNums, minPageNum, maxPageNum);
			
			if (i === null)
				// no more pages that can be unloaded
				
				break;
			
			pageNums.delete(i);
			unloadPageNums.push(i);
			numClipsUnloaded += this._getNumPageClips(i);
			
		}
		
		return unloadPageNums;
		
	}
	
	
	_getNumClipsInPages(pageNums) {
		const numPageClips = pageNums.map(i => this._getNumPageClips(i));
		return numPageClips.reduce((a, v) => a + v, 0);
	}
	
	
	_findMostDistantLoadedPageNum(pageNums, minPageNum, maxPageNum) {
		
		let mostDistantPageNum = null;
		let maxDistance = 0;
		let distance;
		
		for (const i of pageNums) {
			
			if (i < minPageNum)
				distance = minPageNum - i;
			else if (i > maxPageNum)
				distance = i - maxPageNum;
			else
				distance = 0;
			
			if (distance > maxDistance) {
				mostDistantPageNum = i;
				maxDistance = distance;
			}
			
		}
		
		return mostDistantPageNum;
		
	}
	
	
}
	
	

class _ClipViewsLayout {
	
	
	constructor(div, clipViews, settings) {
		this._div = div;
		this._clipViews = clipViews;
		this.settings = settings;
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
    	this._pageStartClipNums = this._paginate();
    }
    
    
    _paginate() {
		throw new Error('_ClipViewsLayout._paginate not implemented');
    }
    
    
	get numPages() {
		let numPages = this._pageStartClipNums.length;
		return numPages == 0 ? numPages : numPages - 1;
	}
	
	
    get pageStartClipNums() {
    	return this._pageStartClipNums;
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
		clipsDiv.style.alignItems = 'flex-start';
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
//	onResize(pageNum) {
//		
//		console.log('NonresizingLayout.onResize');
//		this._checkPageNum(pageNum);
//		
//		// For this layout type resizes are handled by the flexbox layout.
//		
//	}
	
	
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
//	onResize(pageNum) {
//		console.log('ResizingLayout.onResize');
//		this._checkPageNum(pageNum);
//		this._renderClipViews(pageNum);
//	}
	
	
}


function _removeChildren(div) {
    while (div.firstChild)
    	div.removeChild(div.firstChild);
}


function _toCssPercent(x) {
	return x.toFixed(2) + '%';
}


/*

Clip album layout sets clip view time bounds, so clip view
does not have to know anything about layout.

clip album settings:

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
  one spectrogram settings preset that can be used both for clip albums
  and individual clip views? (Perhaps the answer is relative names.)

* How are settings specified? How do plugins specify the settings they
  use? How do they specify preset types?

* How do we create forms for editing settings? To what extent can we
  create them automatically? Can we support their description via YAML?

* Can we implement lookup with composition via dot notation in both
  Python and JavaScript?
  
* Can we support both camel and snake case?

*/


class ClipView {
	
	
	constructor(parent, clip, settings, delegateClass) {
		
		this._parent = parent;
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
	
	
	get clip() {
		return this._clip;
	}
	
	
	get settings() {
		return this._settings;
	}
	
	
	set settings(settings) {
		
		this._settings = settings;
		this._delegate.settings = settings;
		
		if (this._div !== null) {
			this._styleLabel();
			this._stylePlayButton();
			this.render();
		}
		
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
		this._createUiElementsIfNeeded();
		return this._div;
	}
	
	
	get canvas() {
		this._createUiElementsIfNeeded();
		return this._canvas;
	}
	
	
	get label() {
		this._createUiElementsIfNeeded();
		return this._label;
	}
	
	
	get playButton() {
		this._createUiElementsIfNeeded();
		return this._playButton;
	}
	
	
	_createUiElementsIfNeeded() {

		if (this._div === null) {

			this._div = this._createDiv();
			
		    this._canvas = this._createCanvas();
		    
			this._label = this._createLabel();
			this._styleLabel();
			
			this._playButton = this._createPlayButton();
			this._stylePlayButton();
			
		}
		
	}
	
	
	_createDiv() {
		
	    const div = document.createElement('div');
	    
	    div.className = 'clip';
	    
	    // We install event listeners on the div rather than the canvas
	    // since the label and button are children of the div (it does
	    // not seem to work to make them children of the canvas: when
	    // they are they are invisible), and we want to receive mousemove
	    // events (via bubbling) whose targets are the label and the 
	    // button. We listen for mouseenter and mouseleave rather than
	    // mouseover and mouseout since the latter would be delivered to
	    // the div when the mouse moved into and out of it from and to
	    // the label and the button, which we do not want. We only want
	    // to know when the mouse enters and leaves the div from and to
	    // the outside.
	    div.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    div.addEventListener('mousemove', e => this._onMouseMove(e));
	    div.addEventListener('mouseleave', e => this._onMouseLeave(e));
	    
	    return div;
	    
	}
	    
	    
	_createCanvas(div) {
		
	    const canvas = document.createElement('canvas');
	    canvas.className = 'clip-canvas';
	    canvas.addEventListener('click', e => this._onCanvasClick(e));
	    this._div.appendChild(canvas);
	    
	    return canvas;
	    
	}
	
	
	_onMouseEnter(e) {
		this._onMouseEvent(e, 'mouseenter');
	}
	
	
	_onMouseEvent(e, name) {
		
		const text = this._delegate.getMouseText(e, name)
		
		if (text !== null)
			this.label.innerHTML = text;
		else
			this._renderLabel();
		
	}
	
	
	_onMouseMove(e) {
		this._onMouseEvent(e, 'mousemove');
	}
	
	
	_onMouseLeave(e) {
		this._onMouseEvent(e, 'mouseleave');
	}
	
	
	_onCanvasClick(e) {
	
		const parent = this.parent;
		const clipNum = this.clip.num;
		
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
	    
	    /* The following is the code from _startClipSamplesDownload (which
	     * no longer exists) mentioned in the comment above.
	     */
//    const context = new OfflineAudioContext(
//    1, clip.length, clip.sampleRate);
//  const source = context.createMediaElementSource(audio);
//  source.connect(context.destination);
//  context.startRendering().then(audioBuffer =>
//      onAudioDecoded(audioBuffer, clip));

	    
	}
    

	_onPlayButtonClick(e) {
		this.playClip()
	}
	
	
	playClip() {
		
		if (this.clip.audioBuffer != null) {
			// have clip samples
			
			const context = this.parent._audioContext;
			const source = context.createBufferSource();
			source.buffer = this.clip.audioBuffer;
			source.connect(context.destination);
			source.start();
			
		}
		
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
    
    
    /**
     * Responds to a change in the samples of the clip of this view.
     * 
     * This method is called whenever the samples of a clip view's
     * clip change, including when they are loaded from the server
     * and when they are unloaded.
     */
    onClipSamplesChanged() {
        this._delegate.onClipSamplesChanged();
    }

    
    onClipAnnotationsChanged() {
     	this._renderLabel();
    }
    
    
	render() {
		if (this._div !== null) {
		    this._delegate.render();
		    this._renderLabel();
		}
	}
	
	
	_renderLabel() {

	    /*
	     * TODO: Modify clip album settings preset to allow specification
	     * of values of arbitrary annotations (not just the "Classification"
	     * annotation) as label components. The part of the "label"
	     * specification that describes the parts of the label might look
	     * like this:
	     * 
	     *     parts:
	     *         - annotation:
	     *               name: Classification
	     *               hidden_prefixes: [Call.]
	     *         - start_time
	     *         
	     * rather than the current:
	     * 
	     *     classification_included: true
	     *     hidden_clasification_prefixes: [Call.]
	     *     start_time_included: true
	     */
		
		const clip = this.clip;
		const s = this.settings.label;
	
		if (s.visible) {
			
			const labelParts = [];
			
			if (s.classificationIncluded && clip.annotations !== null) {
				
				let annotation = clip.annotations['Classification'];
				
				if (annotation === undefined)
					annotation = 'Unclassified';
				
				else
					for (const prefix of s.hiddenClassificationPrefixes)
						if (annotation.startsWith(prefix))
							annotation = annotation.substr(prefix.length);
				
		        labelParts.push(annotation);
		        
			}
			
			if (s.startTimeIncluded) {
			    
                /*
                 * TODO: Have server tell client if clips are all for
                 * one calendar year or all for one date, and if so for
                 * which year or date, and compact start time display
                 * accordingly. When start times are abbreviated, clip
                 * album should indicate year or date of clips somewhere.
                 */

                const [date, time] = clip.startTime.split(' ');
                
		        if (clipQuery.date === null) {
		            // clips may be for more than one night
		            
		            // include date in start time, but not year part
		            const [_, month, day] = date.split('-');
		            const compactedDate = [month, day].join('-')
		            labelParts.push(compactedDate);
		            
		        } 
		        
		        // always include time in start time
		        const [truncatedTime, _] = time.split('.');
	            labelParts.push(truncatedTime);
		            
			}
			
			this.label.innerHTML =
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
	 * Updates the canvas of this delegate's clip view after the clip's
	 * samples have changed.
	 * 
	 * The canvas is available from this method as  `this.clipView._canvas`,
	 * the clip's audio data are available as `this.clip.audioBuffer`
	 * (a Web Audio `AudioBuffer`), and the clip's samples are available as
	 * `this.clip.samples`, a `Float32Array`.
	 * 
	 * Note that the clip's samples may have changed by becoming unavailable,
	 * in which case `this.clip.audioBuffer` and `this.clip.samples` will
	 * both be `null`.
	 */
	onClipSamplesChanged() {
		throw new Error(
			'ClipViewDelegate.onClipSamplesChanged not implemented');
	}
	
	
	/**
	 * Renders the contents of this delegate's clip view.
	 * 
	 * This method is invoked by a delegate's clip view whenever the
	 * contents of the clip view may need to be rendered, including
	 * when the containing clip album has changed size.
	 */
	render() {
		throw new Error('ClipViewDelegate.render method not implemented.');
	}
	
	
	/**
	 * Gets text to display for the current mouse position.
	 * 
	 * This method is invoked by a delegate's clip view whenever the
	 * mouse enters, leaves, or moves within the view. The argument is
	 * the mouse event that triggered the invocation, along with an
	 * event name that is either "mouseenter", "mouseleave", or
	 * "mousemove". The method can return either text to display
	 * instead of the view's usual label, or `null` to display the
	 * usual label.
	 */
	getMouseText(event, name) {
		return null;
	}
	
	
}


class SpectrogramClipViewDelegate extends ClipViewDelegate {
	
	
    // TODO: Update view in response to settings changes, recomputing
	// as little as possible.
	
	onClipSamplesChanged() {

        const clip = this.clipView.clip;

        if (clip.samples !== null) {
            // have clip samples

//            console.log(
//                `computing and drawing spectrogram for clip ${clip.num}...`);

            const settings = _createLowLevelSpectrogramSettings(
                this.settings.spectrogram, clip.sampleRate);

//            console.log(
//                clip.sampleRate, settings.window.length, settings.hopSize,
//                settings.dftSize);
            
            // Compute spectrogram, offscreen spectrogram canvas, and
            // spectrogram image data and put image data to canvas. The
            // spectrogram canvas and the spectrogram image data have the
		    // same size as the spectrogram. 
            this._spectrogram = _computeSpectrogram(clip.samples, settings);
            this._spectrogramCanvas =
                _createSpectrogramCanvas(this._spectrogram, settings);
            this._spectrogramImageData =
                _createSpectrogramImageData(this._spectrogramCanvas);
		    _computeSpectrogramImage(
                this._spectrogram, this._spectrogramCanvas,
                this._spectrogramImageData, settings);

		    // Draw spectrogram image.
            const canvas = this.clipView.canvas;
            _drawSpectrogramImage(
                clip, this._spectrogramCanvas, canvas, settings);

        } else {
            // do not have clip samples

//            console.log(
//                `freeing spectrogram memory for clip ${clip.num}...`);

            this._spectrogram = null;
            this._spectrogramCanvas = null;
            this._spectrogramImageData = null;

        }

    }

	
	render() {
		// For the time being we do nothing here, since apparently 
		// an HTML canvas can resize images that have been drawn to
		// it automatically. We will need to do something here (or
		// somewhere, anyway) eventually to handle view settings
		// changes, for example changes to spectrogram settings
		// or color map settings.
	}
	
	
	getMouseText(event, name) {
		
		const x = event.clientX;
		const y = event.clientY;
		
	    // The sides of the bounding client rectangle of an HTML element
		// can have non-integer coordinates. We bump them to the nearest
		// integers for comparison to the integer mouse coordinates, and
		// assign time zero to the resulting left coordinate, the clip
		// duration to the right coordinate, the low view frequency to
		// the bottom coordinate, and the high view frequency to the top
		// coordinate.
		const r = this.clipView.div.getBoundingClientRect();
		const left = Math.ceil(r.left);
		const right = Math.floor(r.right);
		const top = Math.ceil(r.top);
		const bottom = Math.floor(r.bottom);
		
		if (x < left || x > right || y < top || y > bottom)
			// mouse outside view
			
			// The mouse is outside of the view for mouseleave events, and
			// (for some reason) even for some mousemove events.
			
			return null;
		
		else {
			// mouse inside view
			
			const clip = this.clipView.clip;
			
			const time = (x - left) / (right - left) * clip.span;
			
			const settings = this.settings.spectrogram;
			const [lowFreq, highFreq] =
				_getFreqRange(settings, clip.sampleRate / 2);
			const deltaFreq = highFreq - lowFreq;
			const freq = highFreq - (y - top) / (bottom - top) * deltaFreq;
			
			return `${time.toFixed(3)} s  ${freq.toFixed(1)} Hz`;
			
		}
		
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


function _createLowLevelSpectrogramSettings(settings, sampleRate) {
    
    const windowSize = Math.round(settings.windowSize * sampleRate);
    const window = createDataWindow('Hann', windowSize);
    const hopSize = Math.round(settings.hopSize * sampleRate);
    const dftSize = _computeDftSize(
        windowSize, settings.dftSizeExponentIncrement);
    
    return {
        window: window,
        hopSize: hopSize,
        dftSize: dftSize,
        referencePower: settings.referencePower,
        lowPower: settings.lowPower,
        highPower: settings.highPower,
        smoothingEnabled: settings.smoothingEnabled,
        timePaddingEnabled: settings.timePaddingEnabled
    };
    
}


function _computeDftSize(windowSize, exponentIncrement) {
    
    const exponent = Math.ceil(Math.log2(windowSize))
    
    if (exponentIncrement === undefined || exponentIncrement < 0)
        exponentIncrement = 0;
    
    return Math.pow(2, exponent + exponentIncrement);
    
}


function _computeSpectrogram(samples, settings) {
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
	// [settings.lowPower, settings.highPower] into the range [255, 0].
	const delta = settings.highPower - settings.lowPower
	const a = -255 / delta;
	const b = 255 * (1. - settings.lowPower / delta);
	
	// Map spectrogram values to pixel values.
	let m = 0;
	for (let i = 0; i < numBins; i++) {
		let k = numBins - 1 - i;
	    for (let j = 0; j < numSpectra; j++) {
			const v = a * spectrogram[k] + b;
			data[m++] = v;
			data[m++] = v;
			data[m++] = v;
			data[m++] = 255;
			k += numBins;
		}
	}
	
	// Write pixel values to spectrogram canvas.
	const context = canvas.getContext('2d');
	context.putImageData(imageData, 0, 0);

}


function _drawSpectrogramImage(clip, spectrogramCanvas, canvas, settings) {

	// Make sure clip view canvas has same size as spectrogram.
	const gramCanvas = spectrogramCanvas;
	if (canvas.width != gramCanvas.width)
	    canvas.width = gramCanvas.width;
	if (canvas.height != gramCanvas.height)
	    canvas.height = gramCanvas.height;
	
	const context = canvas.getContext('2d');
	
	// Draw gray background rectangle.
	context.fillStyle = 'gray';
	context.fillRect(0, 0, canvas.width, canvas.height);
	
	
	// Draw spectrogram from clip spectrogram canvas, stretching as needed.
	
    context.imageSmoothingEnabled = settings.smoothingEnabled;

    const numSpectra = gramCanvas.width;
    const numBins = gramCanvas.height;
    const halfSampleRate = clip.sampleRate / 2.;
    
    // Always draw entire spectrogram duration.
    const sX = 0;
    const sWidth = numSpectra;
    
    const [dX, dWidth] = _getSpectrogramXExtent(
            settings, numSpectra, clip, canvas.width);
        
    // Get view frequency range.
    const [startFreq, endFreq] = _getFreqRange(settings, halfSampleRate);
    
    if (startFreq >= halfSampleRate)
        // view frequency range is above that of spectrogram, so no
        // part of spectrogram will be visible
        
        return;
    
    const sStartFreq = startFreq;
    const sEndFreq = Math.min(endFreq, halfSampleRate);
    
    const sStartFreqY =
        _freqToGramCanvasY(sStartFreq, numBins, halfSampleRate);
    const sEndFreqY = _freqToGramCanvasY(sEndFreq, numBins, halfSampleRate);
    
    // The roles of sStartFreqY and sEndFreqY are reversed from what one
    // might expect in the following since frequency decreases (instead
    // of increasing) with increasing gram image y coordinate.
    const sY = sEndFreqY
    const sHeight = sStartFreqY - sEndFreqY;
    
    const h = canvas.height
    const dStartFreqY = _freqToViewCanvasY(sStartFreq, h, startFreq, endFreq);
    const dEndFreqY = _freqToViewCanvasY(sEndFreq, h, startFreq, endFreq);
    
    const dY = dEndFreqY;
    const dHeight = dStartFreqY - dEndFreqY;
    
    context.drawImage(
        gramCanvas, sX, sY, sWidth, sHeight, dX, dY, dWidth, dHeight);
	
}


function _getSpectrogramXExtent(settings, numSpectra, clip, canvasWidth) {
    
    if (settings.timePaddingEnabled) {
        
        	const sampleRate = clip.sampleRate;
        	const startTime = settings.window.length / 2 / sampleRate;
        	const spectrumPeriod = settings.hopSize / sampleRate;
        	const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
        	const span = (clip.length - 1) / sampleRate;
        	const pixelPeriod = span / canvasWidth;
        	const x = startTime / pixelPeriod;
        	const width = (endTime - startTime) / pixelPeriod;
        	return [x, width];
        	
    } else {
        
        return [0, canvasWidth];
        
    }
    
}


// TODO: Restore the default frequency range from [0, 11025] to
// [0, halfSampleRate] after clip album settings preset changes
// are applied properly.
function _getFreqRange(settings, halfSampleRate) {
	if (settings.frequencyRange !== undefined)
		return settings.frequencyRange;
	else
		return [0, 11025];
}


// TODO: Look into the details of HTML canvas image rendering to
// determine the proper mapping between frequency and gram canvas
// coordinates. I think the simple mapping implemented here is probably
// not the best one, since it assumes that the gram canvas pixel height
// is halfSampleRate / numBins, i.e. (sampleRate / 2) / (dftSize / 2 + 1).
// That is incorrect: the gram canvas pixel height is the DFT bin size,
// sampleRate / dftSize. I suspect that the solution is to put zero hertz
// and half the sample rate in the middles of the bottom and top canvas
// pixels, respectively, rather than at the top and bottom of the canvas.
// The commented-out code below does this.
function _freqToGramCanvasY(freq, numBins, halfSampleRate) {
 
    return numBins * (1. - freq / halfSampleRate);
 
//    const binSize = halfSampleRate / (numBins - 1)
//    return numBins - .5 - freq / binSize
 
}


function _freqToViewCanvasY(freq, canvasHeight, startFreq, endFreq) {
    return canvasHeight * (1. - (freq - startFreq) / (endFreq - startFreq));
}


/*

Questions:

* What is relationship between settings and presets?
* What is relationship between settings and application preferences?
* What is relationship between settings and command interpreter globals?

*/


/*

Annotation settings:

* auto_select_first_page_clip: Boolean
* auto_play_selected_clip: Boolean
* auto_advance_after_annotate_page: Boolean

It might be nice to be able to modify settings with commands, for example
to toggle the above settings. Perhaps the clip album should offer a
"toggle_setting" command? Then one could do something like:

    commands: {
        _toggle_auto_select: [toggle_setting, auto_select_first_page_clip],
        _toggle_auto_play: [toggle_setting, auto_play_selected_clip],
        _toggle_auto_advance: [toggle_setting, auto_advance_after_annotate_page]
    }

*/


/*

Following are some ideas about keybord commands. As of this writing,
inheritance, composite actions, and user-defined actions are not yet
implemented. When thinking about these features, keep in mind that we
want to support editing of multiple annotations with one set of commands.
For example, we might like for some commands to set values for a
"Classification" annotation and others for a "Classification Confidence"
annotation.


_BASIC_KEYBOARD_COMMANDS = {
		
    'commands': {
    	'>': 'show_next_page',
    	'<': 'show_previous_page',
    	'.': 'select_next_clip',
    	',': 'select_previous_clip',
    	'/': 'play_selected_clip'
    	'\': 'clear_buffer_and_locals'
    }

};


_CLASSIFICATION_KEYBOARD_COMMANDS_HEADER = {
		
	'globals': {
		'annotation_name': 'Classification',
		'annotation_scope': 'Selection'
	},

    'actions': {
    
        'annotate': {
		    'args': ['value'],
			'actions': [
			    ['annotate_clips',
			        '<annotation_name>', '<value>', '<annotation_scope>']
			]
		},
		
		'annotate_page': {
		    'args': ['value'],
		    'actions': [
		        ['annotate_clips', '<annotation_name>', '<value>', 'Page']
		    ]
		},
		
	},
	
	'commands': {
    	'#': ['set_local', 'annotation_scope', 'Page'],
    	'_': ['clear_command_and_locals']
	}
		

};


The YAML equivalent of _CLASSIFICATION_KEYBOARD_COMMANDS_HEADER would be:

globals:
    annotation_name: Classification
    annotation_scope: Selection
    
    
actions:

    annotate:
        args: [value]
        actions:
            - [annotate_clips, <annotation_name>, <value>, <annotation_scope>]
           
    annotate_page:
        args: [value]
        actions:
            - [annotate_clips, <annotation_name>, <value>, Page]
            
commands:
    '#': [set_local, annotation_scope, Page]
    '_': [clear_buffer_and_locals]


_CLASSIFICATION_KEYBOARD_COMMANDS = {
	
	// Extension merges mapping items like 'globals' and 'commands'.
	'extends': [
	    'basic_keyboard_commands',
	    'classification_keyboard_commands_header'
	],

    'commands': {
    	
    	'!c': ['set_global', {'annotation_name': 'Classification'}],
    	'!h': ['set_global', {'annotation_name': 'Harold Classification'}],
    	
    	'c': ['annotate_clips', 'Call'],
    	'C': ['annotate_page', 'Call'],
    	'n': ['annotate_clips', 'Noise'],
    	'N': ['annotate_page', 'Noise'],
    	'x': ['annotate_clips', 'Unclassified'],
    	'X': ['annotate_page', 'Unclassified'],

	    '@o': ['auto_annotate_clips', 'MPG Ranch Outside Clip Classifier'],
	    '@O': ['auto_annotate_page', 'MPG Ranch Outside Clip Classifier'],
	    '@c': ['auto_annotate_clips', 'NFC Coarse Clip Classifier'],
	    '@C': ['auto_annotate_page', 'NFC Coarse Clip Classifier'],
	    
    }
    
};

*/

/*

How a command interpreter operates.

A command interpreter executes commands in response to keyboard input.
The interpreter has a repertoire of commands, each with a *name* and an
*action*. The name is a short sequence of characters, typically just
one or two characters in length. The action represents a computation
to be performed when the command is typed, as described in more detail
below.

As keys are typed on the keyboard, the interpreter appends the corresponding
characters to a *command buffer*. As soon as the buffer contains the name
of a command, the intepreter executes the named command's action and
clears the buffer. The interpreter also clears the buffer whenever its
contents are not a prefix of at least one command name, and displays an
appropriate error message. The user can also clear the buffer manually via
a special built-in command.

A command interpreter has a repertoire of *functions* in terms of which
command actions are defined. Each function has a *name* and *parameters*.
An action is specified as a list comprising a function name followed
by function *arguments*, where each argument is the value of one
function parameter. The number of arguments must match the number of
parameters. A single function can be invoked by different actions with
different arguments to accomplish different things. For example, a
function might have a parameter for a label to be applied to items
selected in a user interface, and different actions might all invoke
that one function with different arguments to label the items
differently.

A command interpreter executes actions in the context of an *environment*.
An environment is a set of *variables*, each comprising a *name* and a
*value*. There are two types of variables, *global* and *local*. Once
created, a global variable persists until it is explicitly deleted.
Local variables, however, are more ephemeral, as described below.

An action can refer to a variable by name. When the interpreter is
executing the action and encounters the variable name, it looks the
name up in the environment to find the associated value. [locals,
then globals, then error].

A command interpreter has a number of *built-in* functions that manipulate
the interpreter's command buffer and environment. These functions are:

    * set_global(name, value) - sets one global variable
    * delete_global(name) - deletes one global variable
    * clear_globals() - clears all global variables
    * set_local(name, value) - sets one local variable
    * delete_local(name) - deletes one local variable
    * clear_locals() - clears all global variables
    * clear_command_and_locals() -
          clears the command buffer and all local variables
    
There are two types of functions: *built-in* functions and *regular*
functions. The two types of functions differ in how they interact with
the local environment. The interpreter clears the local variables after
executing a regular function, but not after executing a built-in function.

At this point, at least, the command interpreter does not support composite
actions: it executes exactly one function per action. It also does not
support conditional or repeated execution.

*/


/*

set_global
delete_global
clear_globals

set_local
delete_local
clear_locals

clear_command_and_locals

show_next_page
show_previous_page

select_first_clip
select_next_clip
select_previous_clip

play_selected_clip

toggle_clip_labels

annotate_clips(annotation_value)
annotate_selected_clips(annotation_value)
annotate_page_clips(annotation_value)
annotate_all_clips(annotation_value)

unannotate_clips()
unannotate_selected_clips()
unannotate_page_clips()
unannotate_all_clips()

tag_clips(tag_name)
tag_selected_clips(tag_name)
tag_page_clips(tag_name)
tag_all_clips(tag_name)

untag_clips(tag_name)
untag_selected_clips(tag_name)
untag_page_clips(tag_name)
untag_all_clips(tag_name)


globals:
    annotation_name: Classification
    annotation_scope: Selected
    
commands:

    ">": [show_next_page]
    "<": [show_previous_page]
    ".": [select_next_clip]
    ",": [select_previous_clip]
    "/": [play_selected_clip]
    
    "#": [set_local, annotation_scope, Page]
    "*": [set_local, annotation_scope, All]
    "\": [clear_command_and_locals]
    
    c: [annotate_clips, Call]
    C: [annotate_page_clips, Call]
    n: [annotate_clips, Noise]
    N: [annotate_page_clips, Noise]
    x: [unannotate_clips]
    X: [unannotate_page_clips]
    
    r: [tag_clips, Review]
    u: [untag_clips]
    
*/