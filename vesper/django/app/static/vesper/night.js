"use strict"


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
 *    of viewport width? That might help 
 */
let clipSpectrogramSettings = {
	"windowSize": 100,
	"hopSize": 50,
	"dftSize": 256,
	"referencePower": 1,
	"lowPower": 10,
	"highPower": 100,
	"smoothingEnabled": true,
	"timePaddingEnabled": false
}

// All clip layout setting units are pixels except as noted.
let clipLayoutSettings = {
	"timeScale": 1000,     // pixels per second
	"height": 100,
	"horizontalSpacing": 20,
	"verticalSpacing": 25,
	"selectionOutlineWidth": 5
}

let clipLabelSettings = {
	"visible": true,
	"location": "bottom",
	"color": "white",
	"size": 1,
	"classificationIncluded": true,
	"startTimeIncluded": true,
	"hiddenClassificationPrefixes": ["Call."],
}

// The index of the last clip displayed on this page.
let pageEndIndex = null;

// The clip divs displayed on this page.
let clipDivs = null;

// The selected clips of this page.
let selection = null;


function onLoad() {
	
	const okButton = document.getElementById('ok-button');
	okButton.onclick = onOkButtonClick;
	
	populateSettingsModalControls();
	
	// showPresets('Clip Grid Settings', clipGridSettingsPresets);
	// showPresets('Annotation Scheme', annotationSchemePresets);
	
	const settings = clipSpectrogramSettings;
	settings.window = createDataWindow("Hann", settings.windowSize);
	
	pageEndIndex = Math.min(pageStartIndex + pageSize, numClips);
	setTitle();
	createClipDivs();
	layOutClipDivs();
	initSelection();
	
}


function recreateClipDivs() {
	removeClipDivs();
	createClipDivs();
	layOutClipDivs();
	updateSelectionOutlines();
}


function removeClipDivs() {
	const div = document.getElementById("clips");
    while (div.firstChild)
    	div.removeChild(div.firstChild)
}


function onOkButtonClick() {
	
	const clipGridSettingsSelect =
		document.getElementById('clip-grid-settings');
	
	const i = clipGridSettingsSelect.selectedIndex;
	const preset = clipGridSettingsPresets[i][1];
	
	// clipSpectrogramSettings = preset.clipSpectrogramSettings;
	clipLayoutSettings = preset.clipLayoutSettings;
	clipLabelSettings = preset.clipLabelSettings;
	
	recreateClipDivs();
	
	const annotationSchemeSelect =
		document.getElementById('annotation-scheme');
	
	// console.log('annotation scheme:', annotationSchemeSelect.value);
	
}


function populateSettingsModalControls() {
	
	// TODO: Rather than having the server send presets to the client,
	// perhaps the client should retrieve the presets from the server
	// with XHRs. We could set up URLs so that a client could request
	// all presets of a specified type as JSON.
	
	const clipGridSettingsSelect =
		document.getElementById('clip-grid-settings');
	populatePresetSelect(clipGridSettingsSelect, clipGridSettingsPresets)
	
	const annotationSchemeSelect =
		document.getElementById('annotation-scheme');
	populatePresetSelect(annotationSchemeSelect, annotationSchemePresets)	
	
}


function populatePresetSelect(select, info) {
	
	for (let [path, preset] of info) {
		const option = document.createElement("option");
	    option.text = path.join(' / ');
		select.add(option);
	}
	
}


function showPresets(type_name, info) {
	console.log(`${type_name} presets:`);
	for (let [path, preset] of info)
		console.log('    ' + path);
}


function setTitle() {
	
	const micOutputName = getMicrophoneOutputDisplayName(microphoneOutputName);
	
	const title = `${date} ${stationName} / ${micOutputName} / ` +
	              `${detectorName} / ${classification} Clips ` +
	              `${pageStartIndex + 1}-${pageEndIndex} of ${numClips}`;
	
	let titleElement = document.getElementById("title");
	titleElement.innerHTML = title;
	
	document.title = `Clips - ${title}`;
	
}


function initSelection() {
	selection = new Multiselection(0, clips.length - 1);
	if (selectedIndex !== null)
		selectClip(selectedIndex - pageStartIndex);
}


