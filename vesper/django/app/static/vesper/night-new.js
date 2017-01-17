'use strict'


// RESUME: Implement:
// 1. *clip view canvas mouse event handling for selections
// 2. *playback
// 3. classification commands and auto-navigation
// 4. rug plot
// 5. clip collection view presets
// 6. settings modal
// 7. clip view prerendering


/*
 * TODO:
 * 
 * 1. Add mouse time/freq display.
 * 
 * 2. Server should send metadata (ID, start time, duration) for all clips
 *    of a night to the client. Client performs pagination and display.
 *    Client retrieves audio data as needed (perhaps anticipating user
 *    navigation).
 *    
 * 3. Client should perform only those display pipeline functions that
 *    are needed to update the display after a settings change. For
 *    example, it should not recompute spectrograms after a color map
 *    or layout change.
 *   
 * 4. Client should allow user to specify the page size either as a
 *    number of rows or as a number of clips. Both types of display have
 *    their uses. Would it be okay for clips to remain the same size
 *    when the size of the browser window changes? Perhaps not when the
 *    number of rows is fixed, since then we would have to repaginate as
 *    the window size changes. I suspect we will want a third option for
 *    specifying the page size (number of rows and number of columns) when
 *    all clips are displayed with the same size.
 *    
 * 5. Would it make sense to specify font, button, etc. sizes in terms
 *    of viewport width?
 */


const LAYOUT_TYPE = 'Resizing';


const nonuniformNonresizingSettings = {
		
	layoutType: 'Nonuniform Nonresizing Clip Views',
	
	layout: {
		
		page: {
			size: 50               // clips
		},
		
	    clipView: {
	    	timeScale: 800,        // pixels per second
	    	height: 60,            // pixels
	    	xSpacing: 20,          // pixels
	    	ySpacing: 20           // pixels
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
		    location: 'Bottom',
		    color: 'white',
		    fontSize: 1,
		    classificationIncluded: true,
		    startTimeIncluded: true,
		    hiddenClassificationPrefixes: ['Call.']
        },
        
		spectrogram: {
			windowSize: 100,
			hopSize: 50,
			dftSize: 256,
			referencePower: Math.pow(2, -30),
			lowPower: 10,
			highPower: 100,
			smoothingEnabled: true,
			timePaddingEnabled: true
		}
	
	}
	
};


const nonuniformResizingSettings = {
		
	layoutType: 'Nonuniform Resizing Clip Views',
	
	layout: {
		
		page: {
			width: 2.5,            // seconds
			height: 8              // rows
		},
		
		clipView: {
			xSpacing: 1,           // percent of display width
			ySpacing: 1            // percent of display width
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
		    location: 'Bottom',
		    color: 'white',
		    fontSize: 1,
		    classificationIncluded: true,
		    startTimeIncluded: true,
		    hiddenClassificationPrefixes: ['Call.']
        },
        
		spectrogram: {
			windowSize: 100,
			hopSize: 50,
			dftSize: 256,
			referencePower: Math.pow(2, -30),
			lowPower: 10,
			highPower: 100,
			smoothingEnabled: true,
			timePaddingEnabled: false
		}
	
	}
	
};


let clipCollectionView = null;


function onLoad() {
	
//	initSettingsModal();
	
	createClipCollectionView();
	
}


function createClipCollectionView() {
	
	const elements = {
		'titleHeading': document.getElementById('title'),
	    'rugPlotDiv': document.getElementById('rug-plot'),
	    'clipsDiv': document.getElementById('clips')
	};
	
	const settings = 
		LAYOUT_TYPE === 'Resizing' ?
		nonuniformResizingSettings :
		nonuniformNonresizingSettings;
	
	const clipViewDelegateClasses = {
		'Spectrogram': SpectrogramClipViewDelegate
	};
		
	clipCollectionView = new ClipCollectionView(
		elements, clips, recordings, solarEventTimes, settings,
		clipViewDelegateClasses);
	
}


function onResize() {
	clipCollectionView.onResize();
}


