export class ClipView {


	constructor(clipAlbum, clip, settings) {

	    settings = _updateSettingsIfNeeded(settings);
	    
		this._clipAlbum = clipAlbum;
		this._clip = clip;
		this._settings = settings;

		this._div = null;
		this._label = null;
		this._playButton = null;

        this._overlays = [];

	}


	get clipAlbum() {
		return this._clipAlbum;
	}


	get clip() {
		return this._clip;
	}


	get settings() {
		return this._settings;
	}


	set settings(settings) {

        settings = _updateSettingsIfNeeded(settings);
        
		this._settings = settings;

		if (this._div !== null) {
			this._styleLabel();
			this._stylePlayButton();
            this._updateCanvas();
			this.render();
		}

	}


	get commandableName() {
		return 'Clip View';
	}


    hasCommand(commandName) {
		return false;
	}


    executeCommand(command, env) {
		throw new Error('The ClipView class does not support any commands.');
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


	get overlayCanvas() {
	    this._createUiElementsIfNeeded();
	    return this._overlayCanvas;
	}


    get lastMouseEvent() {
		this._createUiElementsIfNeeded();
		return this._lastMouseEvent;
	}


	get label() {
		this._createUiElementsIfNeeded();
		return this._label;
	}


	get playButton() {
		this._createUiElementsIfNeeded();
		return this._playButton;
	}


	get overlays() {
	    return this._overlays;
	}


	_createUiElementsIfNeeded() {

		if (this._div === null) {

			this._div = this._createDiv();

		    this._canvas = this._createCanvas();
		    this._overlayCanvas = this._createOverlayCanvas();
			this._lastMouseEvent = null;

			this._label = this._createLabel();
			this._styleLabel();

			this._playButton = this._createPlayButton();
			this._stylePlayButton();

		}

	}


	_createDiv() {

	    const div = document.createElement('div');

	    div.className = 'clip';

	    // We install some mouse event listeners on the div rather than
        // the overlay canvas (which is on top of the regular canvas)
	    // since the label and button are children of the div (it does
	    // not seem to work to make them children of the overlay canvas:
        // when they are they are invisible), and we want to receive
        // mousemove events (via bubbling) whose targets are the label
        // and the button. We also listen for mouseenter and mouseleave
        // rather than mouseover and mouseout since the latter would be
        // delivered to the div when the mouse moved into and out of it
        // from and to the label and the button, which we do not want.
        // We only want to know when the mouse enters and leaves the div
        // from and to the outside.
        //
        // Note that we do not install a click listener on the div
        // since we do not want to receive click events for the label
        // and the play button. Instead, we install a click listener
        // on the overlay canvas when we create that. Then we receive
        // events for clicks on the parts of the overlay canvas that
        // are not under the label or the play button.
	    // div.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    // div.addEventListener('mousemove', e => this._onMouseMove(e));
	    // div.addEventListener('mouseleave', e => this._onMouseLeave(e));

	    return div;

	}


	_onMouseEnter(e) {
		this._onMouseEvent(e);
		this._pushCommandables();
	}


    _pushCommandables() {
        this.clipAlbum.pushCommandable(this);
		for (let i = this.overlays.length - 1; i >= 0; i--)
		    this.clipAlbum.pushCommandable(this.overlays[i]);
    }


	_onMouseEvent(e) {

        this._lastMouseEvent = e;

        // We must explicitly test for `mouseleave` in the following
        // since the mouse position is (surprisingly) sometimes inside
        // the view for such events. Even is the mouse event is not
        // `mouseleave` we still call `_mouseInside` since we have
        // found (again, surprisingly) that the mouse position is
        // sometimes outside the view for `mousemove` events.
        
        if (e.type === 'mouseleave' || !this._mouseInside(e)) {
            // mouse is outside of view
            
            this._renderLabel();
            
        } else {
            // event is not mouseleave
            
    		const mouseText = this.getMouseText(e)
    
    		if (mouseText !== null) 
    			this.label.textContent = mouseText;
    		else
    			this._renderLabel();
    		
        }

	}


    _mouseInside(e) {
        const x = e.clientX;
        const y = e.clientY;
        const r = this.div.getBoundingClientRect();
        return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
    }
    
    
    /**
	 * Gets text to display for the current mouse position.
	 *
	 * This method is invoked whenever the mouse enters, leaves, or
     * moves within a clip view. The argument is the mouse event that
     * triggered the invocation. The method can return either text to
	 * display instead of the view's usual label, or `null` to display
	 * the usual label.
	 */
	getMouseText(event) {
		return null;
	}


	_onMouseMove(e) {
		this._onMouseEvent(e);
	}


	_onMouseLeave(e) {
        this._popCommandables();
		this._onMouseEvent(e);
	}


    _popCommandables() {
		const n = 1 + this.overlays.length;
		for (let i = 0; i < n; i++)
		    this.clipAlbum.popCommandable();
	}


    handleKeyPress(e) {
        console.log('ClipView.handleKeyPress', e.key);
        return (e.key === 'c' || e.key === 'm');
    }


    _createCanvas(div) {

	    const canvas = document.createElement('canvas');
	    canvas.className = 'clip-canvas';
	    this._div.appendChild(canvas);

	    return canvas;

	}


    _createOverlayCanvas(div) {

        const canvas = document.createElement('canvas');
        canvas.className = 'clip-overlay-canvas';

        canvas.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    canvas.addEventListener('mousemove', e => this._onMouseMove(e));
	    canvas.addEventListener('mouseleave', e => this._onMouseLeave(e));
	    
        // See note in `_createDiv` method about why we install a click
        // listener on the overlay canvas instead of on the containing div.
	    if (!this.clipAlbum.readOnly)
            canvas.addEventListener(
                'click', e => this._onOverlayCanvasClick(e));

        this._div.appendChild(canvas);

        return canvas;

	}


    _onOverlayCanvasClick(e) {

		const clipAlbum = this.clipAlbum;
		const clipNum = this.clip.num;

		if (e.shiftKey)
			clipAlbum.extendSelection(clipNum);
		else if (e.ctrlKey || e.metaKey)
			clipAlbum.toggleClipSelectionState(clipNum);
		else
			clipAlbum.selectClip(clipNum);

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
        button.setAttribute('data-bs-toggle', 'tooltip');
        button.setAttribute('title', 'Play clip');
	    this._div.appendChild(button);

	    const icon = document.createElement('i');
	    icon.classList.add('bi-play-fill', 'clip-play-button-icon');
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


	async playClip(rate = 1) {
		const buffer = this.clip.audioBuffer;
		const context = this.clipAlbum._audioContext;
        await playAudioBuffer(buffer, context, rate);
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
        this._updateCanvas()
    }


    _updateCanvas() {
        throw new Error('ClipView._updateCanvas method not implemented.');
    }
    
    
    onClipMetadataChanged() {
        this._resizeOverlayCanvasIfNeeded();
        this._renderOverlays();
     	this._renderLabel();
    }


	render() {
		if (this._div !== null) {
            // TODO: Do we need to resize canvas if needed here?
		    this._render();
		    this._resizeOverlayCanvasIfNeeded();
		    this._renderOverlays();
		    this._renderLabel();
		}
	}


	_render() {
		throw new Error('ClipView._render method not implemented.');
	}


	_renderOverlays() {
		this._clearOverlayCanvas();
		if (this.settings.overlays.visible) {
            for (const overlay of this.overlays)
                overlay.render();
		}
	}


    _clearOverlayCanvas() {
		const canvas = this.overlayCanvas;
		const context = canvas.getContext('2d');
		context.clearRect(0, 0, canvas.width, canvas.height);
	}


	_resizeOverlayCanvasIfNeeded() {

	    const canvas = this.overlayCanvas;
	    const clientWidth = canvas.clientWidth;
	    const clientHeight = canvas.clientHeight;

	    const resizeNeeded =
	        clientWidth != 0 && clientHeight != 0 &&
	        (canvas.width != clientWidth || canvas.height != clientHeight)

	    if (resizeNeeded) {
	        canvas.width = clientWidth;
	        canvas.height = clientHeight;
	    }

	    return resizeNeeded;

	}


	resizeOverlayCanvasIfNeeded() {
	    if (this._resizeOverlayCanvasIfNeeded()) {
	        this._renderOverlays();
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

				let annotation = clip.annotations.get('Classification');

				if (annotation === undefined)
					annotation = 'Unclassified';

				else
					for (const prefix of s.hiddenClassificationPrefixes)
						if (annotation.startsWith(prefix))
							annotation = annotation.substr(prefix.length);

		        labelParts.push(annotation);

			}

			if (s.startTimeIncluded) {
				const time = this.clipAlbum._formatDateTime(clip.startTime);
				labelParts.push(time);
			}

            if (s.detectorScoreIncluded && clip.annotations !== null) {

                const annotation = clip.annotations.get('Detector Score');

                if (annotation !== undefined) {
                    const score =
                        Math.round(parseFloat(annotation).toString());
                    labelParts.push(score);
                }

            }
            
            if (s.classifierScoreIncluded && clip.annotations !== null) {
                
                const annotation = clip.annotations.get('Classifier Score');
                
                if (annotation !== undefined) {
                    const score =
                        Math.round(parseFloat(annotation).toString());
                    labelParts.push(score);
                }
            }

            const label = this.label;
            label.textContent = labelParts.join(' ');
            
            if (clip.tags !== null && clip.tags.length !== 0) {
                // clip has one or more tags
                
                // Append space to label text if there is any, to
                // separate it from tags.
                if (label.textContent.length !== 0)
                    label.textContent += ' ';
                
                // Get clip tags, sorted by name.
                const tags = Array.from(clip.tags).sort();
                
                // For each tag, append appropriately-colored tag icon
                // to label.
                for (const tag of tags) {
                    
                    // Create span that displays a tag icon.
                    const icon = document.createElement('i');
                    icon.className = 'bi-tag-fill';
                    
                    // Set color.
                    const color = this.clipAlbum.getTagColor(tag);
                    icon.style.color = color;
                    
                    // Set tooltip.
                    icon.setAttribute('data-bs-toggle', 'tooltip');
                    icon.setAttribute('title', tag);
                    
                    label.appendChild(icon);
                    
                }
                
            }
            
		}
        
	}
    
}


/**
 * Updates clip view settings if needed.
 * 
 * This function provides a certain amount of backwards compatibility
 * with old clip album settings presets.
 */
function _updateSettingsIfNeeded(settings) {
    
    // Note that this would not be needed if we had default settings.
    if (settings.overlays === undefined)
        settings.overlays = {'visible': true};
    
    return settings;
    
}


function playAudioBuffer(buffer, audioContext, rate = 1) {

	return new Promise((resolve, reject) => {

		if (buffer !== null) {
			// have audio samples

			const source = audioContext.createBufferSource();
			source.buffer = buffer;

			if (rate != 1)
			    source.playbackRate.value = rate;
			
			source.addEventListener('ended', resolve);

			source.connect(audioContext.destination);
			source.start();

		}

	});

}
