'use strict'


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
		return this.clip.span;
	}
	
	
	get div() {
		if (this._div === null) {
			this._div = this._delegate.div;
			this._label = this._createLabel();
		}
		return this._div;
	}
	
	
	_createLabel() {
		const div = this.div;
		const document = div.ownerDocument;
	    const label = document.createElement('p');
	    label.className = 'clip-label';
	    label.innerHTML = (this.clip.index + 1).toString();
	    div.appendChild(label);
	    return label;
	}
	
	
	render() {
		this._delegate.render();
	}
	
	
}


class ClipViewDelegate {
	
	
	constructor(clipView, clip, settings) {
		this._clipView = clipView;
		this._clip = clip;
		this._settings = settings;
		this._div = null;
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
	
	
	get div() {
		if (this._div === null)
			this._div = this._createDiv();
		return this._div;
	}
	
	
	/**
	 * Creates HTML elements for this delegate's clip view.
	 * 
	 * This method creates the root div element of this delegate's
	 * clip view as well as the div's descendants, except for the
	 * label and the play button, which are created by the clip view.
	 */
	_createDiv() {
		throw new Error('ClipViewDelegate._createDiv not implemented.');
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
