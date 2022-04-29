import { DateTime, IANAZone }
    from '/static/third-party/luxon-2.2.0/luxon.min.js';

import { ArrayUtils } from '/static/vesper/util/array-utils.js';
import { Clip, CLIP_LOAD_STATUS } from '/static/vesper/clip-album/clip.js';
import { ClipAlbumUtils } from '/static/vesper/clip-album/clip-album-utils.js';
import { CommandableDelegate, KeyboardInputInterpreter }
    from '/static/vesper/clip-album/keyboard-input-interpreter.js';
import { Layout } from '/static/vesper/clip-album/layout.js';
import { Multiselection } from '/static/vesper/clip-album/multiselection.js';
import { NightRugPlot } from '/static/vesper/clip-album/night-rug-plot.js';
import { NULL_CHOICE } from '/static/vesper/ui-constants.js';
import { PausingIterator, PausingIteratorState }
    from '/static/vesper/util/pausing-iterator.js';
import { PreloadingClipManager }
    from '/static/vesper/clip-album/clip-manager.js';
import { SpectrogramClipView }
    from '/static/vesper/clip-album/spectrogram-clip-view.js';
import { ViewUtils } from '/static/vesper/view/view-utils.js';


// This function is derived from code provided by the Django project at
// https://docs.djangoproject.com/en/3.2/ref/csrf/.
function getCookieValue(name) {
    
    let value = null;
    
    if (document.cookie && document.cookie !== '') {
        
        const cookies = document.cookie.split(';');
        
        for (let i = 0; i < cookies.length; i++) {
            
            const cookie = cookies[i].trim();
            
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                value = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
            
        }
        
    }
    
    // console.log(`getCookieValue: ${name} ${value}`);
    
    return value;
    
}


// Django CSRF token to include in HTTP requests (e.g. POST) that can
// modify the server state.
const _CSRF_TOKEN = getCookieValue('csrftoken');


const _DEFAULT_TAG_COLORS = [
    'DarkOrange',
    'Magenta',
    'Green',
    'Red',
    'Blue',
    'Brown',
    'Black'
];


class _TagColors {
    
    
    constructor(settings) {
        
        // Initialize map from tags to colors from tag colors setting.
        const entries = this._getSetting(settings, 'clipView.tags.colors');
        this._colors = entries === undefined ? new Map() : new Map(entries);
        
        // Get set of colors that appear in tag colors setting.
        const colors = new Set(this._colors.values());
        
        // Get default colors that appear in tag colors setting.
        const usedColors = _DEFAULT_TAG_COLORS.filter(c => colors.has(c));
            
        // Get default colors that do not appear in tag colors setting.
        const unusedColors = _DEFAULT_TAG_COLORS.filter(c => !colors.has(c));
            
        // Create array of default colors ordered so that colors that
        // appear in tag colors setting precede those that don't.
        this._defaultColors = usedColors.concat(unusedColors);
        
        // Set next default color index to that of first default color
        // that does not appear in tag colors setting.
        this._nextIndex = usedColors.length;
        
    }
    
    
    // TODO: Consider using something like the following more widely.
    /**
     Returns the value of a setting, or `undefined` if there is no such
     setting.
     */
    _getSetting(settings, name) {
        
        const parts = name.split('.');
        
        let s = settings;
        
        for (const part of parts) {
            
            s = s[part];
            
            if (s === undefined)
               return undefined;
               
        }
        
        return s;
        
    }
    
    
    /**
     Gets the color of the specified tag.
     
     If a color is specified for the tag in the clip album settings from
     which this object was constructed, that color is returned. Otherwise
     one of the default colors is returned.
     */
    getTagColor(tag) {
        
        let color = this._colors.get(tag);
        
        if (color === undefined) {
            // tag color unknown
            
            // Choose the next default color for this tag.
            color = this._defaultColors[this._nextIndex];
            
            // Remember choice.
            this._colors.set(tag, color);
            
            // Increment next default color index with wraparound.
            this._nextIndex =
                (this._nextIndex + 1) % this._defaultColors.length;
                
        }
        
        return color;
        
    }
    
    
}


/*
 * TODO: Client should perform only those display pipeline functions that
 * are needed to update the display after a settings change. For example
 * it should not recompute spectrograms after a color map or layout change.
 */