function createClipDivs() {
	
	// The server provides us with a Javascript array called `clips`,
	// each element of which describes a clip. It also provides us with
	// an empty <div> element with ID "clips" where clips should be
	// displayed. We populate the <div> according to the contents of
	// the `clips` array.
	
	const clipsDiv = document.getElementById("clips");
	
	if (clips.length != 0) {
		
		clipDivs = [];
		
		for (let i = 0; i != clips.length; ++i) {
			
			const clip = clips[i];
			clip.index = i;
			
			const div = createClipDiv(clip);
			clip.div = div;
			
			clipsDiv.appendChild(div);
			clipDivs.push(div);
		}
		
	} else
		clipsDiv.innerHTML = "There are no clips to display.";
	
}


function layOutClipDivs() {
	
	const s = clipLayoutSettings;
	const outlineWidth = s.selectionOutlineWidth;
	
	const x = Math.max(s.horizontalSpacing / 2, outlineWidth) + "px";
	const y = Math.max(s.verticalSpacing / 2, outlineWidth) + "px";
	
	let i = 0;
	
	for (let div of clipDivs) {
		
		const clip = clips[i++];
		const span = (clip.length - 1) / clip.sampleRate;
		const width = span * s.timeScale;
		div.style.minWidth = width + "px";
	    div.style.width = width + "px";
	    div.style.height = s.height + "px";
	    div.style.margin = y + " " + x + " " + y + " " + x;
	    div.style.outlineWidth = outlineWidth + "px";
	    
	    // Set canvas width and height to width and height on screen.
	    // This will help prevent distortion of items drawn on the
	    // canvas, especially text.
	    const canvas = div.querySelector(".clip-canvas");
	    canvas.style.width = "100%";
	    canvas.style.height = "100%";
	    canvas.width = canvas.clientWidth;
	    canvas.height = canvas.clientHeight;
	    
	}
	
}


function createClipDiv(clip) {
	
	const index = clip.index;
	
    const div = document.createElement("div");
    div.className = "clip";
    div.setAttribute("data-index", index);
    
    clip.div = div;
    
    const canvas = document.createElement("canvas");
    canvas.className = "clip-canvas";
    canvas.setAttribute("data-index", index);
    canvas.addEventListener("mouseover", onMouseOver);
    canvas.addEventListener("mouseout", onMouseOut);
    canvas.addEventListener("click", onCanvasClick);
    div.appendChild(canvas);
    
    const button = document.createElement("button");
    button.className = "clip-play-button";
    button.setAttribute("data-index", index);
    button.addEventListener("click", onPlayButtonClick);
    div.appendChild(button);    
    
    const icon = document.createElement("span");
    icon.className = "glyphicon glyphicon-play";
    icon.setAttribute("data-index", index);
    button.appendChild(icon);
    
    /*
     * TODO: Download each audio file only once rather than twice.
     * We currently download an audio file once for its HTML5 audio element
     * (for playback) and a second time using an XHR (to get its samples
     * so we can compute a spectrogram from them).
     * 
     * I believe we should be able to use a Web Audio MediaElementSourceNode
     * to decode the audio of an audio element into the destination AudioBuffer
     * of an offline audio context, obviating the XHR, but I have not been
     * able to get this to work. The commented code in startAudioDecoding
     * always yields all-zero samples.
     * 
     * Another approach would be use only the XHR, dropping the audio element
     * and performing playback using Web Audio. I would prefer the other
     * approach, however, since it should allow us to decode only portions
     * of the source of an audio element, which would be useful in the
     * future for long sounds.
     */
    
    const audio = document.createElement("audio");
    audio.className = "clip-audio";
    audio.setAttribute("src", clip.url);
    audio.setAttribute("data-index", index);
    audio.innerHtml =
        "Your browser does not support the <code>audio</code> HTML element."
    div.appendChild(audio)
    
    const label = document.createElement("p");
    label.className = "clip-label"
    div.appendChild(label);
    
    startAudioDecoding(clip);
    
    return div;
	
}


