'use strict'


// TODO: Update job end time, status, and log periodically while job
// is running. (Updating the log is potentially problematic, since it
// can grow very large.)


// let intervalId = null;


function onLoad() {
    prettifyCommand();
    scrollJobTextArea();
    // intervalId = window.setInterval(onJobInterval, 1000);
}


function prettifyCommand() {
    const textArea = document.getElementById('command-textarea');
    const object = JSON.parse(textArea.value);
    textArea.value = JSON.stringify(object, null, 4);
}


function scrollJobTextArea() {
    const textArea = document.getElementById('job-textarea');
    textArea.scrollTop = textArea.scrollHeight;
}


//function onJobInterval() {
//	console.log('onJobInterval');
//	const url = '/job/xx/json';
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
