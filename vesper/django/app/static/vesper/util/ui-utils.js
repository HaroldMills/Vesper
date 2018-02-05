'use strict'


function getMicrophoneOutputDisplayName(output_name) {
	
	/*
	 * Gets the display form of the specified microphone output name.
	 * 
	 * If the output name ends with " Output", we remove that suffix.
	 * Otherwise we leave the name as is.
	 */
	
	const suffix = ' Output'
	if (output_name.endsWith(suffix))
		return output_name.substring(0, output_name.length - suffix.length);
	else
		return output_name
		
}