function startAudioDecoding(clip) {
	
	const context = new OfflineAudioContext(1, 1, clip.sampleRate);
	const xhr = new XMLHttpRequest();
	xhr.open("GET", clip.url);
	xhr.responseType = "arraybuffer";
	xhr.onload = () =>
		context.decodeAudioData(xhr.response).then(audioBuffer =>
		    onAudioDecoded(audioBuffer, clip));
	xhr.send();
	
//    const context = new OfflineAudioContext(1, clip.length, clip.sampleRate);
//    const source = context.createMediaElementSource(audio);
//    source.connect(context.destination);
//    context.startRendering().then(audioBuffer =>
//        onAudioDecoded(audioBuffer, clip));

}


function onAudioDecoded(audioBuffer, clip) {
	// showAudioBufferInfo(audioBuffer);
    clip.samples = audioBuffer.getChannelData(0);
    scaleSamples(clip.samples, 32767);
    const settings = clipSpectrogramSettings;
    clip.spectrogram = computeClipSpectrogram(clip, settings);
    clip.spectrogramCanvas = createSpectrogramCanvas(clip, settings);
    clip.spectrogramImageData = createSpectrogramImageData(clip);
    drawSpectrogram(clip, settings);
    drawClip(clip, settings);
}


function showAudioBufferInfo(b) {
	const samples = b.getChannelData(0);
    let [min, max] = getExtrema(samples);
    console.log(
        "AudioBuffer", b.numberOfChannels, b.length, b.sampleRate, b.duration,
        min, max);
}


function getExtrema(samples) {
    let min = 1000000;
    let max = -1000000;
    for (let i = 0; i < samples.length; i++) {
    	const s = samples[i];
        min = Math.min(s, min);
        max = Math.max(s, max);
    }
    return [min, max];	
}


function scaleSamples(samples, factor) {
    for (let i = 0; i < samples.length; i++)
    	samples[i] *= factor;	
}


function computeClipSpectrogram(clip, settings) {
	const samples = clip.samples
	const spectrogram = allocateSpectrogramStorage(samples.length, settings);
	computeSpectrogram(samples, settings, spectrogram);
	return spectrogram;
}


function createSpectrogramCanvas(clip, settings) {
	
	const gram = clip.spectrogram;
	const numBins = settings.dftSize / 2 + 1;
	const numSpectra = gram.length / numBins;
	
	const canvas = document.createElement("canvas");
	canvas.width = numSpectra;
	canvas.height = numBins;
	
	return canvas;
	
}


function createSpectrogramImageData(clip) {
	
	const canvas = clip.spectrogramCanvas;
	const numSpectra = canvas.width;
	const numBins = canvas.height;

	const context = canvas.getContext("2d");
	return context.createImageData(numSpectra, numBins);

}


function drawSpectrogram(clip, settings) {
	
	const gram = clip.spectrogram;

	const canvas = clip.spectrogramCanvas;
	const numSpectra = canvas.width;
	const numBins = canvas.height;

	const imageData = clip.spectrogramImageData;
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
			const v = 255 - a * gram[k] + b;
			data[m++] = v;
			data[m++] = v;
			data[m++] = v;
			data[m++] = 255;
			k += spectrumStride;
		}
	}
	
	// Write pixel values to spectrogram canvas.
	const context = canvas.getContext("2d");
	context.putImageData(imageData, 0, 0);
	
}


function drawClip(clip, settings) {
	
    const canvas = clip.div.querySelector(".clip-canvas");
	const context = canvas.getContext("2d");
	
	// Draw gray background rectangle.
	context.fillStyle = "gray";
	context.fillRect(0, 0, canvas.width, canvas.height);
	
	// Draw spectrogram from clip spectrogram canvas, stretching as needed.
	const gramCanvas = clip.spectrogramCanvas;
	const numSpectra = gramCanvas.width;
	context.imageSmoothingEnabled = settings.smoothingEnabled;
	if (settings.timePaddingEnabled) {
		let [x, width] = getSpectrogramXExtent(
			settings, numSpectra, clip, canvas.width);
		context.drawImage(gramCanvas, x, 0, width, canvas.height);
	} else {
		context.drawImage(gramCanvas, 0, 0, canvas.width, canvas.height);
	}

	// Draw label.
	drawClipLabel(clip, clipLabelSettings);
	
}


