import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { Clip } from '/static/vesper/clip-album/clip.js';
import { ClipView } from '/static/vesper/clip-album/clip-view.js';
import { CommandableDelegate, KeyboardInputInterpreter }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { Multiselection } from '/static/vesper/clip-album/multiselection.js';
import { NightRugPlot } from '/static/vesper/clip-album/night-rug-plot.js';
import { PreloadingClipManager }
    from '/static/vesper/clip-album/clip-manager.js';
import { Layout } from '/static/vesper/clip-album/layout.js';


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


// Set of keys that can be used in key bindings.
const _ALLOWED_KEYS = new Set(
	'abcdefghijklmnopqrstuvwxyz' +
	'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
	'`1234567890-=[]\\;\',./' +
	'~!@#$%^&*()_+{}|:"<>?');


const _DEFAULT_KEY_BINDINGS = {

    'interpreter_initialization_commands': [
        ['set_persistent_variable', 'annotation_name', 'Classification'],
        ['set_persistent_variable', 'annotation_scope', 'Selection']
    ],

    'key_bindings': {

        'Clip Album': {
            '>': ['show_next_page'],
    		'<': ['show_previous_page'],
    	    '.': ['select_next_clip'],
    	    ',': ['select_previous_clip'],
    	    '/': ['play_selected_clip']
        }

    }

};


// The maximum number of clips that the _annotateClips function will
// annotate without displaying the wait cursor.
const _ANNOTATION_WAIT_CURSOR_THRESHOLD = 20


function setCursor(name) {
	document.body.style.cursor = name;
}