//function initSettingsModal() {
//	
//	// TODO: Rather than having the server send presets to the client,
//	// perhaps the client should retrieve the presets from the server
//	// with XHRs. We could set up URLs so that a client could request
//	// all presets of a specified type as JSON.
//	
//	// showPresets(
//	//     'Clip Collection View Settings', clipCollectionViewSettingsPresets);
//	// showPresets('Annotation Scheme', annotationSchemePresets);
//	
//	const clipCollectionViewSettingsSelect =
//		document.getElementById('clip-collection-view-settings');
//	populatePresetSelect(
//		clipCollectionViewSettingsSelect, clipCollectionViewSettingsPresets)
//	
//	const annotationSchemeSelect =
//		document.getElementById('annotation-scheme');
//	populatePresetSelect(annotationSchemeSelect, annotationSchemePresets)	
//	
//	const okButton = document.getElementById('ok-button');
//	okButton.onclick = onOkButtonClick;
//	
//}
//
//
//function showPresets(type_name, info) {
//	console.log(`${type_name} presets:`);
//	for (let [path, preset] of info)
//		console.log('    ' + path);
//}
//
//
//function populatePresetSelect(select, info) {
//	
//	for (let [path, preset] of info) {
//		const option = document.createElement('option');
//	    option.text = path.join(' / ');
//		select.add(option);
//	}
//	
//}
//
//
//function onOkButtonClick() {
//	
//	const clipCollectionViewSettingsSelect =
//		document.getElementById('clip-collection-view-settings');
//	
//	const i = clipCollectionViewSettingsSelect.selectedIndex;
//	const preset = clipCollectionViewSettingsPresets[i][1];
//	
//	// clipSpectrogramSettings = preset.clipSpectrogramSettings;
//	clipLayoutSettings = preset.clipLayoutSettings;
//	clipLabelSettings = preset.clipLabelSettings;
//	selectionOutlineWidth = preset.selectionOutlineWidth;
//	
//	recreateClipDivs();
//	
//	const annotationSchemeSelect =
//		document.getElementById('annotation-scheme');
//	
//	// console.log('annotation scheme:', annotationSchemeSelect.value);
//	
//}




