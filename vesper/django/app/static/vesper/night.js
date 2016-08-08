"use strict"


// Clip time scale in pixels per second.
const clipXScale = 1000;

// Clip height in pixels.
const clipHeight = 100;

// Clip spacing sizes in pixels.
const clipXSpacing = 20,
      clipYSpacing = 20;

// Clip outline width in pixels.
const clipOutlineWidth = 5;

// Spectrogram parameters.
const spectrogramParams = {
	"window": createDataWindow("Hann", 100),
	"hopSize": 25,
	"dftSize": 256,
	"referencePower": 1,
	"lowPower": 10,
	"highPower": 100,
	"smoothingEnabled": true,
	"timePaddingEnabled": false
}

// The index of the last clip displayed on this page.
let pageEndIndex = null;

// The clip plots displayed on this page.
let plots = null;

// The selected clips of this page.
let selection = null;


function onLoad() {
	showAnnotationSchemes(annotationSchemePresets, '');
	pageEndIndex = Math.min(pageStartIndex + pageSize, numClips);
	setTitle();
	createPlots();
	layOutPlots();
	initSelection();
}


function showAnnotationSchemes(info) {
	showAnnotationSchemesAux(info, '')
}


function showAnnotationSchemesAux(info, prefix) {
	let [dirName, subdirInfos, presets] = info;
	console.log(prefix + dirName);
	prefix += '    ';
	for (let subdirInfo of subdirInfos)
		showAnnotationSchemesAux(subdirInfo, prefix);
	for (let preset of presets)
		console.log(prefix + preset[0]);
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
		selectPlot(selectedIndex - pageStartIndex);
}


function createPlots() {
	
	// The server provides us with a Javascript array called `clips`,
	// each element of which describes a clip. It also provides us with
	// an empty <div> element with ID "plots" where clip plots should
	// go. We populate the <div> according to the contents of the
	// `clips` array.
	
	const plotsDiv = document.getElementById("plots");
	
	if (clips.length != 0) {
		
		plots = [];
		
		for (let i = 0; i != clips.length; ++i) {
			
			const clip = clips[i];
			clip.index = i;
			
			const plot = createPlot(clip);
			clip.plot = plot;
			
			plotsDiv.appendChild(plot);
			plots.push(plot);
		}
		
	} else
		plotsDiv.innerHTML = "There are no clips to display.";
	
}


function layOutPlots() {
	
	const x = Math.max(clipXSpacing / 2, clipOutlineWidth) + "px",
	      y = Math.max(clipYSpacing / 2, clipOutlineWidth) + "px";
	
	let i = 0;
	
	for (let plot of plots) {
		
		const clip = clips[i++];
		const span = (clip.length - 1) / clip.sampleRate;
		const width = span * clipXScale;
		plot.style.minWidth = width + "px";
	    plot.style.width = width + "px";
	    plot.style.height = clipHeight + "px";
	    plot.style.margin = y + " " + x + " " + y + " " + x;
	    
	    // Set canvas width and height to width and height on screen.
	    // This will help prevent distortion of items drawn on the
	    // canvas, especially text.
	    const canvas = plot.querySelector(".clip-plot-canvas");
	    canvas.width = canvas.clientWidth;
	    canvas.height = canvas.clientHeight;
	    
	}
	
}