const _COMMAND_SPECS = [

    ['show_next_page'],
    ['show_previous_page'],

    ['select_first_clip'],
    ['select_next_clip'],
    ['select_previous_clip'],

    ['play_selected_clip'],

    ['toggle_clip_labels'],
    ['toggle_clip_overlays'],

    ['annotate_clips', 'annotation_value'],
    ['annotate_selected_clips', 'annotation_value'],
    ['annotate_page_clips', 'annotation_value'],
    ['annotate_all_clips', 'annotation_value'],

    ['unannotate_clips'],
    ['unannotate_selected_clips'],
    ['unannotate_page_clips'],
    ['unannotate_all_clips'],

];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class ClipAlbum {


	constructor(
		    elements, clips, recordings, solarEventTimes, clipViewClasses,
            settings = null, keyBindings = null) {

		this._elements = elements;
		this._clips = this._createClips(clips);

        // It's important to set the clip view class before the commands,
        // since setting the commands creates a new command interpreter,
        // a process that accesses the clip view class.
        this._clipViewClasses = clipViewClasses;
        this._clipViewClass = this.clipViewClasses[settings.clipViewType];

		this._settings = settings === null ? _DEFAULT_SETTINGS : settings;

        this._commandableDelegate = _commandableDelegate;

        // This creates the keyboard input interpreter.
		this.keyBindings =
            keyBindings === null ? _DEFAULT_KEY_BINDINGS : keyBindings;

		this._clipViews = this._createClipViews(this.settings);

        this._resizeThrottle = new _WindowResizeThrottle(this);

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
		this._clipManager = new PreloadingClipManager(
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
		return new Clip(clipNum, ...clipInfo);
	}


	_createClipViews(settings) {

        const viewSettings = settings.clipView;
        const clipViews = new Array(this.clips.length);

		for (const [i, clip] of this.clips.entries()) {
			clipViews[i] = new this.clipViewClass(this, clip, viewSettings);
			clip.view = clipViews[i];
		}

		return clipViews;

	}


	_createLayout(settings) {
		const layoutClass = Layout.classes[settings.layoutType];
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
		    this._resizeClipViewOverlayCanvasesIfNeeded();
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


	/*
	 * We would like for the size of a clip view overlay canvas to track
	 * its client size (i.e. its size on the screen), so that the canvas
	 * contents are not degraded by resampling when they are drawn to the
	 * screen. Ideally, we would accomplish this by listening for resize
	 * events from the canvas, and resizing the canvas and rerendering its
	 * contents whenever its client size changes. As of this writing,
	 * however, there is no way to listen for such resize events (but see
	 * the proposal https://wicg.github.io/ResizeObserver). As a partial
	 * workaround, we implement this method and attempt to call it whenever
	 * canvas resizes might be needed, for example when the window containing
	 * a clip album resizes, or when the album navigates from one page to
	 * another.
	 */
    _resizeClipViewOverlayCanvasesIfNeeded() {

        const clipViews = this._clipViews;
        const [startNum, endNum] =
            this._layout.getPageClipNumRange(this.pageNum);

        for (let i = startNum; i < endNum; i++) {
            const clipView = clipViews[i];
            clipView.resizeOverlayCanvasIfNeeded();
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
			const color =
			    selection.contains(i) ? outline.color : 'transparent';
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


	get clipViewClasses() {
		return this._clipViewClasses;
	}


    get clipViewClass() {
        return this._clipViewClass;
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
			paginationChanged = !ArrayUtils.arraysEqual(
				this._layout.pageStartClipNums, oldPageStartClipNums);

		}

		// Get new page number of clip that was first on old page.
		const newPageNum = this._layout.getClipPageNum(oldFirstClipNum);

		return [paginationChanged, newPageNum];

	}


	get keyBindings() {
		return this._keyBindings;
	}


	set keyBindings(keyBindings) {
        this._keyBindings = keyBindings;
        this._keyboardInputInterpreter =
            this._createKeyboardInputInterpreter(keyBindings);
    }


    _createKeyboardInputInterpreter(keyBindings) {

        const oldInterpreter = this._keyboardInputInterpreter;
        const newInterpreter = new KeyboardInputInterpreter(keyBindings);

        if (oldInterpreter === undefined) {
            // did not already have a keyboard input interpreter

            newInterpreter.pushCommandable(this);

        } else {
            // already had a keyboard input interpreter

            // I'm not sure we'll ever need this, since I'm not sure
            // we'll ever create a new interpreter when the mouse is
            // over a clip view, but just in case...

            const commandables = [];

            // Pop all commandables from old interpreter into `commandables`.
            while (true) {
                const commandable = oldInterpreter.popCommandable();
                if (commandable === undefined)
                    break;
                else
                    commandables.push(commandable);
            }

            // Push all commandables to new interpreter.
            while (commandables.length !== 0)
                newInterpreter.pushCommandable(commandables.pop());

        }

        return newInterpreter;

    }


    pushCommandable(commandable) {
        this._keyboardInputInterpreter.pushCommandable(commandable);
    }


    popCommandable() {
        return this._keyboardInputInterpreter.popCommandable();
    }


    _toggleClipLabels() {
        this.settings.clipView.label.visible =
			!this.settings.clipView.label.visible;
		this._updateClipViewSettings(this.settings);
	}


	_toggleClipOverlays() {
	    this.settings.clipView.overlays.visible =
	        !this.settings.clipView.overlays.visible;
	    this._updateClipViewSettings(this.settings);
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


	_annotatePageClips(name, value) {
		const [startClipNum, endClipNum] =
			this.getPageClipNumRange(this.pageNum);
		const clipNums = ArrayUtils.rangeArray(startClipNum, endClipNum);
		const clips = clipNums.map(i => this.clips[i]);
		this._annotateClips(name, value, clips);
	}


	_annotateAllClips(name, value) {
		this._annotateClips(name, value, this.clips);
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
	    if (e.ctrlKey || e.altKey || e.metaKey || !_ALLOWED_KEYS.has(e.key))
	    	return;

//		console.log(
//			`onKeyPress "${e.key}"`,
//			e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);

		// Prevent client from doing whatever it might normally do
		// in response to the pressed key.
		e.preventDefault();

        let status, name;

        try {
            [status, name] = this._keyboardInputInterpreter.handleKey(e.key);
        } catch (e) {
            window.alert(e.message);
        }

        if (status === KeyboardInputInterpreter.KEY_SEQUENCE_UNRECOGNIZED)
            window.alert(`Unrecognized key sequence "${name}".`);

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


    // Commandable methods and command execution methods.


    get commandableName() {
        return 'Clip Album';
    }


    hasCommand(commandName) {
        return this._commandableDelegate.hasCommand(commandName);
    }


    executeCommand(command, env) {
        this._commandableDelegate.executeCommand(command, this, env);
    }


    _executeShowNextPageCommand(env) {
        this._showNextPage();
    }


    _executeShowPreviousPageCommand(env) {
        this._showPreviousPage();
    }


    _executeSelectFirstClipCommand(env) {
        this._selectFirstClip();
    }


    _executeSelectNextClipCommand(env) {
        this._selectNextClip();
    }


    _executeSelectPreviousClipCommand(env) {
        this._selectPreviousClip();
    }


    _executePlaySelectedClipCommand(env) {
        this._playSelectedClip();
    }


    _executeToggleClipLabelsCommand(env) {
        this._toggleClipLabels();
    }


    _executeToggleClipOverlaysCommand(env) {
        this._toggleClipOverlays();
    }


    _executeAnnotateClipsCommand(env) {

		const scope = env.getRequired('annotation_scope');

		switch (scope) {

		case 'Selection':
			this._executeAnnotateSelectedClipsCommand(env);
			break;

		case 'Page':
			this._executeAnnotatePageClipsCommand(env);
			break;

		case 'All':
			this._executeAnnotateAllClipsCommand(env);
			break;

		default:
			window.alert(`Unrecognized annotation scope "${scope}".`);

		}

	}


    _executeAnnotateSelectedClipsCommand(env) {

		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotateSelectedClips(name, value);

		// TODO: Optionally play selected clip.
		this._selectNextClip();

	}


	_executeAnnotatePageClipsCommand(env) {

		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotatePageClips(name, value);

		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.

	}


	_executeAnnotateAllClipsCommand(env) {
		const name = env.getRequired('annotation_name');
		const value = env.getRequired('annotation_value');
		this._annotateAllClips(name, value);
	}


    _executeUnannotateClipsCommand(env) {

		const scope = env.getRequired('annotation_scope');

		switch (scope) {

		case 'Selection':
			this._executeUnannotateSelectedClipsCommand(env);
			break;

		case 'Page':
			this._executeUnannotatePageClipsCommand(env);
			break;

		case 'All':
			this._executeUnannotateAllClipsCommand(env);
			break;

		default:
			window.alert(`Unrecognized annotation scope "${scope}".`);

		}

	}


	_executeUnannotateSelectedClipsCommand(env) {

		const name = env.getRequired('annotation_name');
		this._annotateSelectedClips(name, null);

		// TODO: Optionally play selected clip.
		this._selectNextClip();

	}


	_executeUnannotatePageClipsCommand(env) {

		const name = env.getRequired('annotation_name');
		this._annotatePageClips(name, null)

		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.

	}


	_executeUnannotateAllClipsCommand(env) {
		const name = env.getRequired('annotation_name');
		this._annotateAllClips(name, null);
	}


}


class _WindowResizeThrottle {


    constructor(clipAlbum) {
        this.clipAlbum = clipAlbum;
        this._resizing = false;
        window.addEventListener('resize', () => this.onResize());
    }


    onResize() {
        if (!this._resizing) {
            this._resizing = true;
            this.clipAlbum._resizeClipViewOverlayCanvasesIfNeeded();
            this._resizing = false;
        }
    }


}


function _scrollToTop() {
	window.scrollTo(0, 0);
}


function _scrollToBottom() {
	window.scrollTo(0, document.body.scrollHeight);
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
