import { ClipAlbum } from '/static/vesper/clip-album/clip-album.js';


let clipAlbum = null;


// Module-level state, set via `init` function.
let state = null;


export function init(state_) {

    // Set module-level state.
    state = state_;

    // Install event handlers.
    window.onload = onLoad;
    window.onresize = onResize;

}


function onLoad() {
    if (!state.archiveReadOnly)
        initSettingsModal();
    createClipAlbum();
}


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


function createClipAlbum() {
	clipAlbum = new ClipAlbum(state);
}


function onResize() {
	clipAlbum.onResize();
}


function initSettingsModal() {

	// TODO: Rather than having the server send presets to the client,
	// perhaps the client should fetch the presets from the server.
	// We could set up URLs so that a client could request all presets
    // of a specified type as JSON.

	const settingsSelect =
	    document.getElementById('settings-modal-settings-select');
	populatePresetSelect(
        settingsSelect, state.settingsPresets, state.settingsPresetPath);

	const keyBindingsSelect =
	    document.getElementById('settings-modal-key-bindings-select');
	populatePresetSelect(
        keyBindingsSelect, state.keyBindingsPresets,
        state.keyBindingsPresetPath);

    const okButton = document.getElementById('settings-modal-ok-button');
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

	if (state.settingsPresets.length > 0)
		clipAlbum.settings = _getSelectedPreset(
            'settings-modal-settings-select', state.settingsPresets);

	if (state.keyBindingsPresets.length > 0)
		clipAlbum.commands = _getSelectedPreset(
            'settings-modal-key-bindings-select', state.keyBindingsPresets);

}


function _getSelectedPreset(selectId, presets) {
	const select = document.getElementById(selectId);
	return presets[select.selectedIndex][1];
}