//class AnnotationCommandInterpreter {
//	
//	
//	constructor(spec) {
//		this._commandNamePrefixes = new Set();
//		this._commandActions = {};
//		this._parseSpec(spec);
//		this._clearCommandNameBuffer();
//	}
//	
//	
//	_parseSpec(spec) {
//		for (const element of spec)
//			this._parseSpecElement(element);
//	}
//	
//	
//	_parseSpecElement(element) {
//		const commands = element.annotation_commands;
//		const commandNames = Object.keys(commands);
//		this._addCommandNamePrefixes(commandNames);
//		this._addCommandActions(element.annotation_name, commands);
//	}
//	
//	
//	_addCommandNamePrefixes(names) {
//		
//		/*
//		 * Adds the nonempty, proper prefixes of the specified command
//		 * names to this._commandNamePrefixes.
//		 */
//		
//		for (const name of names)
//			for (let i = 1; i < name.length; i++)
//				this._commandNamePrefixes.add(name.slice(0, i));
//		
//	}
//	
//	
//	_addCommandActions(annotationName, commands) {
//		const keys = Object.keys(commands);
//		for (const key of keys)
//			this._commandActions[key] =
//				_parseCommandAction(annotationName, commands[key]);
//	}
//	
//	
//	_clearCommandNameBuffer() {
//		this._commandNameBuffer = '';
//	}
//	
//	
//	onKey(key) {
//		
//		if (key === '\\') {
//			
//			this._clearCommandNameBuffer();
//			console.log('Cleared command name buffer.');
//		
//		} else {
//			
//			const name = this._commandNameBuffer + key;
//			
//			let action = this._commandActions[name];
//			
//			if (action !== undefined) {
//				
//				action();
//				this._clearCommandNameBuffer();
//			
//			} else if (this._commandNamePrefixes.has(name)) {
//					
//				// TODO: Show contents of name buffer in UI.
//				console.log(`Command name buffer "${name}".`);
//				this._commandNameBuffer = name;
//			    
//			
//			} else {
//				// nonexistent command
//				
//				// TODO: Notify user of error.
//				console.log(`Unrecognized command name "${name}".`);
//				this._clearCommandNameBuffer();
//				
//			}
//				
//		}
//		
//	}
//	
//}
//
//	
//function _parseCommandAction(annotationName, actionSpec) {
//	
//	let scope = 'Selection';
//	if (actionSpec.startsWith('*')) {
//		scope = 'Page';
//		actionSpec = actionSpec.slice(1);
//	}
//	
//	let annotationValue = null;
//	let annotatorName = null;
//	if (actionSpec.startsWith('@'))
//		annotatorName = actionSpec.slice(1);
//	else
//		annotationValue = actionSpec;
//
//	if (annotationValue !== null)
//		return () => _annotateClips(annotationName, annotationValue, scope);
//	else
//		return () => _runClipAnnotator(annotationName, annotatorName, scope);
//
//}
//
//
//function _annotateClips(name, value, scope) {
//	
//	if (scope === 'Selection') {
//		_annotateSelectedClips(name, value);
//		// TODO: We need access to the clip collection view here.
//		_selectNextClip();
//	}
//	
//	else if (scope === 'Page')
//		_annotateIntervalClips(name, value, [0, clips.length - 1]);
//	
//	else
//		// TODO: Implement 'All' scope.
//		window.alert(`Unrecognized annotation command scope "${scope}".`);
//	
//}
//
//
//function _annotateSelectedClips(name, value) {
//	for (const interval of selection.selectedIntervals)
//		_annotateIntervalClips(name, value, interval);
//}
//
//
//function _annotateIntervalClips(name, value, interval) {
//	
//	for (let i = interval[0]; i <= interval[1]; i++) {
//		
//		const clip = clips[i];
//		const url = `/vesper/clips/${clip.id}/annotations/${name}`;
//		
//		const xhr = new XMLHttpRequest();
//		xhr.onload = () => _onAnnotationPutComplete(xhr, clip, name, value);
//		xhr.open('PUT', url);
//		xhr.setRequestHeader('Content-Type', 'text/plain; charset=utf-8');
//		xhr.send(value);
//		
//	}
//
//}
//
//
//function _onAnnotationPutComplete(xhr, clip, annotationName, annotationValue) {
//	
//	console.log(
//		'PUT completed', xhr.status, clip.id, annotationName, annotationValue);
//	
//	// TODO: Notify user on errors.
//	// TODO: Handle non-"Classification" annotations.
//	if (xhr.status === 200) {
//		clip.classification = annotationValue;
//		drawClip(clip, clipSpectrogramSettings);
//	}
//	
//}
//
//
//function _runClipAnnotator(annotationName, annotatorName, scope) {
//	// TODO: Implement this function.
//	console.log(
//		`run annotator "${annotationName}" "${annotatorName}" ${scope}`);
//}
//
//
//const annotationCommandInterpreter = new AnnotationCommandInterpreter([
//    {
//		'annotation_name': 'Classification',
//		'annotation_commands': {
//			'c': 'Call',
//			'C': '*Call',
//			'n': 'Noise',
//			'N': '*Noise',
//			'x': 'Unclassified',
//			'X': '*Unclassified',
//			'@o': '@MPG Ranch Outside Clip Classifier',
//			'@O': '*@MPG Ranch Outside Clip Classifier',
//			'@c': '@NFC Coarse Clip Classifier',
//			'@C': '*@NFC Coarse Clip Classifier'
//		}
//    }, {
//    	'annotation_name': 'Classification Confidence',
//    	'annotation_commands': {
//    		'1': '1',
//    		'2': '2',
//    		'3': '3'
//    	}
//    }
//]);




function onKeyPress(e) {
	clipCollectionView.onKeyPress(e);
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