const _FALLBACK_SETTINGS = {

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
			windowSize: 100,
			hopSize: 20,
			referencePower: 1e-9,
			lowPower: 10,
			highPower: 100,
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


const _FALLBACK_KEY_BINDINGS = {

    interpreterInitializationCommands: [
        ['set_persistent_variable', 'annotation_name', 'Classification'],
        ['set_persistent_variable', 'annotation_scope', 'Selection']
    ],

    keyBindings: {

        'Clip Album': {
            '>': ['show_next_page'],
    		'<': ['show_previous_page'],
    	    '.': ['select_next_clip'],
    	    ',': ['select_previous_clip'],
    	    '/': ['play_selected_clip'],
        }

    }

};


// The maximum number of clips that the _editClipMetadata function will
// edit without displaying the wait cursor.
const _CLIP_EDIT_WAIT_CURSOR_THRESHOLD = 20


function setCursor(name) {
	document.body.style.cursor = name;
}


const _COMMAND_SPECS = [

    ['show_next_page'],
    ['show_previous_page'],

    ['start_page_auto_advance'],
    ['stop_page_auto_advance'],
    ['toggle_page_auto_advance'],
    ['accelerate_page_auto_advance'],
    ['decelerate_page_auto_advance'],

    ['select_first_clip'],
    ['select_next_clip'],
    ['select_previous_clip'],

    ['start_clip_auto_advance'],
    ['stop_clip_auto_advance'],
    ['toggle_clip_auto_advance'],
    ['accelerate_clip_auto_advance'],
    ['decelerate_clip_auto_advance'],

    ['play_selected_clip'],
    ['play_selected_clip_at_rate', 'playback_rate'],

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
    
    ['tag_clips', 'tag'],
    ['tag_selected_clips', 'tag'],
    ['tag_page_clips', 'tag'],
    ['tag_all_clips', 'tag'],
    
    ['untag_clips', 'tag'],
    ['untag_selected_clips', 'tag'],
    ['untag_page_clips', 'tag'],
    ['untag_all_clips', 'tag'],
    
    ['go_to_next_date'],
    ['go_to_previous_date'],
    ['go_to_clip_calendar'],
    
    ['set_clip_album_settings_preset', 'preset_path'],
    ['set_clip_album_commands_preset', 'preset_path'],

];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


export class ClipAlbum {


    constructor(state) {
        
        // console.log(`'${state.clipFilter.date}':`);
        
        this._readOnly = state.archiveReadOnly;
        this._clipFilter = state.clipFilter;
        this._clips = state.clips.map(_parseClip);
        this._recordings = state.recordings.map(_parseRecording);
        this._solarEventTimes = _parseSolarEventTimes(state.solarEventTimes);
        this._timeZone = new IANAZone(state.timeZoneName);
            
		this._dateTimeFormatOptions = this._getDateTimeFormatOptions();

        this._settingsPresets = state.settingsPresets;
        [this._settings, this._settingsPresetPath] =
            this._getSettingsPreset(state.settingsPresetPath);
        
        this._keyBindingsPresets = state.keyBindingsPresets;
        [this._keyBindings, this._keyBindingsPresetPath] =
            this._getKeyBindingsPreset(state.keyBindingsPresetPath);
        
        this._initUiElements();
        
        // It's important to set the clip view class before creating
        // the keyboard input interpreter, since creating the
        // interpreter requires the clip view class.
        this._clipViewClasses = {
            'Spectrogram': SpectrogramClipView
        };
        this._clipViewClass = this.clipViewClasses[this.settings.clipViewType];
        
        this._commandableDelegate = _commandableDelegate;
        
        this._keyboardInputInterpreter =
            this._createKeyboardInputInterpreter(this.keyBindings);

        this._tagColors = new _TagColors(this.settings);
        
        this._clipViews = this._createClipViews(this.settings);

        this._resizeThrottle = new _WindowResizeThrottle(this);

        this._layout = this._createLayout(this.settings);
        
        this._rugPlot = this._createRugPlot(state);

        // We use a Web Audio `AudioContext` object to play clips.
        this._audioContext = new AudioContext();

        this._clipManager = this._createClipManager();

        this._pageIterator = this._createPageAutoAdvanceIterator();

        this._clipIterator = this._createClipAutoAdvanceIterator();

        this._setPageNum(state.pageNum - 1);
        
        this._initUrlAndHistory();
        
    }
    
    
    // TODO: Have clip album figure out if clips are all for one calendar
    // year or all for one date, and if so for which year or date, and
    // choose `DateTime` format accordingly. Display date information
    // (i.e. year or date) missing from displayed start times in clip
    // album title. Make it very easy to obtain full clip information,
    // including station, sensor, and complete start time including time
    // zone, e.g. in tooltips, a footer, or individual clip views.


	_getDateTimeFormatOptions() {

		if (this._isSingleDateClipAlbum()) {

			return {
				includeDate: false,
				includeHourLeadingZero: false,
				includeMillisecond: false
			};

		} else {

			return {
				includeYear: false,
				includeMillisecond: false
			};

		}

	}


    _isSingleDateClipAlbum() {
        return this._clipFilter.date !== null;
    }


    _formatDateTime(time) {
        return ClipAlbumUtils.formatDateTime(
        	time, this.timeZone, this._dateTimeFormatOptions);

    }
    
    
    _getSettingsPreset(presetPath) {
        return _getPreset(
            presetPath, this._settingsPresets, _FALLBACK_SETTINGS,
            'Clip Album Settings');      
    }
    
    
    _getKeyBindingsPreset(presetPath) {
        return _getPreset(
            presetPath, this._keyBindingsPresets, _FALLBACK_KEY_BINDINGS,
            'Clip Album Commands');      
        
    }
    
    
	_initUiElements() {
	    
        this._clipsDiv = document.getElementById('clips');
        
	    // previous page button
	    const prevButton = document.getElementById('go-to-previous-page-button');
	    prevButton.addEventListener(
	        'click', e => this._onGoToPreviousPageButtonClick(e));
 
	    // next page button
        const nextButton = document.getElementById('go-to-next-page-button');
        nextButton.addEventListener(
            'click', e => this._onGoToNextPageButtonClick(e));
        
        // set clip filter button
        const filterButton = document.getElementById('set-clip-filter-button');
        const filterModal = this._getSetClipFilterModal();
        filterButton.addEventListener('click', _ => filterModal.show());

        this._initSetClipFilterModal();
        this._initGoToPageModal();
        this._initSetPresetsModal();
        
        // go to next date anchor
        const nextAnchor =
            document.getElementById('go-to-next-date-anchor');
        if (nextAnchor !== null)
            nextAnchor.addEventListener(
                'click', e => this._onGoToNextDateAnchorClick(e));

        // go to previous date anchor
        const prevAnchor =
            document.getElementById('go-to-previous-date-anchor');
        if (prevAnchor !== null)
            prevAnchor.addEventListener(
                'click', e => this._onGoToPreviousDateAnchorClick(e));

        // go to clip calendar anchor
        const clipCalendarAnchor =
            document.getElementById('go-to-clip-calendar-anchor');
        if (clipCalendarAnchor !== null)
            clipCalendarAnchor.addEventListener(
                'click', e => this._onGoToClipCalendarAnchorClick(e));

        this._installKeyPressEventListener();

	}
	
	
	_onGoToPreviousPageButtonClick(event) {
	    this.pageNum -= 1;
	}
	

	_onGoToNextPageButtonClick(event) {
	    this.pageNum += 1;
	}
	
	
    _getSetClipFilterModal() {
        const modalDiv = document.getElementById('set-clip-filter-modal');
        return bootstrap.Modal.getOrCreateInstance(modalDiv);
    }
    
    
    _initSetClipFilterModal() {
        const button =
            document.getElementById('set-clip-filter-modal-ok-button');
        button.addEventListener(
            'click', e => ViewUtils.onSetClipFilterModalOkButtonClick(e));
    }
    
    
    _initGoToPageModal() {
        
        // Set up modal event listeners.
        const modal = document.getElementById('go-to-page-modal');
        modal.addEventListener(
            'show.bs.modal', e => this._onGoToPageModalShow());
        modal.addEventListener(
            'shown.bs.modal', e => this._onGoToPageModalShown());
        modal.addEventListener(
            'hidden.bs.modal', e => this._onGoToPageModalHidden());
            
        // Set up OK button click listener.
        const button = document.getElementById('go-to-page-modal-ok-button');
        button.addEventListener(
            'click', e => this._onGoToPageModalOkButtonClick(e));
        
    }
    
    
    _onGoToPageModalShow() {
        
        if (this.numPages !== 0) {
            
            // Set label to include page number range.
            const label = document.getElementById('go-to-page-modal-label');
            label.textContent = `Page number (1 to ${this.numPages}):`;
            
            // Configure number input.
            const number = document.getElementById('go-to-page-modal-number');
            number.min = 1;
            number.max = this.numPages;
            number.value = '';
            
        }
        
    }
    
    
    _onGoToPageModalShown() {
        
        this._uninstallKeyPressEventListener();
        
        // Give keyboard focus to page number input.
        const number = document.getElementById('go-to-page-modal-number');
        number.focus();
        
    }
    
    
    _uninstallKeyPressEventListener() {
        document.onkeypress = null;
    }
    
    
    _onGoToPageModalHidden() {
        
        this._installKeyPressEventListener();
        
        const number = document.getElementById('go-to-page-modal-number');
        number.blur();
        
    }
    
    
    _installKeyPressEventListener() {
        document.onkeypress = e => this.onKeyPress(e);
    }
    
    
    _onGoToPageModalOkButtonClick(event) {
        
        const form = document.getElementById('go-to-page-modal-form');
        
        if (form.checkValidity()) {
            
            const number = document.getElementById('go-to-page-modal-number');
            const value = Number.parseInt(number.value);
            this.pageNum = value - 1;
            
        } else {
            
            event.preventDefault();
            event.stopImmediatePropagation();
            
        }
        
    }
    
    
    _initSetPresetsModal() {

        // TODO: Rather than having the server send presets to the client,
        // perhaps the client should fetch the presets from the server.
        // We could set up URLs so that a client could request all presets
        // of a specified type as JSON.

        // Populate settings select.
        _populatePresetSelect(
            'set-presets-modal-settings-select',
            this.settingsPresets, this.settingsPresetPath);

        // Populate key bindings select.
        _populatePresetSelect(
            'set-presets-modal-key-bindings-select',
            this.keyBindingsPresets, this.keyBindingsPresetPath);

        // Set up modal show listener.
        const modal = document.getElementById('set-presets-modal');
        modal.addEventListener(
            'show.bs.modal', e => this._onSetPresetsModalShow());
        
        // Set up OK button click listener.
        const button = document.getElementById('set-presets-modal-ok-button');
        button.addEventListener(
            'click', e => this._onSetPresetsModalOkButtonClick());

    }


    _onSetPresetsModalShow() {
        
        _updatePresetSelect(
            'set-presets-modal-settings-select', this.settingsPresetPath);
            
        _updatePresetSelect(
            'set-presets-modal-key-bindings-select',
            this.keyBindingsPresetPath);
            
    }
    
    
    _onSetPresetsModalOkButtonClick() {

        const settingsPath = _getSelectedPresetPath(
            'set-presets-modal-settings-select');
        this._setSettingsPresetPath(settingsPath);
            
        const keyBindingsPath = _getSelectedPresetPath(
            'set-presets-modal-key-bindings-select');
        this._setKeyBindingsPresetPath(keyBindingsPath);
                
        this._updateUrlAndHistory();
        
    }


    _updateUrlAndHistory() {
        window.history.pushState(this._historyState, null, this._url);
    }
    
    
    _onGoToNextDateAnchorClick(event) {
        this._goToNextDate();
    }
    

    _goToNextDate() {
        this._goToRelativeDate(1);
    }
    
    
    _goToRelativeDate(dayCount) {
        
        // Get URL of this clip album.
        const url = new URL(window.location.href);
        const params = url.searchParams;
        
        // Get date of this clip album.
        const dateString = params.get('date');
        const date = _parseDate(dateString);
        
        // Get new date.
        const newDate = _addDaysToDate(date, dayCount);
        const newDateString = _formatDate(newDate);
        
        // Update date in URL.
        params.set('date', newDateString);
        
        // Go to new URL.
        window.location.href = url.href;
        
    }
    
    
    _onGoToPreviousDateAnchorClick(event) {
        this._goToPreviousDate();
    }
    
    
    _goToPreviousDate() {
        this._goToRelativeDate(-1);
    }
    
    
    _onGoToClipCalendarAnchorClick(event) {
        this._goToClipCalendar();
    }
    
    
    _goToClipCalendar() {
        
        // Get URL of this clip album.
        const albumUrl = new URL(window.location.href);
        const albumParams = albumUrl.searchParams;
        
        // Build URL of corresponding clip calendar.
        const calendarUrl = new URL(albumUrl.origin + '/clip-calendar');
        const calendarParams = calendarUrl.searchParams;
        calendarParams.set('station_mic', albumParams.get('station_mic'));
        calendarParams.set('detector', albumParams.get('detector'));
        calendarParams.set(
            'classification', albumParams.get('classification'));
        calendarParams.set('settings', this.settingsPresetPath);
        calendarParams.set('commands', this.keyBindingsPresetPath);
        
       // Go to new URL.
        window.location.href = calendarUrl.href;
        
    }
    
    
    getTagColor(tag) {
        return this._tagColors.getTagColor(tag);
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
			this._clipsDiv, this._clipViews, settings.layout);
	}
    
    
    _createRugPlot(state) {
        
        if (this._isSingleDateClipAlbum()) {
            
            const rugPlotDiv = document.getElementById('rug-plot');
            return new NightRugPlot(this, rugPlotDiv);
                
        } else {
            
            return null;
            
        }
        
    }
    
    
	_createClipManager() {
	    
        const settings = {
            'maxNumClips': 2000,
            'numPrecedingPreloadedPages': 1,
            'numFollowingPreloadedPages': 1
        };
        
        return new PreloadingClipManager(
            settings, this.clips, this._layout.pagination);

	}
	
	
    get _historyState() {
        return {
            settingsPresetPath: this.settingsPresetPath,
            keyBindingsPresetPath: this.keyBindingsPresetPath,
            pageNum: this.pageNum
        };
    }
    
    
    set _historyState(state) {
        this._setSettingsPresetPath(state.settingsPresetPath);
        this._setKeyBindingsPresetPath(state.keyBindingsPresetPath);
        this._setPageNum(state.pageNum);
    }
    
    
    _createPageAutoAdvanceIterator() {

        const pause = 2;
        const minPause = .125;
        const maxPause = 16;
        const pauseScaleFactor = 2 ** .25;

        return new PausingIterator(
            pageNum => this._handleAutoAdvancePage(pageNum),
            pause, minPause, maxPause, pauseScaleFactor);
        
    }


    async _handleAutoAdvancePage(pageNum) {
        this.pageNum = pageNum;
    }


    _createClipAutoAdvanceIterator() {

        const pause = 1;
        const minPause = .125;
        const maxPause = 16;
        const pauseScaleFactor = 2 ** .25;

        return new PausingIterator(
            clipNum => this._handleAutoAdvanceClip(clipNum),
            pause, minPause, maxPause, pauseScaleFactor);

    }


    async _handleAutoAdvanceClip(clipNum) {
        this._selectClip(clipNum);
        await this._clipViews[clipNum].playClip();
    }


    _selectClip(i) {

        const clipPageNum = this._layout.getClipPageNum(i);

        if (this.pageNum !== clipPageNum) {
            this.pageNum = clipPageNum;
            _scrollToTop();
        }

        this.selectClip(i);
        this._scrollToClipViewIfNeeded(i);

    }


    _initUrlAndHistory() {
        window.history.replaceState(this._historyState, null, this._url);
        window.onpopstate = e => this._onPopHistoryState(e);
    }
    
    
    /**
     Gets a URL that reflects this clip album's current state, including
     search parameters for the settings preset path, the key bindings
     preset path, and the page number.
     */
    get _url() {
        
        // Get browser URL.
        const url = new URL(window.location.href);
        
        // Update search parameters according to clip album's current state.
        const params = url.searchParams;
        params.set('settings', this.settingsPresetPath);
        params.set('commands', this.keyBindingsPresetPath);
        params.set('page', this.pageNum + 1);
        
        return url;

    }
    
    
    _onPopHistoryState(event) {
        this._historyState = event.state;
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
		this._updateButtonStates();

	}


	_updateTitle() {

		const f = this.clipFilter;

        const dateText = this._isSingleDateClipAlbum() ? ` / ${f.date}` : '';
        
        const classificationText =
            f.classification === NULL_CHOICE
            ? '' : ` / ${f.classification}`;
            
        const tagText =
            f.tag === NULL_CHOICE
            ? '' : ` / ${f.tag}`;
            
        const title = `${f.stationMicName}${dateText} / ${f.detectorName}` +
            `${classificationText}${tagText}`;

		const titleHeading = document.getElementById('title')
        const pageText = this._getTitlePageText();
		titleHeading.textContent = `${title} / ${pageText}`;

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


	_updateButtonStates() {
	    
	    const prevButton =
            document.getElementById('go-to-previous-page-button');
	    prevButton.disabled = this.numPages === 0 || this.pageNum === 0;
	    
        const nextButton = document.getElementById('go-to-next-page-button');
	    nextButton.disabled =
	        this.numPages === 0 || this.pageNum === this.numPages - 1;
	    
        const anchor = document.getElementById('go-to-page-anchor');
        const disabled = this.numPages <= 1;
        anchor.parentElement.className = disabled ? 'disabled' : '';
	    anchor.disabled = disabled;
	    
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

        if (this.numPages > 0) {
            
            const clipViews = this._clipViews;
            const [startNum, endNum] =
                this._layout.getPageClipNumRange(this.pageNum);
    
            for (let i = startNum; i < endNum; i++) {
                const clipView = clipViews[i];
                clipView.resizeOverlayCanvasIfNeeded();
            }
            
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


	get readOnly() {
	    return this._readOnly;
	}
	
	
    get clipFilter() {
        return this._clipFilter;
    }


	get clips() {
		return this._clips;
	}


    get recordings() {
        return this._recordings;
    }


    get solarEventTimes() {
        return this._solarEventTimes;
    }


    get timeZone() {
        return this._timeZone;
    }


	get clipViewClasses() {
		return this._clipViewClasses;
	}


    get clipViewClass() {
        return this._clipViewClass;
    }


    get settingsPresets() {
        return this._settingsPresets;
    }
    
    
    get settingsPresetPath() {
        return this._settingsPresetPath;
    }
    
    
    set settingsPresetPath(path) {
        this._setSettingsPresetPath(path);
        this._updateUrlAndHistory();
    }
    
    
    _setSettingsPresetPath(path) {
        const [preset, actualPath] = this._getSettingsPreset(path);
        this._setSettings(preset);
        this._settingsPresetPath = actualPath;
    }
    
    
    _setSettings(settings) {

        this._updateClipViewSettings(settings);

        const [paginationChanged, pageNum] =
            this._updateLayoutSettings(settings);

        this._settings = settings;

        if (paginationChanged) {

            this._clipManager = this._createClipManager();
            
            // Set `this._pageNum` to `null` so setting page number
            // again below triggers full page update.
            this._pageNum = null;
            
            // Note that this triggers a call to this._update, so we
            // don't need to invoke this._update explicitly here.
            this._setPageNum(pageNum);

        } else {
            
            this._update();
            
        }

    }


	get settings() {
		return this._settings;
	}


	_updateClipViewSettings(settings) {

		if (settings.clipViewType !== this.settings.clipViewType) {
			// clip view type will change

			this._clipViews = this._createClipViews(settings);

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

        if (this.numPages === 0) {
            // clip album empty
            
            return [false, this.pageNum];
            
        } else {
            // clip album not empty
            
    		const oldFirstClipNum = this._layout.pagination[this.pageNum];
    		let paginationChanged;
    
    		if (settings.layoutType !== this.settings.layoutType) {
    			// layout type will change
    
    			this._layout = this._createLayout(settings);
    
    			// Pagination may or may not have changed. We say it has to
    			// ensure that display will update properly in all cases.
    			paginationChanged = true;
    
    		} else {
    			// layout type will not change
    
    			const oldPagination = this._layout.pagination;
    			this._layout.settings = settings.layout;
    			paginationChanged = !ArrayUtils.arraysEqual(
    				this._layout.pagination, oldPagination);
    
    		}
    
    		// Get new page number of clip that was first on old page.
    		const newPageNum = this._layout.getClipPageNum(oldFirstClipNum);
    
    		return [paginationChanged, newPageNum];
            
        }

	}


	get keyBindingsPresets() {
	    return this._keyBindingsPresets;
	}
	
	
	get keyBindingsPresetPath() {
	    return this._keyBindingsPresetPath;
	}
	
	
    set keyBindingsPresetPath(path) {
        this._setKeyBindingsPresetPath(path);
        this._updateUrlAndHistory();
    }
    
    
    _setKeyBindingsPresetPath(path) {
        const [preset, actualPath] = this._getKeyBindingsPreset(path);
        this._setKeyBindings(preset);
        this._keyBindingsPresetPath = actualPath;
    }
    
    
    _setKeyBindings(keyBindings) {
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


	get keyBindings() {
		return this._keyBindings;
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


	_annotateSelectedClips(annotations) {
        
		const clipNums = this._selection.selectedIndices;
        
        if (clipNums.length == 0) {
            
            window.alert(
                'There are no selected clips to annotate. ' +
                'Please select one or more clips and try again.');
            
        } else {
            
		    const clips = clipNums.map(i => this.clips[i]);
		    this._annotateClips(clips, annotations);
            
        }
        
	}


    async _annotateClips(clips, annotations) {
        
        // TODO: Consider allowing value to be array of same length as clips.
        // This would allow us to improve the efficiency of commands that
        // set only the first component of clip annotation values (and
        // thus must be able to set different annotation values on
        // different clips) by posting only once to the server rather
        // than once per clip.
 
        function getRequestContent() {
            
            const clipIds = clips.map(clip => clip.id);
            
            return {
                clip_ids: clipIds,
                annotations: Object.fromEntries(annotations)
            };
            
        }
        
        function updateClientAnnotations(clip) {
            
            const annos = clip.annotations;
            
            if (annos !== null)
                // client has copy of clip annotations
            
                for (const [name, value] of annotations.entries())
                    annos.set(name, value);
                        
        }
        
        return this._editClipMetadata(
            clips, '/annotate-clip-batch/', getRequestContent,
            updateClientAnnotations, 'annotation');

    }
    
    
    // This method handles the UI concerns of cursor changes and error
    // notification itself, but delegates actual metadata edits to
    // `_editClipMetadataAux`.
    async _editClipMetadata(
            clips, url, getRequestContent, updateClientMetadata,
            operationName) {
        
        const waitCursorNeeded =
            clips.length > _CLIP_EDIT_WAIT_CURSOR_THRESHOLD;
             
        this._setCursorIfNeeded(waitCursorNeeded, 'wait');

        try {
            
            await this._editClipMetadataAux(
                clips, url, getRequestContent, updateClientMetadata,
                operationName);
 
        } catch(e) {
            
            // Restore normal cursor before displaying alert.
            this._setCursorIfNeeded(waitCursorNeeded, 'auto');
            
            window.alert(e);
            
            return;
            
        }
        
        this._rerenderCurrentPageClips(clips);

        this._setCursorIfNeeded(waitCursorNeeded, 'auto');
        
    }
    
    
    _setCursorIfNeeded(needed, cursorName) {
        if (needed)
            setCursor(cursorName);
    }
    
    
    // This method performs metadata edits, but does not concern itself
    // with related UI updates. The `_editClipMetadata` method, which
    // calls this one, handles UI updates.
    async _editClipMetadataAux(
            clips, url, getRequestContent, updateClientMetadata,
            operationName) {
            
        // TODO: Consider implementing some sort of promise-based way
        // of getting clip samples and metadata. Then, instead of the
        // following, which sometimes fails with an exception, we could
        // just await the data we need. See related TODO in
        // static/vesper/clip-album/clip.js.
        this._checkClipMetadataStatus(clips);
        
        const content = getRequestContent();
        
        let response = null;
        
        try {
            
            response = await(this._sendJsonPostRequest(url, content));
        
        } catch(e) {
            
            throw (
                `Clip ${operationName} request failed with message: ${e}.`);
                
        }
        
        if (response.status === 200) {
            
            // Update client copies of clip metadata.
            for (const clip of clips)
                updateClientMetadata(clip);
                
        } else {
            
            let message = 
                `Clip ${operationName} request failed with response ` +
                `${response.status} (${response.statusText}).`;
                
            if (response.status === 403)
                message += ' Perhaps you are not logged in?';
                
            throw message;
               
        }
            
    }
    
    
    _checkClipMetadataStatus(clips) {
        
        const firstLoadingIndex = clips.find(
            clip => clip.metadataStatus === CLIP_LOAD_STATUS.LOADING);
            
        if (firstLoadingIndex !== undefined)
            throw (
                'Metadata for some of the specified clips are currently ' +
                'loading from the server. Please try again in a moment.');
        
    }
    
    
    _sendJsonPostRequest(url, content) {

        const body = JSON.stringify(content);
        
        // Include `X-CSRFToken` header to satisfy Django CSRF protection.
        // Django will reject POST request without it: see
        // https://docs.djangoproject.com/en/3.2/ref/csrf/.
        const headers = new Headers({
            'Content-Type': 'application/json; charset=utf-8',
            'X-CSRFToken': _CSRF_TOKEN
        });
        
        return fetch(url, {
            method: 'POST',
            body: body,
            headers: headers,
            credentials: 'same-origin'
        });

    }


    _rerenderCurrentPageClips(clips) {
        for (const clip of clips)
            if (this._isClipOnCurrentPage(clip))
                clip.view.render();
    }
    
    
    _isClipOnCurrentPage(clip) {
        return this._layout.getClipPageNum(clip.num) == this.pageNum;
    }


	_annotatePageClips(annotations) {
		const [startClipNum, endClipNum] =
			this.getPageClipNumRange(this.pageNum);
		const clipNums = ArrayUtils.rangeArray(startClipNum, endClipNum);
		const clips = clipNums.map(i => this.clips[i]);
		this._annotateClips(clips, annotations);
	}


	_annotateAllClips(annotations) {
		this._annotateClips(this.clips, annotations);
	}


    _unannotateSelectedClips(annotationNames) {
        const clipNums = this._selection.selectedIndices;
        const clips = clipNums.map(i => this.clips[i]);
        this._unannotateClips(clips, annotationNames);
    }


    async _unannotateClips(clips, annotationNames) {
        
        function getRequestContent() {
            
            const clipIds = clips.map(clip => clip.id);
            
            return {
                clip_ids: clipIds,
                annotation_names: Array.from(annotationNames)
            };
            
        }
        
        function updateClientAnnotations(clip) {
            
            const annos = clip.annotations;
            
            if (annos !== null)
                // client has copy of clip annotations
            
                for (const name of annotationNames)
                    annos.delete(name);
            
        }
                        
        return this._editClipMetadata(
            clips, '/unannotate-clip-batch/', getRequestContent,
            updateClientAnnotations, 'unannotation');

    }
    
    
    _unannotatePageClips(annotationNames) {
        const [startClipNum, endClipNum] =
            this.getPageClipNumRange(this.pageNum);
        const clipNums = ArrayUtils.rangeArray(startClipNum, endClipNum);
        const clips = clipNums.map(i => this.clips[i]);
        this._unannotateClips(clips, annotationNames);
    }


    _unannotateAllClips(annotationNames) {
        this._unannotateClips(this.clips, annotationNames);
    }


    _tagSelectedClips(tags) {
        
        const clipNums = this._selection.selectedIndices;
        
        if (clipNums.length === 0) {
            
            window.alert(
                'There are no selected clips to tag. ' +
                'Please select one or more clips and try again.');
            
        } else {
            
            const clips = clipNums.map(i => this.clips[i]);
            this._tagClips(clips, tags);
            
        }
        
    }


    async _tagClips(clips, tags) {
        
        function getRequestContent() {
            
            const clipIds = clips.map(clip => clip.id);
            
            return {
                clip_ids: clipIds,
                tags: Array.from(tags)
            };
            
        }
        
        function updateClientTags(clip) {
            
            const clientTags = clip.tags;
            
            if (clientTags !== null)
                // client has copy of clip tags
            
                for (const t of tags)
                    clientTags.add(t);
                        
        }
        
        return this._editClipMetadata(
            clips, '/tag-clip-batch/', getRequestContent, updateClientTags,
            'tag');
            
    }
    
    
    _tagPageClips(tags) {
        const [startClipNum, endClipNum] =
            this.getPageClipNumRange(this.pageNum);
        const clipNums = ArrayUtils.rangeArray(startClipNum, endClipNum);
        const clips = clipNums.map(i => this.clips[i]);
        this._tagClips(clips, tags);
    }


    _tagAllClips(tags) {
        this._tagClips(this.clips, tags);
    }


    _untagSelectedClips(tags) {
        const clipNums = this._selection.selectedIndices;
        const clips = clipNums.map(i => this.clips[i]);
        this._untagClips(clips, tags);
    }


    async _untagClips(clips, tags) {
        
        function getRequestContent() {
            
            const clipIds = clips.map(clip => clip.id);
            
            return {
                clip_ids: clipIds,
                tags: Array.from(tags)
            };
            
        }
        
        function updateClientTags(clip) {
            
            const clientTags = clip.tags;
            
            if (clientTags !== null)
                // client has copy of clip tags
            
                for (const t of tags)
                    clientTags.delete(t);
            
        }
                        
        return this._editClipMetadata(
            clips, '/untag-clip-batch/', getRequestContent, updateClientTags,
            'untag');

    }
    
    
    _untagPageClips(tags) {
        const [startClipNum, endClipNum] =
            this.getPageClipNumRange(this.pageNum);
        const clipNums = ArrayUtils.rangeArray(startClipNum, endClipNum);
        const clips = clipNums.map(i => this.clips[i]);
        this._untagClips(clips, tags);
    }


    _untagAllClips(tags) {
        this._untagClips(this.clips, tags);
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
        if (this._setPageNum(pageNum))
            this._updateUrlAndHistory();
	}


    _setPageNum(pageNum) {
        
        let pageNumChanged = false;
        const newPageNum = this._getPageNum(pageNum);
        
        if (this.numPages === 0) {
            // empty clip album
        
            // Make sure page number is defined and zero. It is `undefined`
            // initially, and can be set to `null` before calling this method
            // to force a UI update.
            if (this._pageNum !== 0) {
                this._pageNum = 0;
                pageNumChanged = true;
            }
            
        } else if (newPageNum !== this.pageNum) {
            // page number will change

            this._pageNum = newPageNum;
            
            this._selection = this._createSelection();
            
            if (this._rugPlot !== null) {
                const range = this.getPageClipNumRange(newPageNum);
                this._rugPlot.setPageClipNumRange(range);
            }
                
            this._clipManager.pageNum = newPageNum;
            
            pageNumChanged = true;
            
        }

        this._update();
        
        return pageNumChanged;
            
    }
    
    
	_getPageNum(pageNum) {
	    
	    if (this.numPages == 0 || pageNum < 0)
	        return 0;
	    
	    else if (pageNum > this.numPages - 1)
	        return this.numPages - 1;
	    
	    else
	        return pageNum;
	    
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


    _startPageAutoAdvance() {

        if (this._autoAdvanceStopped() &&
                this.numPages !== 0 && this.pageNum != this.numPages - 1) {
            // page and clip auto advance are both stopped, clip album
            // is not empty, and current page is not final page

            this._pageIterator.iterate(this.pageNum, this.numPages);

        }

    }


    _autoAdvanceStopped() {

        // Be careful here with parentheses and newlines. For example, this:
        //
        //   return
        //       this._pageIterator.state === PausingIteratorState.Stopped &&
        //       this._clipIterator.state === PausingIteratorState.Stopped;
        //
        // always returns `undefined`, ignoring all but the first line.

        return (
            this._pageIterator.state === PausingIteratorState.Stopped &&
            this._clipIterator.state === PausingIteratorState.Stopped);

    }


    _stopPageAutoAdvance() {
        this._pageIterator.stop();
    }


    _togglePageAutoAdvance() {
        if (this._pageIterator.state === PausingIteratorState.Running)
            this._stopPageAutoAdvance();
        else
            this._startPageAutoAdvance();
    }


    _acceleratePageAutoAdvance() {
        this._pageIterator.decreasePause();
    }


    _deceleratePageAutoAdvance() {
        this._pageIterator.increasePause();
    }

    
    _startClipAutoAdvance() {

        if (this._autoAdvanceStopped() && this.clips.length !== 0) {
            // page and clip auto advance are both stopped and album
            // is not empty

            const startClipNum = this._getAutoAdvanceStartClipNum();
            const endClipNum = this.clips.length;
            this._clipIterator.iterate(startClipNum, endClipNum);

        }

    }


    _getAutoAdvanceStartClipNum() {

        if (this._selection === null) {
            // no selection

            return 0;

        } else {
            // have selection

            const selectedIntervals = this._selection.selectedIntervals;

            if (selectedIntervals.length === 0) {
                // empty selection

                return this._layout.getPageClipNumRange(this.pageNum)[0];

            } else {
                // nonempty selection

                return selectedIntervals[0][0];

            }

        }

    }


    _stopClipAutoAdvance() {
        this._clipIterator.stop();
    }


    _toggleClipAutoAdvance() {
        if (this._clipIterator.state === PausingIteratorState.Running)
            this._stopClipAutoAdvance();
        else
            this._startClipAutoAdvance();
    }


    _accelerateClipAutoAdvance() {
        this._clipIterator.decreasePause();
    }


    _decelerateClipAutoAdvance() {
        this._clipIterator.increasePause();
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
				this._scrollToClipViewIfNeeded(i + 1);

			}

		}

	}


	_isSelectionSingleton() {
		return this._selection !== null && this._selection.size === 1;
	}


	_playSelectedClip(rate = 1) {
		if (this._isSelectionSingleton()) {
			const i = this._selection.selectedIntervals[0][0];
			this._clipViews[i].playClip(rate);
		}
	}


	_scrollToClipViewIfNeeded(clipNum) {

        const clipView = this._clipViews[clipNum];

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
		const clipsDivY = this._clipsDiv.getBoundingClientRect().top;

		// get y coordinate of top of first clip of current page.
		const [startNum, _] = this.getPageClipNumRange(this.pageNum);
		const clipDiv = this._clipViews[startNum].div;
		const clipDivY = clipDiv.getBoundingClientRect().top;

		const yMargin = clipDivY - clipsDivY;

		return yMargin;

	}


	_showClipViewRects() {
		console.log('clip view bounding client rectangles:');
		const r = this._clipsDiv.getBoundingClientRect();
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
				this._scrollToClipViewIfNeeded(i - 1);

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


    _executeStartPageAutoAdvanceCommand(env) {
        this._startPageAutoAdvance();
    }


    _executeStopPageAutoAdvanceCommand(env) {
        this._stopPageAutoAdvance();
    }


    _executeTogglePageAutoAdvanceCommand(env) {
        this._togglePageAutoAdvance();
    }


    _executeAcceleratePageAutoAdvanceCommand(env) {
        this._acceleratePageAutoAdvance();
    }


    _executeDeceleratePageAutoAdvanceCommand(env) {
        this._deceleratePageAutoAdvance();
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


    _executeStartClipAutoAdvanceCommand(env) {
        this._startClipAutoAdvance();
    }


    _executeStopClipAutoAdvanceCommand(env) {
        this._stopClipAutoAdvance();
    }


    _executeToggleClipAutoAdvanceCommand(env) {
        this._toggleClipAutoAdvance();
    }


    _executeAccelerateClipAutoAdvanceCommand(env) {
        this._accelerateClipAutoAdvance();
    }


    _executeDecelerateClipAutoAdvanceCommand(env) {
        this._decelerateClipAutoAdvance();
    }

    
    _executePlaySelectedClipCommand(env) {
        this._playSelectedClip();
    }


    _executePlaySelectedClipAtRateCommand(env) {
        const rate = env.getRequired('playback_rate');
        this._playSelectedClip(rate);
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

        const annotations = this._getAnnotations(env);
		this._annotateSelectedClips(annotations);

		// TODO: Optionally play selected clip.
		this._selectNextClip();

	}


    _getAnnotations(env) {
        const name = env.getRequired('annotation_name');
        const value = env.getRequired('annotation_value');
        return new Map([[name, value]]);
    }
    
    
	_executeAnnotatePageClipsCommand(env) {

        const annotations = this._getAnnotations(env);
		this._annotatePageClips(annotations);

		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.

	}


	_executeAnnotateAllClipsCommand(env) {
        const annotations = this._getAnnotations(env);
		this._annotateAllClips(annotations);
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

        const names = this._getAnnotationNames(env);
		this._unannotateSelectedClips(names);

		// TODO: Optionally play selected clip.
		this._selectNextClip();

	}


    _getAnnotationNames(env) {
        const name = env.getRequired('annotation_name');
        return new Set([name]);
    }
    
    
	_executeUnannotatePageClipsCommand(env) {

        const names = this._getAnnotationNames(env);
		this._unannotatePageClips(names)

		// TODO: Optionally advance to next page, if there is one,
		// select the first clip, and optionally play it.

	}


	_executeUnannotateAllClipsCommand(env) {
        const names = this._getAnnotationNames(env);
		this._unannotateAllClips(names);
	}
    
    
    _executeTagClipsCommand(env) {

        const scope = env.getRequired('annotation_scope');

        switch (scope) {

        case 'Selection':
            this._executeTagSelectedClipsCommand(env);
            break;

        case 'Page':
            this._executeTagPageClipsCommand(env);
            break;

        case 'All':
            this._executeTagAllClipsCommand(env);
            break;

        default:
            window.alert(`Unrecognized annotation scope "${scope}".`);

        }

    }


    _executeTagSelectedClipsCommand(env) {
        const tags = this._getTags(env);
        this._tagSelectedClips(tags);
        this._selectNextClip();
    }


    _getTags(env) {
        const tag = env.getRequired('tag');
        return new Set([tag]);
    }
    
    
    _executeTagPageClipsCommand(env) {
        const tags = this._getTags(env);
        this._tagPageClips(tags);
    }


    _executeTagAllClipsCommand(env) {
        const tags = this._getTags(env);
        this._tagAllClips(tags);
    }


    _executeUntagClipsCommand(env) {

        const scope = env.getRequired('annotation_scope');

        switch (scope) {

        case 'Selection':
            this._executeUntagSelectedClipsCommand(env);
            break;

        case 'Page':
            this._executeUntagPageClipsCommand(env);
            break;

        case 'All':
            this._executeUntagAllClipsCommand(env);
            break;

        default:
            window.alert(`Unrecognized annotation scope "${scope}".`);

        }

    }


    _executeUntagSelectedClipsCommand(env) {
        const tags = this._getTags(env);
        this._untagSelectedClips(tags);
        this._selectNextClip();
    }


    _executeUntagPageClipsCommand(env) {
        const tags = this._getTags(env);
        this._untagPageClips(tags)
    }


    _executeUntagAllClipsCommand(env) {
        const tags = this._getTags(env);
        this._untagAllClips(tags);
    }
    
    
    _executeGoToNextDateCommand(env) {
        if (this._isSingleDateClipAlbum())
            this._goToNextDate();
    }
    
    
    _executeGoToPreviousDateCommand(env) {
        if (this._isSingleDateClipAlbum())
            this._goToPreviousDate();
    }
    
    
    _executeGoToClipCalendarCommand(env) {
        if (this._isSingleDateClipAlbum())
            this._goToClipCalendar();
    }
    
    
    _executeSetClipAlbumSettingsPresetCommand(env) {
        this.settingsPresetPath = env.getRequired('preset_path');
    }


    _executeSetClipAlbumCommandsPresetCommand(env) {
        this.keyBindingsPresetPath = env.getRequired('preset_path');
    }


}


function _parseClip(clipInfo, clipNum) {

    const [id, startIndex, length, sampleRate, isoStartTime] = clipInfo;

    const utcStartTime = DateTime.fromISO(isoStartTime);

    return new Clip(
        clipNum, id, startIndex, length, sampleRate, utcStartTime);

}


function _parseRecording(isoRecordingBounds) {
    const bounds = isoRecordingBounds;
    return {
        startTime: DateTime.fromISO(bounds.startTime),
        endTime: DateTime.fromISO(bounds.endTime)
    }
}


function _parseSolarEventTimes(isoEventTimes) {

    if (isoEventTimes === null) {

        return null;

    } else {

        const eventNames = Object.getOwnPropertyNames(isoEventTimes);
        const utcEventTimes = {};

        for (const name of eventNames) {
            const isoTime = isoEventTimes[name];
            const utcTime = isoTime === null ? null : DateTime.fromISO(isoTime);
            utcEventTimes[name] = utcTime;
        }

        return utcEventTimes;

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


function _getPreset(presetPath, presetInfos, fallbackPreset, presetType) {

    if (presetPath === '') {
        // fallback preset specified
        
        return [fallbackPreset, presetPath];
        
    } else {
        // non-fallback preset specified
        
        for (const [path, preset] of presetInfos)
            if (path.join('/') === presetPath)
                return [preset, presetPath];

        // If we get here, there is no preset with the specified path.
        
        window.alert(
            `Could not find ${presetType} preset "${presetPath}". ` +
            `Will use built-in fallback preset instead.`);
        
        return [fallbackPreset, ''];
        
    }

}


function _populatePresetSelect(selectId, presetInfos, presetPath) {

    const select = document.getElementById(selectId);

    for (const [i, [path, preset]] of presetInfos.entries()) {

        const option = document.createElement('option');
        option.text = path.join('/');
        select.add(option);

        if (option.text === presetPath)
            select.selectedIndex = i;

    }

}


function _updatePresetSelect(selectId, presetPath) {
    
    const select = document.getElementById(selectId);
    const options = select.options;
    
    for (let i = 0; i < options.length; i++) {
        
        const option = options.item(i);
        
        if (option.text === presetPath)
            select.selectedIndex = i;
        
    }
    
}


function _getSelectedPresetPath(selectId) {
    
    // Note that the value of an HTML select element is the empty string
    // if no option is selected: see
    // https://developer.mozilla.org/en-US/docs/Web/API/HTMLSelectElement.
    // The `ClipAlbum` class uses the empty string as the name of the
    // built-in fallback preset, so it's safe to return.
    const select = document.getElementById(selectId);
    return select.value;
    
}


function _parseDate(dateString) {
    const [yearString, monthString, dayString] = dateString.split('-');
    const year = parseInt(yearString);
    const month = parseInt(monthString);
    const day = parseInt(dayString);
    return new Date(year, month - 1, day);
}


function _formatDate(date) {
    const yearString = date.getFullYear().toString();
    const monthString = (date.getMonth() + 1).toString().padStart(2, '0');
    const dayString = date.getDate().toString().padStart(2, '0');
    return [yearString, monthString, dayString].join('-');
}


function _addDaysToDate(date, dayCount) {
    const year = date.getFullYear();
    const month = date.getMonth();
    const day = date.getDate() + dayCount;
    return new Date(year, month, day);
}


function _scrollToTop() {
	window.scrollTo(0, 0);
}


function _scrollToBottom() {
	window.scrollTo(0, document.body.scrollHeight);
}


/*
 * Some of the notes below are out of date.
 */


/*

Vesper currently displays one night's worth of clips in a clip album for
a particular station/mic, detector, and classification. We would like to
support the specification and display of clip albums for a wider range of
queries, for example including species clip albums and tagged clip albums.

Initially, the UI for specifying the clips for the more general type of
clip album will be very similar to the UI for configuring a clip calendar.
The page will have the same clip query controls toward the top, but will
display a clip album rather than a calendar below the clip query controls.
Inbetween the clip query controls and the clip album will be a title.

The clip query controls and the title in the clip calendar and species
album pages are somewhat redundant. I think it might be preferable
to move the clip query controls into a modal. That will provide more
room for the clip album display, and also allow the query controls to
become more complicated, for example to allow the specification of tags.
Moving the clip query controls to a model can be a separate task, though,
that follows the initial implementation of the new clip album page.

To implement the new clip album page:

1. Separate title and rug plot from existing clip album and modify night
clip album accordingly.

2. Build new clip album page.

We might actually implement a preliminary version of (2) first using the
existing clip album class (or a minimally modified version of it) as a
proof of concept, for example to see what happens when we try to display
a clip album containing a million clips (e.g. all tseep clips from the
Harold station from fall 2017).

*/


/*

Need to pull title and rug plot out of clip album, making them separate
components.

Clip album will send `pageNumChanged` events. Night will register listener
that updates title and rug plot in response to page changes.

Rug plot will also send `pageSelected` events. Night will register
listener that updates title and clip album in response.

Update cycles will be avoided by having clip album and rug plot property
setters do nothing when property value will not change.

Perhaps rug plot should not be configured with clips and recordings, but
rather with clip times and recording intervals.

Rug plot pages are specified with an array of page start indices. Rug plot
should be able to function with no pages defined. [Does a rug plot with no
pages defined send events in response to mouse clicks?]

*/


/*

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

tag_clips(tag)
tag_selected_clips(tag)
tag_page_clips(tag)
tag_all_clips(tag)

untag_clips(tag)
untag_selected_clips(tag)
untag_page_clips(tag)
untag_all_clips(tag)


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
