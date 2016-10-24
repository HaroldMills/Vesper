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


const _clipViewClasses = {
	'Demo': DemoClipView
}


const _layoutClasses = {
	'Nonuniform Nonresizing Clip Views': NonuniformNonresizingClipViewsLayout,
	'Nonuniform Resizing Clip Views': NonuniformResizingClipViewsLayout
}


class ClipCollectionView {
	
	
	constructor(div, clips, settings) {
		
		this._div = div;
		this._clips = clips;
		this._settings = settings;
		this._pageNum = 0;
		
		this._clipViews = this._createClipViews(settings);
		this._layout = this._createLayout(settings);
		
		this._update();
		
	}
	
	
	_createClipViews(settings) {
		const viewClass = _clipViewClasses[settings.clipViewType];
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
