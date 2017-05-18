'use strict'


let clipAlbum = null;


function onLoad() {
	initSettingsModal();
	createClipAlbum();
}


function createClipAlbum() {
	
	const elements = {
		'titleHeading': document.getElementById('title'),
	    'rugPlotDiv': document.getElementById('rug-plot'),
	    'clipsDiv': document.getElementById('clips')
	};
	
	const clipViewDelegateClasses = {
		'Spectrogram': SpectrogramClipViewDelegate
	};
	
	const settings = _findPreset(settingsPresets, settingsPresetPath);
	const commands = _findPreset(commandsPresets, commandsPresetPath);
		
	clipAlbum = new ClipAlbum(
		elements, clips, recordings, solarEventTimes, clipViewDelegateClasses,
		settings, commands);
	
}


function _findPreset(presetInfos, presetPath) {
	
	for (const [path, preset] of presetInfos)
		if (path.join('/') === presetPath)
			return preset;
	
	return null;
	
}


function onResize() {
	clipAlbum.onResize();
}


function initSettingsModal() {
	
	// TODO: Rather than having the server send presets to the client,
	// perhaps the client should retrieve the presets from the server
	// with XHRs. We could set up URLs so that a client could request
	// all presets of a specified type as JSON.
	
//	showPresets('Clip Album Settings', settingsPresets);
//	showPresets('Clip Album Commands', commandsPresets);
	
	const settingsSelect = document.getElementById('settings');
	populatePresetSelect(settingsSelect, settingsPresets, settingsPresetPath);
	
	const commandsSelect = document.getElementById('commands');
	populatePresetSelect(commandsSelect, commandsPresets, commandsPresetPath);
	
	const okButton = document.getElementById('ok-button');
	okButton.onclick = onOkButtonClick;
	
}


function showPresets(type_name, info) {
	console.log(`${type_name} presets:`);
	for (const [path, preset] of info)
		console.log('    ' + path);
}


function populatePresetSelect(select, presetInfos, presetPath) {
	
	for (const [i, [path, preset]] of presetInfos.entries()) {
		
		const option = document.createElement('option');
	    option.text = path.join('/');
		select.add(option);
		
		if (option.text === presetPath)
			select.selectedIndex = i;
		
	}
	
}


function onOkButtonClick() {
	
	if (settingsPresets.length > 0)
		clipAlbum.settings = _getSelectedPreset('settings', settingsPresets);
	
	if (commandsPresets.length > 0)
		clipAlbum.commands = _getSelectedPreset('commands', commandsPresets);
		
}


function _getSelectedPreset(selectId, presets) {
	const select = document.getElementById(selectId);
	return presets[select.selectedIndex][1];
}


function onKeyPress(e) {
	clipAlbum.onKeyPress(e);
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