function getSpectrogramXExtent(settings, numSpectra, clip, canvasWidth) {
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


function drawClipLabel(clip, settings) {

	const s = settings;
	
	if (s.visible) {
		
		let labelParts = [];
		
		if (s.classificationIncluded) {
			
			let annotation = clip.classification;
			
			if (s.hasOwnProperty("hiddenClassificationPrefixes"))
				for (let prefix of s.hiddenClassificationPrefixes)
					if (annotation.startsWith(prefix))
						annotation = annotation.substr(prefix.length);
			
	        labelParts.push(annotation);
	        
		}
		
		if (s.startTimeIncluded) {
			const parts = clip.startTime.split(" ");
			labelParts.push(parts[1]);
		}
		
		const button = clip.div.querySelector(".clip-play-button");
		
		/*
		 * I'm not sure why it's necessary to set the left property in
		 * the following, but without it the play button appears to the
		 * right of the clip rather than within it.
		 */
		button.style.left = "5px";
    	button.style.top = "5px";
    	button.style.bottom = "unset";
		
		if (labelParts.length != 0) {
			
		    const label = clip.div.querySelector(".clip-label");
		    const loc = s.location;
		    
		    // Set label horizontal location.
		    if (loc.endsWith("left")) {
		    	label.style.left = "0";
		    } else if (loc.endsWith("right")) {
		    	label.style.right = "0";
		    } else {
		    	label.style.left = "0";
		    	label.style.width = "100%";
		        label.style.textAlign = "center";
		    }
		    
		    // Set label vertical location and padding.
		    if (loc.startsWith("below")) {
		    	label.style.top = "100%";
		    	label.style.padding = "0";
		    } else if (loc.startsWith("above")) {
		    	label.style.bottom = "100%";
		    	label.style.padding = "0"
		    } else if (loc.startsWith("top")) {
		    	label.style.top = "0";
		    	label.style.padding = "0 5px";
		    } else {
		    	label.style.bottom = "0";
		    	label.style.padding = "0 5px";
		    }
		    
		    // Set button location.
		    if (loc.startsWith("top")) {
		    	
				/*
				 * I'm not sure why it's necessary to set the left property in
				 * the following, but without it the play button appears to the
				 * right of the clip rather than within it.
				 */
		    	button.style.left = "5px";
		        button.style.bottom = "5px";
		        button.style.top = "unset";
		        
		    }
		    
		    label.style.color = s.color;
		    label.style.fontSize = `${s.size}em`;
		    label.innerHTML = labelParts.join(' ');
		    
		}
		
	}
	
}


function onMouseOver(e) {
	const i = getClipIndex(e.target);
	console.log("mouse over " + i);
}


function getClipIndex(element) {
	return parseInt(element.getAttribute("data-index"));
}


function onMouseOut(e) {
	const i = getClipIndex(e.target);
	console.log("mouse out " + i);
}


function onCanvasClick(e) {

	const index = getClipIndex(e.target);
	
	if (e.shiftKey)
		selection.extend(index);
	else if (e.ctrlKey)
		selection.toggle(index);
	else
		selection.select(index);
	
	updateSelectionOutlines();
	
}


function updateSelectionOutlines() {
	for (let i = 0; i < clipDivs.length; ++i) {
		const color = selection.contains(i) ? "orange" : "transparent";
		clipDivs[i].style.outlineColor = color;
	}
}


function onPlayButtonClick(e) {
	const i = getClipIndex(e.target);
	const div = clipDivs[i];
	const audio = div.getElementsByClassName("clip-audio")[0];
	audio.play();
}


function loadNextPage() {
	pageDown(true);
}


class AnnotationCommandInterpreter {
	
	
	constructor(spec) {
		this.commandNamePrefixes = new Set();
		this.commandActions = {};
		this.parseSpec(spec);
		this.clearCommandNameBuffer();
	}
	
	
	parseSpec(spec) {
		for (let element of spec)
			this.parseSpecElement(element);
	}
	
	
	parseSpecElement(element) {
		const commands = element.annotation_commands;
		const commandNames = Object.keys(commands);
		this.addCommandNamePrefixes(commandNames);
		this.addCommandActions(element.annotation_name, commands);
	}
	
	
	addCommandNamePrefixes(names) {
		
		/*
		 * Adds the nonempty, proper prefixes of the specified command
		 * names to this.commandNamePrefixes.
		 */
		
		for (let name of names)
			for (let i = 1; i < name.length; i++)
				this.commandNamePrefixes.add(name.slice(0, i));
		
	}
	
	
	addCommandActions(annotationName, commands) {
		const keys = Object.keys(commands);
		for (let key of keys)
			this.commandActions[key] =
				parseCommandAction(annotationName, commands[key]);
	}
	
	
	clearCommandNameBuffer() {
		this.commandNameBuffer = '';
	}
	
	
	onKey(key) {
		
		if (key === '\\') {
			
			this.clearCommandNameBuffer();
			console.log(`Cleared command name buffer.`);
		
		} else {
			
			const name = this.commandNameBuffer + key;
			
			let action = this.commandActions[name];
			
			if (action !== undefined) {
				
				action();
				this.clearCommandNameBuffer();
			
			} else if (this.commandNamePrefixes.has(name)) {
					
				// TODO: Show contents of name buffer in UI.
				console.log(`Command name buffer "${name}".`);
				this.commandNameBuffer = name;
			    
			
			} else {
				// nonexistent command
				
				// TODO: Notify user of error.
				console.log(`Unrecognized command name "${name}".`);
				this.clearCommandNameBuffer();
				
			}
				
		}
		
	}
	
}

	
function parseCommandAction(annotationName, actionSpec) {
	
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
		return () => annotateClips(annotationName, annotationValue, scope);
	else
		return () => runClipAnnotator(annotationName, annotatorName, scope);

}


function annotateClips(name, value, scope) {
	
	if (scope === 'Selection') {
		annotateSelectedClips(name, value);
		maybeSelectNextClip();
	}
	
	else if (scope === 'Page')
		annotateIntervalClips(name, value, [0, clips.length - 1]);
	
	else
		window.alert(`Unrecognized annotation command scope "${scope}".`);
	
}


function annotateSelectedClips(name, value) {
	for (let interval of selection.selectedIntervals)
		annotateIntervalClips(name, value, interval);
}


function annotateIntervalClips(name, value, interval) {
	
	for (let i = interval[0]; i <= interval[1]; i++) {
		
		const clip = clips[i];
		const url = `/vesper/clips/${clip.id}/annotations/${name}`;
		
		const xhr = new XMLHttpRequest();
		xhr.onload = () => onAnnotationPutComplete(xhr, clip, name, value);
		xhr.open('PUT', url);
		xhr.setRequestHeader('Content-Type', 'text/plain; charset=utf-8');
		xhr.send(value);
		
	}

}


function onAnnotationPutComplete(xhr, clip, annotationName, annotationValue) {
	
	console.log(
		'PUT completed', xhr.status, clip.id, annotationName, annotationValue);
	
	// TODO: Notify user on errors.
	// TODO: Handle non-"Classification" annotations.
	if (xhr.status === 200) {
		clip.classification = annotationValue;
		drawClip(clip, clipSpectrogramSettings);
	}
	
}


function runClipAnnotator(annotationName, annotatorName, scope) {
	// TODO: Implement this function.
	console.log(
		`run annotator "${annotationName}" "${annotatorName}" ${scope}`);
}


const annotationCommandInterpreter = new AnnotationCommandInterpreter([
    {
		'annotation_name': 'Classification',
		'annotation_commands': {
			'c': 'Call',
			'C': '*Call',
			'n': 'Noise',
			'N': '*Noise',
			'x': 'Unclassified',
			'X': '*Unclassified',
			'@o': '@MPG Ranch Outside Clip Classifier',
			'@O': '*@MPG Ranch Outside Clip Classifier',
			'@c': '@NFC Coarse Clip Classifier',
			'@C': '*@NFC Coarse Clip Classifier'
		}
    }, {
    	'annotation_name': 'Classification Confidence',
    	'annotation_commands': {
    		'1': '1',
    		'2': '2',
    		'3': '3'
    	}
    }
]);



function selectFirstClip() {
	if (clipDivs.length > 0)
	    selectClip(0);
}


function maybeSelectNextClip() {
	
	if (isSelectionSingleton()) {
		
		const i = selection.selectedIntervals[0][0];
		
		if (i === clipDivs.length - 1) {
			// selected clip is last of page
			
			pageDown(true);
			
		} else {
			// selected clip is not last of page
			
			selectClip(i + 1);
			
		}
		
	}
			
}
		

function maybeSelectPreviousClip() {
	
	if (isSelectionSingleton()) {
		
		const i = selection.selectedIntervals[0][0];
		
		if (i === 0) {
			// selected clip is first of page
			
			pageUp(true);
			
		} else {
			// selected clip is not first of page
			
			selectClip(i - 1);
			
		}
			
	}

}


function onKeyPress(e) {
	
//	console.log(
//		`onKeyPress "${e.key}"`, e.shiftKey, e.ctrlKey, e.altKey, e.metaKey);
	
	const action = getPredefinedCommandAction(e);
	
	if (action !== null) {
		
		// Prevent client from doing whatever it might normally do
		// in response to the pressed key.
		e.preventDefault();
		
		action();
			
	} else {
	
	    annotationCommandInterpreter.onKey(e.key);
	    
	}
	
}


const predefinedCommands = {
		">": () => pageDown(false),
		"<": () => pageUp(false),
		"^": selectFirstClip,
		" ": maybeSelectNextClip,
		"__Shift+Space__": maybeSelectPreviousClip
	}


function getPredefinedCommandAction(e) {
	
	let name = e.key;
	if (name === " " && e.shiftKey)
		name = "__Shift+Space__";
	
	const action = predefinedCommands[name];
	
	return action === undefined ? null : action;

}


function selectClip(i) {
    selection.select(i);
    updateSelectionOutlines();
    scrollToClipIfNeeded(clipDivs[i]);
}


function pageDown(selectFirstClip) {
	if (pageEndIndex < numClips) {
		const newStartIndex = pageEndIndex;
		const selectedIndex = selectFirstClip ? newStartIndex : null;
		loadPage(newStartIndex, selectedIndex);
	}
}


function pageUp(selectLastClip) {
	if (pageStartIndex > 0) {
		const selectedIndex = selectLastClip ? pageStartIndex - 1 : null;
		const newStartIndex = Math.max(pageStartIndex - pageSize, 0);
		loadPage(newStartIndex, selectedIndex);
	}
}


function loadPage(startIndex, selectedIndex) {
	let query =
		`station=${stationName}&` +
		`microphone_output=${microphoneOutputName}&` +
		`detector=${detectorName}&` +
		`classification=${classification}&` +
		`date=${date}&start=${startIndex + 1}&size=${pageSize}`;
	if (selectedIndex !== null)
		query += `&selected=${selectedIndex + 1}`;
	console.log("new query", query);
	window.location.search=query;	
}


function isSelectionSingleton() {
	return selection !== null && getNumSelectedClips() === 1;
}


function getNumSelectedClips() {
	return selection.selectedIntervals.reduce(getNumSelectedClipsAux, 0);
}


function getNumSelectedClipsAux(acc, interval) {
	const [a, b] = interval;
	return acc + b - a + 1;
}


function scrollToClipIfNeeded(clipDiv) {
	
    const rect = clipDiv.getBoundingClientRect();
    
	const navbar = document.getElementById("navbar");
	const navbarHeight = navbar.getBoundingClientRect().height;
	
    const yMargin = clipLayoutSettings.verticalSpacing / 2;
    
    if (rect.top < navbarHeight + yMargin ||
            rect.bottom > window.innerHeight - yMargin)
    	
    	window.scrollBy(0, rect.top - navbarHeight - yMargin);
    
}


window.onload = onLoad;
document.onkeypress = onKeyPress;
