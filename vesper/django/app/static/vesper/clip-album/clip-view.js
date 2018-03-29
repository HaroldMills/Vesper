import { CommandInterpreter, RegularFunction }
    from '/static/vesper/clip-album/command-interpreter.js';
import { TimeFrequencyMarkerOverlay }
    from '/static/vesper/clip-album/time-frequency-marker-overlay.js';


export class ClipViewCommandInterpreter extends CommandInterpreter {


    // TODO: Document why we use a separate class for the functions
    // (we can't refer to `this` before invoking `super`).
    constructor(spec) {
        const aux = new _ClipViewCommandInterpreterAux();
        super(spec, aux.functions)
        this._aux = aux;
    }


    get clipView() {
        return this._aux.clipView;
    }


    set clipView(clipView) {
        if (clipView !== this.clipView) {
            this._aux.clipView = clipView;
            if (clipView === null)
                this._clearCommandAndLocals(this._environment);
        }
    }


    handleKey(key) {
        if (this.clipView === null) {
            return [CommandInterpreter.COMMAND_UNRECOGNIZED, key];
        } else {
            return super.handleKey(key);
        }
    }


}


export class _ClipViewCommandInterpreterAux {


    constructor() {
        this._clipView = null;
        this._functions = this._createFunctions();
    }


    _createFunctions() {

        const functionData = [
            ['set_time_frequency_marker', [],
                _ => this.clipView._setTimeFrequencyMarker()],
            ['clear_time_frequency_marker', [],
                _ => this.clipView._clearTimeFrequencyMarker()]
        ]

        return functionData.map(
            args => new RegularFunction(...args));

    }


    get clipView() {
        return this._clipView;
    }


    set clipView(clipView) {
        this._clipView = clipView;
    }


    get functions() {
        return this._functions;
    }


}


export class ClipView {


	constructor(parent, clip, settings, delegateClass) {

		this._parent = parent;
		this._clip = clip;
		this._settings = settings;

		this._delegate = new delegateClass(this, this.clip, this.settings);

		this._div = null;
		this._label = null;
		this._playButton = null;

        // TODO: Delegate should create overlays, according to settings.
		this._overlays = [
            new TimeFrequencyMarkerOverlay(
                this, 'Call Center Time', 'Call Center Freq')
        ];

        this._commandInterpreter = null;

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


	get overlayCanvas() {
	    this._createUiElementsIfNeeded();
	    return this._overlayCanvas;
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


    _setTimeFrequencyMarker() {
        const clip = this.clip;
        console.log(
            'ClipView._setTimeFrequencyMarker', clip.num, clip.id,
            clip.annotations);
    }


    _clearTimeFrequencyMarker() {
        console.log('ClipView._clearTimeFrequencyMarker', this.clip.num);
    }


	_createUiElementsIfNeeded() {

		if (this._div === null) {

			this._div = this._createDiv();

		    this._canvas = this._createCanvas();
		    this._overlayCanvas = this._createOverlayCanvas();

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
        console.log('_onMouseEnter', this.label.innerHTML);
        this.parent.activeView = this;
		this._onMouseEvent(e, 'mouseenter');
	}


	_onMouseEvent(e, name) {

        // this._delegate.onMouseEvent(e, name);

		const mouseText = this._delegate.getMouseText(e, name)

        const activeView = this.parent.activeView;
        const activeText =
            activeView === null ? 'null' : activeView.clip.num.toString();

        console.log('_onMouseEvent', name, mouseText, activeText);

		if (mouseText !== null)
			this.label.innerHTML = mouseText;
		else
			this._renderLabel();

	}


	_onMouseMove(e) {
        this.parent.activeView = this;
		this._onMouseEvent(e, 'mousemove');
	}


	_onMouseLeave(e) {
        this.parent.activeView = null;
		this._onMouseEvent(e, 'mouseleave');
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

        // See note in `_createDiv` method about why we install a click
        // listener on the overlay canvas instead of on the containing div.
        canvas.addEventListener('mouseenter', e => this._onMouseEnter(e));
	    canvas.addEventListener('mousemove', e => this._onMouseMove(e));
	    canvas.addEventListener('mouseleave', e => this._onMouseLeave(e));
        canvas.addEventListener('click', e => this._onOverlayCanvasClick(e));

        this._div.appendChild(canvas);

        return canvas;

	}


    _onOverlayCanvasClick(e) {

        console.log('_onOverlayCanvasClick');

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
        this._resizeOverlayCanvasIfNeeded();
        this._renderOverlays();
     	this._renderLabel();
    }


	render() {
		if (this._div !== null) {
		    this._delegate.render();
		    this._resizeOverlayCanvasIfNeeded();
		    this._renderOverlays();
		    this._renderLabel();
		}
	}


	_renderOverlays() {
        for (const overlay of this.overlays) {
            overlay.render();
        }
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