function createPlot(clip) {
	
	const index = clip.index;
	
    const plot = document.createElement("div");
    plot.className = "clip-plot";
    plot.setAttribute("data-index", index);
    
    clip.plot = plot;
    
    const canvas = document.createElement("canvas");
    canvas.className = "clip-plot-canvas";
    canvas.setAttribute("data-index", index);
    canvas.addEventListener("mouseover", onMouseOver);
    canvas.addEventListener("mouseout", onMouseOut);
    canvas.addEventListener("click", onCanvasClick);
    plot.appendChild(canvas);
    
    const button = document.createElement("button");
    button.className = "clip-plot-play-button";
    button.setAttribute("data-index", index);
    button.addEventListener("click", onPlayButtonClick);
    plot.appendChild(button);    
    
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
    audio.className = "clip-plot-audio";
    audio.setAttribute("src", clip.url);
    audio.setAttribute("data-index", index);
    audio.innerHtml =
        "Your browser does not support the <code>audio</code> HTML element."
    plot.appendChild(audio)
    
    startAudioDecoding(clip);
    
    return plot;
	
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
    const params = spectrogramParams;
    clip.spectrogram = computeClipSpectrogram(clip, params);
    clip.spectrogramCanvas = createSpectrogramCanvas(clip, params);
    clip.spectrogramImageData = createSpectrogramImageData(clip);
    drawSpectrogram(clip, params);
    drawClipPlot(clip, params);
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


function computeClipSpectrogram(clip, params) {
	const samples = clip.samples
	const spectrogram = allocateSpectrogramStorage(samples.length, params);
	computeSpectrogram(samples, params, spectrogram);
	return spectrogram;
}


function createSpectrogramCanvas(clip, params) {
	
	const gram = clip.spectrogram;
	const numBins = params.dftSize / 2 + 1;
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


function drawSpectrogram(clip, params) {
	
	const gram = clip.spectrogram;

	const canvas = clip.spectrogramCanvas;
	const numSpectra = canvas.width;
	const numBins = canvas.height;

	const imageData = clip.spectrogramImageData;
	const data = imageData.data;
	
	// Get scale factor and offset for mapping the range
	// [params.lowPower, params.highPower] into the range [0, 255].
	const delta = params.highPower - params.lowPower
	const a = 255 / delta;
	const b = -255 * params.lowPower / delta;

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


function drawClipPlot(clip, params) {
	
    const canvas = clip.plot.querySelector(".clip-plot-canvas");
	const context = canvas.getContext("2d");
	
	// Draw gray background rectangle.
	context.fillStyle = "gray";
	context.fillRect(0, 0, canvas.width, canvas.height);
	
	// Draw spectrogram from clip spectrogram canvas, stretching as needed.
	const gramCanvas = clip.spectrogramCanvas;
	const numSpectra = gramCanvas.width;
	context.imageSmoothingEnabled = params.smoothingEnabled;
	if (params.timePaddingEnabled) {
		let [x, width] = getSpectrogramXExtent(
			params, numSpectra, clip, canvas.width);
		context.drawImage(gramCanvas, x, 0, width, canvas.height);
	} else {
		context.drawImage(gramCanvas, 0, 0, canvas.width, canvas.height);
	}

	// Draw text overlay.
	context.font = "1.2em sans-serif";
	context.fillStyle = "white";
	context.textAlign = "center";
	let classification = clip.classification;
	if (classification.startsWith("Call."))
		classification = classification.slice(5);
	const parts = clip.startTime.split(" ");
	const time = `${parts[1]} ${parts[2]}`;
	const text = classification + " " + time;
	context.fillText(text, canvas.width / 2, canvas.height - 5, canvas.width);
	
}


function getSpectrogramXExtent(params, numSpectra, clip, canvasWidth) {
	const sampleRate = clip.sampleRate;
    const startTime = params.window.length / 2 / sampleRate;
    const spectrumPeriod = params.hopSize / sampleRate;
    const endTime = startTime + (numSpectra - 1) * spectrumPeriod;
    const span = (clip.length - 1) / sampleRate;
    const pixelPeriod = span / canvasWidth;
    const x = startTime / pixelPeriod;
    const width = (endTime - startTime) / pixelPeriod;
    return [x, width];
}


function onMouseOver(e) {
	const i = getPlotIndex(e.target);
	console.log("mouse over " + i);
}


function getPlotIndex(element) {
	return parseInt(element.getAttribute("data-index"));
}


function onMouseOut(e) {
	const i = getPlotIndex(e.target);
	console.log("mouse out " + i);
}


function onCanvasClick(e) {

	const index = getPlotIndex(e.target);
	
	if (e.shiftKey)
		selection.extend(index);
	else if (e.ctrlKey)
		selection.toggle(index);
	else
		selection.select(index);
	
	updateSelectionOutlines();
	
}


function updateSelectionOutlines() {
	for (let i = 0; i < plots.length; ++i) {
		const color = selection.contains(i) ? "orange" : "transparent";
		plots[i].style.outlineColor = color;
	}
}


function onPlayButtonClick(e) {
	const i = getPlotIndex(e.target);
	const plot = plots[i];
	const audio = plot.getElementsByClassName("clip-plot-audio")[0];
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
		drawClipPlot(clip, spectrogramParams);
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
	if (plots.length > 0)
	    selectPlot(0);
}


function maybeSelectNextClip() {
	
	if (isSelectionSingleton()) {
		
		const i = selection.selectedIntervals[0][0];
		
		if (i === plots.length - 1) {
			// selected plot is last of page
			
			pageDown(true);
			
		} else {
			// selected plot is not last of page
			
			selectPlot(i + 1);
			
		}
		
	}
			
}
		

function maybeSelectPreviousClip() {
	
	if (isSelectionSingleton()) {
		
		const i = selection.selectedIntervals[0][0];
		
		if (i === 0) {
			// selected plot is first of page
			
			pageUp(true);
			
		} else {
			// selected plot is not first of page
			
			selectPlot(i - 1);
			
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


function selectPlot(i) {
    selection.select(i);
    updateSelectionOutlines();
    scrollToPlotIfNeeded(plots[i]);
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


function scrollToPlotIfNeeded(plot) {
	
    const rect = plot.getBoundingClientRect();
    
	const navbar = document.getElementById("navbar");
	const navbarHeight = navbar.getBoundingClientRect().height;
	
    const yMargin = clipYSpacing / 2;
    
    if (rect.top < navbarHeight + yMargin ||
            rect.bottom > window.innerHeight - yMargin)
    	
    	window.scrollBy(0, rect.top - navbarHeight - yMargin);
    
}


window.onload = onLoad;
document.onkeypress = onKeyPress;
