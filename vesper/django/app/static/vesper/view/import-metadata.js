function onDragOver(event) {
	event.preventDefault();
}


function onDrop(event) {
	
	event.preventDefault();
	
	for (const file of droppedFiles(event)) {
		const reader = new FileReader();
		reader.onload = e => onFileLoad(e);
		reader.readAsText(file);
	}
	
}


function onFileLoad(event) {
	
	const fileContents = event.target.result;
	const textArea = document.getElementById('yaml-text-area');
	
	// It's important to use `value` here instead of `innerHTML`. If we
	// use `innerHTML` instead, then for some reason drag and drop won't
	// work if the user first edits the text in the text area. See
	// https://stackoverflow.com/questions/22185544/editing-textarea-breaks-droppable.
	textArea.value = fileContents;
	
}


/**
 * Generates the files of a drop event.
 * 
 * @param event - the drop event.
 * @returns an iterator for the files of the specified drop event.
 */
function* droppedFiles(event) {
	
	// The code of this function is derived from an example at
	// https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/File_drag_and_drop.
	
	const items = event.dataTransfer.items
	
	if (items) {
		// have DataTransferItemList support
		
		for (const item of items)
			if (item.kind === 'file')
				yield item.getAsFile();
		
	} else {
		// don't have DataTransferItemList support
		
		// Use DataTransfer interface to access file(s).
		
		for (const file of dt.files)
			yield file;
		
	}
	
}
