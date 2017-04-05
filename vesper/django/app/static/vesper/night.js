'use strict'


let clipCollectionView = null;


function onLoad() {
	initSettingsModal();
	createClipCollectionView();
}


function createClipCollectionView() {
	
	const elements = {
		'titleHeading': document.getElementById('title'),
	    'rugPlotDiv': document.getElementById('rug-plot'),
	    'clipsDiv': document.getElementById('clips')
	};
	
	const clipViewDelegateClasses = {
		'Spectrogram': SpectrogramClipViewDelegate
	};
		
	clipCollectionView = new ClipCollectionView(
		elements, clips, recordings, solarEventTimes, clipViewDelegateClasses);
	
}


function onResize() {
	clipCollectionView.onResize();
}


function initSettingsModal() {
	
	// TODO: Rather than having the server send presets to the client,
	// perhaps the client should retrieve the presets from the server
	// with XHRs. We could set up URLs so that a client could request
	// all presets of a specified type as JSON.
	
	showPresets(
	    'Clip Collection View Settings', viewSettingsPresets);
	showPresets(
		'Clip Collection View Keyboard Commands', keyboardCommandsPresets);
	
	const viewSettingsSelect = document.getElementById('view-settings');
	populatePresetSelect(viewSettingsSelect, viewSettingsPresets);
	
	const keyboardCommandsSelect = document.getElementById('keyboard-commands');
	populatePresetSelect(keyboardCommandsSelect, keyboardCommandsPresets);
	
	const okButton = document.getElementById('ok-button');
	okButton.onclick = onOkButtonClick;
	
}


function showPresets(type_name, info) {
	console.log(`${type_name} presets:`);
	for (let [path, preset] of info)
		console.log('    ' + path);
}


function populatePresetSelect(select, info) {
	
	for (let [path, preset] of info) {
		const option = document.createElement('option');
	    option.text = path.join(' / ');
		select.add(option);
	}
	
}


function onOkButtonClick() {
	
	if (viewSettingsPresets.length > 0)
		clipCollectionView.settings = _getSelectedPreset(
			'view-settings', viewSettingsPresets);
	
	if (keyboardCommandsPresets.length > 0)
		clipCollectionView.keyboardCommands = _getSelectedPreset(
		    'keyboard-commands', keyboardCommandsPresets);
		
}


function _getSelectedPreset(selectId, presets) {
	const select = document.getElementById(selectId);
	return presets[select.selectedIndex][1];
}


function onKeyPress(e) {
	clipCollectionView.onKeyPress(e);
}


window.onload = onLoad;
window.onresize = onResize;
document.onkeypress = onKeyPress;
