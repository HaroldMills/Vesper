'use strict'


// TODO: Update job end time, status, and log periodically while job
// is running. (Updating the log is potentially problematic, since it
// can grow very large.)


// let intervalId = null;


function onLoad() {
	const textArea = document.getElementById('textarea');
	textArea.scrollTop = textArea.scrollHeight;
	// intervalId = window.setInterval(onJobInterval, 1000);
}


//function onJobInterval() {
//	console.log('onJobInterval');
//	const url = '/vesper/job/xx/json';
//	const xhr = new XMLHttpRequest();
//	xhr.onload = () => onJobGetComplete(xhr);
//	xhr.onerror = () => console.log('XHR error');
//	xhr.open('GET', url);
//	xhr.setRequestHeader('Cache-Control', 'no-cache');
//	xhr.send();
//}
//
//
//function onJobGetComplete(xhr) {
//	console.log('onJobGetComplete status', xhr.status);
//	if (xhr.status === 200) {
//		console.log('onJobGetComplete');
//	} else
//		window.clearInterval(intervalId);
//}


window.onload = onLoad;
